"""Realiser A16 integration."""

import asyncio
import logging
import socket
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .realiser_a16_hex import A16Response, RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

DOMAIN = "realiser_a16"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_SPEAKER_SWITCHES = "enable_speaker_switches"
DEFAULT_UPDATE_INTERVAL = 10


class RealiserA16DataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Realiser A16.

    Uses a persistent TCP connection. The A16 supports only one connection
    at a time and closes it after an inactivity timeout (30-250 seconds).
    We reconnect automatically when needed.

    Data layout returned by _fetch_data (consumed by all platform entities):

        data = {
            "connected": bool,
            "status": {            # flat KEY→value dict
                # User A (from 0x80, or async with any command)
                "AUR": "Benni", "PA": "01", "VA": "60", "IN": "HDMI-1",
                "ASPKR": "5.1.4h", "AQNAME": "Benni", ...
                # User B (from 0xA0)
                "BUR": "...", "PB": "01", "VB": "55", ...
                # Power
                "PWR": "ON",
            },
            "assignments": {       # DSP channel assignments
                "ach": {1: "L", 2: "R", ...},   # User A channels
                "bch": {1: "L", 2: "R", ...},   # User B channels
            },
            "speakers": {          # per-speaker state (1-based IDs)
                1: {"name": "L",  "visible": True,  "state": "active"},
                2: {"name": "R",  "visible": True,  "state": "mute"},
                ...
            },
            "speaker_mode": "SOLO" | "MUTE" | None,
            "firmware": {"A16FW": "2.17 ...", "APMFW": "...", ...},
        }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = 4101,
        timeout: float = 10.0,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client: Optional[RealiserA16Hex] = None
        self._lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Open a fresh TCP connection to the A16."""
        self._disconnect()
        _LOGGER.debug("Connecting to %s:%s", self.host, self.port)
        self._client = RealiserA16Hex(self.host, self.port, timeout=self.timeout)
        self._client.connect()

        # Wake-up: the A16 needs at least one command after a new connection
        # before it starts prepending async User A status to responses.
        try:
            self._client.send(0x2E)
            _LOGGER.debug("Wake-up command sent")
        except Exception as err:
            _LOGGER.warning("Wake-up command failed: %s", err)

        _LOGGER.info("Connected to Realiser A16 at %s:%s", self.host, self.port)

    def _disconnect(self) -> None:
        """Close TCP connection cleanly."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _send(self, code: int) -> A16Response:
        """Send command, reconnecting once on failure."""
        if self._client is None:
            self._connect()
        try:
            return self._client.send(code)  # type: ignore[union-attr]
        except (OSError, socket.error) as err:
            _LOGGER.warning("Send 0x%02x failed (%s), reconnecting…", code, err)
            self._disconnect()
            self._connect()
            return self._client.send(code)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Data fetch
    # ------------------------------------------------------------------

    def _fetch_data(self) -> Dict[str, Any]:
        """Fetch device state with optimized two-stage polling.

        Stage 1 (every 10s): Power + User A + User B (3 commands)
            - 0x2E → power + user_a (async)
            - 0x80 → user_a (full info)
            - 0xA0 → user_b

        Stage 2 (every 60s): Assignments + Speakers (3 commands)
            - 0x37 → ach/bch assignments + user_a (async)
            - 0xAE → visible speakers + user_a (async)
            - 0xAF → active speakers + mode + user_a (async)

        We alternate between stages and merge data with existing coordinator data.
        """
        try:
            # Determine which stage to run based on existing data age
            # For simplicity, we alternate: first fast, then slow, then fast...
            is_slow_stage = hasattr(self, "_slow_stage_counter")
            if not hasattr(self, "_slow_stage_counter"):
                self._slow_stage_counter = 0

            self._slow_stage_counter += 1

            if self._slow_stage_counter % 6 == 0:
                # Slow stage every 6th update (~60s)
                result = self._fetch_slow_stage()
            else:
                # Fast stage (~10s)
                result = self._fetch_fast_stage()
            self._reconnect_failures = 0
            return result

        except Exception as err:
            self._disconnect()
            self._reconnect_failures = getattr(self, "_reconnect_failures", 0) + 1
            _LOGGER.error(
                "Failed to fetch data (failure #%d): %s",
                self._reconnect_failures,
                err,
                exc_info=True,
            )
            raise UpdateFailed(f"Failed to fetch data: {err}") from err

    def _fetch_fast_stage(self) -> Dict[str, Any]:
        """Fast stage: Power + User A + User B (3 commands)."""
        r_pwr = self._send(0x2E)
        _LOGGER.debug("0x2e power=%s", r_pwr.power)

        r_a = self._send(0x80)
        _LOGGER.debug("0x80 user_a keys=%s", list(r_a.user_a.keys()))

        r_b = self._send(0xA0)
        _LOGGER.debug("0xa0 user_b keys=%s", list(r_b.user_b.keys()))

        # Merge with existing data
        existing = self.data or {}
        status = dict(existing.get("status", {}))
        if r_a.user_a:
            status.update(r_a.user_a)
        if r_b.user_b:
            status.update(r_b.user_b)
        if r_pwr.power:
            status["PWR"] = r_pwr.power

        result = {
            "connected": True,
            "status": status,
            "assignments": existing.get("assignments", {"ach": {}, "bch": {}}),
            "speakers": existing.get("speakers", {}),
            "speaker_mode": existing.get("speaker_mode"),
            "firmware": existing.get("firmware", {}),
        }
        return result

    def _fetch_slow_stage(self) -> Dict[str, Any]:
        """Slow stage: Assignments + Speaker Visibility + Speaker Status (3 commands)."""
        r_assign = self._send(0x37)
        _LOGGER.debug(
            "0x37 ach=%d bch=%d",
            len(r_assign.assignments["ach"]),
            len(r_assign.assignments["bch"]),
        )

        r_vis = self._send(0xAE)
        _LOGGER.debug("0xae visible=%s", r_vis.visible_speakers)

        r_act = self._send(0xAF)
        _LOGGER.debug(
            "0xaf active=%s mode=%s", r_act.active_speakers, r_act.speaker_mode
        )

        # Merge with existing data (keep fast-stage data)
        existing = self.data or {}
        status = dict(existing.get("status", {}))

        # Update with latest user_a from slow commands
        user_a = _merge_user_a(r_assign, r_vis, r_act)
        for k, v in user_a.items():
            if v:
                status[k] = v

        # Update assignments and speakers
        result = {
            "connected": True,
            "status": status,
            "assignments": {
                "ach": r_assign.assignments["ach"],
                "bch": r_assign.assignments["bch"],
            },
            "speakers": _build_speaker_dict(
                r_vis.visible_speakers, r_act.active_speakers
            ),
            "speaker_mode": r_act.speaker_mode or r_vis.speaker_mode,
            "firmware": r_assign.firmware,
        }
        return result

    def refresh_speakers(self) -> Dict[str, Any]:
        """Fetch speaker visibility + status on-demand (called by speaker switches).

        Returns the speakers dict and updates coordinator.data in place.
        """
        try:
            r_vis = self._send(0xAE)
            r_act = self._send(0xAF)

            speakers = _build_speaker_dict(
                r_vis.visible_speakers, r_act.active_speakers
            )
            speaker_mode = r_act.speaker_mode or r_vis.speaker_mode

            if self.data:
                self.data["speakers"] = speakers
                self.data["speaker_mode"] = speaker_mode

            _LOGGER.debug(
                "refresh_speakers: visible=%s active=%s mode=%s",
                r_vis.visible_speakers,
                r_act.active_speakers,
                speaker_mode,
            )
            return speakers

        except Exception as err:
            _LOGGER.error("Failed to refresh speakers: %s", err)
            raise

    async def _async_update_data(self) -> Dict[str, Any]:
        """Async update with lock."""
        async with self._lock:
            return await self.hass.async_add_executor_job(self._fetch_data)

    def send_command(self, code: int) -> A16Response:
        """Send a raw command (called from platforms via executor)."""
        return self._send(code)


