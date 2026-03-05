"""Select entities for Realiser A16 input selection."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

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
        """Return the currently selected input."""
        preset = self.coordinator.data.get(f"preset_{self.zone.lower()}", {})
        key = "IN" if self.zone == "A" else "BUR"
        value = preset.get(key, "").strip()
        # Normalize: remove extra spaces, ensure matches options
        if value in self._attr_options:
            return value
        # Try partial match (e.g., "HDMI-1 " with trailing space)
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
