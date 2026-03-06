"""Select entities for Realiser A16 input selection and mode control."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

# Mapping von Input-Namen zu IR-Command Codes (aus PDF Tabelle 1)
INPUT_COMMANDS = {
    "eARC": 0x20,
    "HDMI-1": 0x21,
    "HDMI-2": 0x22,
    "HDMI-3": 0x23,
    "HDMI-4": 0x24,
    "USB": 0x25,
    "LINE": 0x26,
    "STEREO": 0x27,
    "COAXIAL": 0x28,
    "OPTICAL": 0x29,
}

# IR Zone Select commands
CMD_ZONE_A = RealiserA16Hex.CMD_ZONE_A  # 0x06
CMD_ZONE_B = RealiserA16Hex.CMD_ZONE_B  # 0x07


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up select entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RealiserA16InputSelect(coordinator, "A"),
            RealiserA16InputSelect(coordinator, "B"),
            RealiserA16ModeSelect(coordinator),
            RealiserA16PresetSelect(coordinator, "A"),
            RealiserA16PresetSelect(coordinator, "B"),
        ]
    )


class RealiserA16InputSelect(SelectEntity):
    """Select entity for Realiser A16 input selection."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str
    ) -> None:
        """Initialize the input select."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._attr_unique_id = f"{coordinator.host}_input_{self.zone.lower()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }
        self._attr_options = list(INPUT_COMMANDS.keys())

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        """Return the currently selected input.

        The input name is stored in coordinator.data["status"] as "IN" (User A)
        or "BIN" (User B) - both come from the 0x80/0xA0 response.
        """
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("status", {})
        key = "IN" if self.zone == "A" else "BIN"
        value = status.get(key, "").strip()
        # Direct match
        if value in self._attr_options:
            return value
        # Partial match (e.g. device returns "HDMI-1 " with trailing space)
        for opt in self._attr_options:
            if value.startswith(opt):
                return opt
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the input source."""
        if option not in INPUT_COMMANDS:
            raise ValueError(f"Unknown input option: {option}")

        # Send zone select first (A or B) to ensure we're controlling correct zone
        zone_cmd = CMD_ZONE_A if self.zone == "A" else CMD_ZONE_B
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.send_command, zone_cmd
        )

        # Small delay to ensure zone is selected
        await self.coordinator.hass.async_create_task(
            self.coordinator.hass.async_add_executor_job(
                lambda: __import__("time").sleep(0.1)
            )
        )

        # Then send input command
        input_cmd = INPUT_COMMANDS[option]
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.send_command, input_cmd
        )

        # Request immediate refresh to update state
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16ModeSelect(SelectEntity):
    """Select entity for SOLO/MUTE mode (ALL key, 0x1A toggles between modes)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:account-voice"
    _attr_options = ["SOLO", "MUTE"]

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the mode select."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return "Speaker Mode"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        """Return current SOLO/MUTE mode from assignments."""
        if not self.coordinator.data:
            return None
        assignments = self.coordinator.data.get("assignments", {})
        mode = assignments.get("global", {}).get("ALL", "").upper()
        if mode in self._attr_options:
            return mode
        return None

    async def async_select_option(self, option: str) -> None:
        """Change SOLO/MUTE mode.

        0x1A toggles the mode. We read the current mode and only send the command
        if we need to switch; if current state is unknown we send once anyway.
        """
        current = self.current_option
        if current == option:
            _LOGGER.debug("Mode already %s, no command needed", option)
            return

        # Toggle to requested mode (0x1A flips SOLO ↔ MUTE)
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.send_command,
            RealiserA16Hex.CMD_ALL_TOGGLE,  # 0x1A
        )
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16PresetSelect(SelectEntity):
    """Select entity for loading User A or B presets (1–16)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:music-box-multiple"
    _attr_options = [f"Preset {n}" for n in range(1, 17)]

    # Base command codes per zone
    _PRESET_BASE = {"A": 0x70, "B": 0x90}
    # Status key that carries the current preset number
    _STATUS_KEY = {"A": "PA", "B": "PB"}

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str
    ) -> None:
        """Initialize the preset select."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._attr_unique_id = f"{coordinator.host}_preset_{self.zone.lower()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return f"Preset {self.zone}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        """Return the currently loaded preset as 'Preset N'.

        The coordinator status dict contains PA=01..16 (Zone A) or PB=01..16 (Zone B),
        populated from the 0x80 / 0xA0 response.
        """
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("status", {})
        raw = status.get(self._STATUS_KEY[self.zone], "").strip()
        try:
            n = int(raw)
            if 1 <= n <= 16:
                return f"Preset {n}"
        except (ValueError, TypeError):
            pass
        return None

    async def async_select_option(self, option: str) -> None:
        """Load the selected preset."""
        try:
            n = int(option.split()[-1])  # "Preset 3" → 3
        except (ValueError, IndexError):
            _LOGGER.warning("Invalid preset option: %s", option)
            return
        if not 1 <= n <= 16:
            _LOGGER.warning("Preset number out of range: %d", n)
            return

        cmd = self._PRESET_BASE[self.zone] + (n - 1)
        _LOGGER.debug("Loading preset %d for zone %s (cmd=0x%02x)", n, self.zone, cmd)
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.send_command, cmd
        )
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