# ------------------------------------------------------------------
# Module-level helpers (no coordinator state needed)
# ------------------------------------------------------------------


def _merge_user_a(*responses: A16Response) -> Dict[str, str]:
    """Merge User A dicts from multiple responses, preferring non-empty values."""
    merged: Dict[str, str] = {}
    for resp in responses:
        for key, value in resp.user_a.items():
            if value or key not in merged:
                merged[key] = value
    return merged


def _build_speaker_dict(visible: set, active: set) -> Dict[Any, Any]:
    """Build the per-speaker state dict used by all platform entities.

    Speaker IDs in A16Response are 0-based (V00 = speaker index 0).
    The SPEAKER_NAMES dict and entity unique-IDs use 1-based IDs.

    Returns:
        {
            1: {"name": "L",  "visible": True,  "state": "active"},
            2: {"name": "R",  "visible": True,  "state": "mute"},
            ...50...
        }
    """
    result: Dict[int, Dict[str, Any]] = {}
    for speaker_id in range(1, 51):
        idx = speaker_id - 1  # A16 protocol is 0-based
        name = RealiserA16Hex.SPEAKER_NAMES.get(speaker_id, f"Spk{speaker_id}")
        result[speaker_id] = {
            "name": name,
            "visible": idx in visible,
            "state": "active" if idx in active else "mute",
        }
    return result


# ------------------------------------------------------------------
# Home Assistant entry points
# ------------------------------------------------------------------


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Realiser A16 from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 4101)
    timeout = entry.data.get(CONF_TIMEOUT, 10.0)
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = RealiserA16DataUpdateCoordinator(
        hass, host, port, timeout, update_interval
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def async_refresh_speakers(call: ServiceCall) -> None:
        """Service to manually refresh speaker data."""
        await hass.async_add_executor_job(coordinator.refresh_speakers)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh_speakers", async_refresh_speakers)

    await hass.config_entries.async_forward_entry_setups(
        entry, ["media_player", "sensor", "switch", "select", "button"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = ["media_player", "sensor", "switch", "select", "button"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ]
        coordinator._disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
