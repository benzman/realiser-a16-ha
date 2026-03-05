"""Realiser A16 integration."""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

DOMAIN = "realiser_a16"
CONF_UPDATE_INTERVAL = "update_interval"

# Default polling interval in seconds
DEFAULT_UPDATE_INTERVAL = 10


class RealiserA16DataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Realiser A16."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = 4101,
        timeout: float = 5.0,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client: Optional[RealiserA16Hex] = None
        self._lock = asyncio.Lock()
        self._connected = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    def _get_client(self) -> RealiserA16Hex:
        """Get or create client."""
        if self.client is None:
            self.client = RealiserA16Hex(self.host, self.port, self.timeout)
        return self.client

    def _ensure_connected(self) -> None:
        """Ensure TCP connection is established."""
        try:
            client = self._get_client()
            if not self._connected:
                _LOGGER.debug(
                    "Attempting TCP connection to %s:%s", self.host, self.port
                )
                client.connect()
                self._connected = True
                _LOGGER.info("Connected to Realiser A16 at %s:%s", self.host, self.port)
                # Wir warten kurz nach connect, damit der A16 bereit ist
                import time

                time.sleep(0.2)
        except Exception as err:
            self._connected = False
            _LOGGER.exception("Failed to connect to %s:%s", self.host, self.port)
            raise UpdateFailed(f"Connection failed: {err}") from err

    def _fetch_data(self) -> Dict[str, Any]:
        """Fetch actual data from device."""
        try:
            self._ensure_connected()
            client = self._get_client()

            # Poll essential commands with individual error handling
            status_raw = ""
            assignments_raw = ""
            preset_a_raw = ""
            preset_b_raw = ""

            # STATUS (quick ack)
            try:
                _LOGGER.debug("Sending command 0x45 (STATUS)")
                status_raw = client.send(0x45)
                _LOGGER.debug("STATUS response: %s", status_raw[:100])
            except Exception as err:
                _LOGGER.warning("STATUS command failed: %s", err)

            # ASSIGNMENTS (speaker mapping)
            try:
                _LOGGER.debug("Sending command 0x37 (ASSIGNMENTS)")
                assignments_raw = client.send(0x37)
                _LOGGER.debug("ASSIGNMENTS response: %s", assignments_raw[:100])
            except Exception as err:
                _LOGGER.warning("ASSIGNMENTS command failed: %s", err)

            # PRESET A (full data)
            try:
                _LOGGER.debug("Sending command 0x46 (PRESET A)")
                preset_a_raw = client.send(0x46)
                _LOGGER.debug(
                    "PRESET A keys: %s", self._parse_preset(preset_a_raw).keys()
                )
            except Exception as err:
                _LOGGER.warning("PRESET A command failed: %s", err)

            # PRESET B (full data)
            try:
                _LOGGER.debug("Sending command 0x47 (PRESET B)")
                preset_b_raw = client.send(0x47)
                _LOGGER.debug(
                    "PRESET B keys: %s", self._parse_preset(preset_b_raw).keys()
                )
            except Exception as err:
                _LOGGER.warning("PRESET B command failed: %s", err)

            # Parse responses (even if some commands failed)
            data = {
                "connected": True,
                "status": self._parse_key_value(status_raw),
                "assignments": self._parse_assignments(assignments_raw),
                "preset_a": self._parse_preset(preset_a_raw),
                "preset_b": self._parse_preset(preset_b_raw),
            }
            return data

        except Exception as err:
            self._connected = False
            _LOGGER.error("Failed to fetch data: %s", err, exc_info=True)
            raise UpdateFailed(f"Failed to fetch data: {err}") from err

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data async with lock to prevent concurrent requests."""
        async with self._lock:
            return await self.hass.async_add_executor_job(self._fetch_data)

    def _parse_key_value(self, raw: str) -> Dict[str, str]:
        """Parse KEY=VALUE null-terminated strings."""
        result = {}
        if not raw:
            return result
        tokens = raw.split("\x00")
        for token in tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def _parse_assignments(self, raw: str) -> Dict[str, Any]:
        """Parse assignments response (ACH/BCH tokens)."""
        result: Dict[str, Any] = {"global": {}, "ach": {}, "bch": {}}
        if not raw:
            return result

        tokens = raw.split("\x00")
        for token in tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                result["global"][k] = v
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

    def _parse_preset(self, raw: str) -> Dict[str, str]:
        """Parse full preset data (AUR, PA, VA, etc.)."""
        result = {}
        if not raw:
            return result
        tokens = raw.split("\x00")
        for token in tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def send_command(self, code: int) -> str:
        """Send raw command and return response (for services)."""
        if not self._connected:
            self._ensure_connected()
        return self._get_client().send(code)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Realiser A16 from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 4101)
    timeout = entry.data.get(CONF_TIMEOUT, 15.0)  # Increased default timeout
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = RealiserA16DataUpdateCoordinator(
        hass, host, port, timeout, update_interval
    )

    # Initial refresh
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["media_player", "sensor", "switch", "select"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = ["media_player", "sensor", "switch", "select"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok and entry.entry_id in hass.data[DOMAIN]:
        coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ]
        if coordinator.client:
            coordinator.client.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
