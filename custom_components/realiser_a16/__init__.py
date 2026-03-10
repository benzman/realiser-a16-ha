"""Realiser A16 integration."""

import asyncio
import logging
import socket
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .realiser_a16_hex import RealiserA16Hex

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

    def _connect(self) -> None:
        """Open a fresh TCP connection to the A16."""
        self._disconnect()
        _LOGGER.debug("Connecting to %s:%s", self.host, self.port)
        self._client = RealiserA16Hex(self.host, self.port, timeout=self.timeout)
        self._client.connect()

        # Wake-up: A16 requires a command to be sent first after new connection
        # Otherwise commands may return incomplete data
        try:
            self._client.send(0x2E)  # Power status - quick wake-up
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

    def _send(self, code: int) -> str:
        """Send command, reconnecting once on failure."""
        if self._client is None:
            self._connect()
        try:
            return self._client.send(code)  # type: ignore[union-attr]
        except (OSError, socket.error) as err:
            _LOGGER.warning("Send 0x%02x failed (%s), reconnecting...", code, err)
            self._disconnect()
            self._connect()
            return self._client.send(code)  # type: ignore[union-attr]

    def _fetch_data(self) -> Dict[str, Any]:
        """Fetch data from device using a persistent connection."""
        try:
            # User A info (0x80): VA, AUR, IN, ASPKR, ...
            raw_a = self._send(0x80)
            _LOGGER.debug("0x80 User A info: %s", raw_a[:120])

            # User B info (0xA0): VB, BUR, ...
            raw_b = self._send(0xA0)
            _LOGGER.debug("0xa0 User B info: %s", raw_b[:120])

            # Power status (0x2e)
            raw_pwr = self._send(0x2E)
            _LOGGER.debug("0x2e Power status: %s", raw_pwr[:60])

            # Speaker assignments (0x37)
            raw_assign = self._send(0x37)
            _LOGGER.debug("0x37 Assignments: %s", raw_assign[:60])

            # Speaker visibility (0xAE) - contains V00, V01, etc.
            raw_vis = self._send(0xAE)
            _LOGGER.debug("0xae Speaker visibility: %s", raw_vis[:200])

            # Speaker status (0xAF) - contains ALL=SOLO/MUTE, A00, A01, etc.
            raw_act = self._send(0xAF)
            _LOGGER.debug("0xaf Speaker status: %s", raw_act[:200])

            status = self._parse_kv(raw_a)
            status.update(self._parse_kv(raw_b))  # VB, BUR, etc.
            status.update(self._parse_kv(raw_pwr))  # PWR

            return {
                "connected": True,
                "status": status,
                "assignments": self._parse_assignments(raw_assign),
                "speakers": self._parse_speakers(raw_vis, raw_act),
                "raw": {
                    "0x80": raw_a,
                    "0xa0": raw_b,
                    "0x2e": raw_pwr,
                    "0x37": raw_assign,
                    "0xae": raw_vis,
                    "0xaf": raw_act,
                },
            }

        except Exception as err:
            self._disconnect()
            _LOGGER.error("Failed to fetch data: %s", err, exc_info=True)
            raise UpdateFailed(f"Failed to fetch data: {err}") from err

    def refresh_speakers(self) -> Dict[str, Any]:
        """Fetch speaker visibility and status on-demand (0xAE + 0xAF).

        Returns parsed speakers dict and updates coordinator.data["speakers"].
        """
        try:
            # Speaker visibility (0xAE)
            raw_vis = self._send(0xAE)
            _LOGGER.debug("0xae Speaker visibility: %s", raw_vis[:200])

            # Speaker status (0xAF) - contains ALL=SOLO/MUTE and active speakers
            raw_act = self._send(0xAF)
            _LOGGER.debug("0xaf Speaker status: %s", raw_act[:200])

            speakers = self._parse_speakers(raw_vis, raw_act)

            if self.data:
                self.data["speakers"] = speakers

            return speakers

        except Exception as err:
            _LOGGER.error("Failed to refresh speakers: %s", err)
            raise

    async def _async_update_data(self) -> Dict[str, Any]:
        """Async update with lock."""
        async with self._lock:
            return await self.hass.async_add_executor_job(self._fetch_data)

    def send_command(self, code: int) -> str:
        """Send a raw command (called from platforms via executor)."""
        return self._send(code)

    # --- Parsers ---

    def _parse_kv(self, raw: str) -> Dict[str, str]:
        """Parse null-separated KEY=VALUE pairs."""
        result: Dict[str, str] = {}
        if not raw:
            return result
        for token in raw.replace("\r", "").split("\x00"):
            token = token.strip()
            if "=" in token:
                k, v = token.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def _parse_speakers(self, raw_vis: str, raw_act: str) -> Dict[str, Any]:
        """Parse speaker data from 0xAE (visibility) and 0xAF (status) responses.

        0xAE response format:
            V00,V01,V02,... (visible speaker indices, 0-based)

        0xAF response format:
            ALL=SOLO|ALL=MUTE (the mode)
            A00,A01,A02,... (active speaker indices, 0-based)

        Returns:
            Dict keyed by speaker ID (1-50):
                {
                    1: {"name": "L",  "visible": True,  "state": "active"},
                    2: {"name": "R",  "visible": True,  "state": "mute"},
                    ...
                }
        """
        visible_ids = set()
        active_ids = set()
        mode = None

        # Parse visibility from 0xAE response (V00, V01, etc.)
        if raw_vis:
            for token in raw_vis.split("\x00"):
                token = token.strip()
                if token.startswith("V") and len(token) >= 2:
                    try:
                        idx = int(token[1:3])
                        visible_ids.add(idx)
                    except (ValueError, IndexError):
                        pass

        # Parse status from 0xAF response (A00, ALL=, etc.)
        if raw_act:
            for token in raw_act.split("\x00"):
                token = token.strip()
                if not token:
                    continue

                if token.startswith("ALL="):
                    mode = token.split("=", 1)[1]
                elif token.startswith("A") and len(token) >= 2:
                    try:
                        idx = int(token[1:3])
                        active_ids.add(idx)
                    except (ValueError, IndexError):
                        pass

        # Build result dictionary
        result = {}
        for speaker_id in range(1, 51):
            name = RealiserA16Hex.SPEAKER_NAMES.get(speaker_id, f"Spk{speaker_id}")
            # Speaker IDs in response are 0-based, we use 1-based
            is_visible = (speaker_id - 1) in visible_ids
            is_active = (speaker_id - 1) in active_ids

            result[speaker_id] = {
                "name": name,
                "visible": is_visible,
                "state": "active" if is_active else "mute",
            }

        _LOGGER.debug(
            "Parsed speakers - mode: %s, visible: %s, active: %s",
            mode,
            visible_ids,
            active_ids,
        )

        return result

    def _parse_assignments(self, raw: str) -> Dict[str, Any]:
        """Parse ACH/BCH assignment tokens."""
        result: Dict[str, Any] = {"global": {}, "ach": {}, "bch": {}}
        if not raw:
            return result
        for token in raw.replace("\r", "").split("\x00"):
            token = token.strip()
            if "=" in token:
                k, v = token.split("=", 1)
                result["global"][k.strip()] = v.strip()
            elif token.startswith("A") and len(token) >= 3:
                try:
                    idx = int(token[1:3])
                    result["ach"][idx] = token
                except ValueError:
                    pass
            elif token.startswith("B") and len(token) >= 3:
                try:
                    idx = int(token[1:3])
                    result["bch"][idx] = token
                except ValueError:
                    pass
        return result


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

    # Register services
    async def async_refresh_speakers(call: ServiceCall) -> None:
        """Service to manually refresh speaker data."""
        await hass.async_add_executor_job(coordinator.refresh_speakers)
        # Also trigger a coordinator refresh to update all entities
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
