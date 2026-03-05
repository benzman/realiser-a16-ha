"""Switch entities for Realiser A16."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switch entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RealiserA16PowerSwitch(coordinator),
            RealiserA16AllSoloSwitch(coordinator),
        ]
    )


class RealiserA16PowerSwitch(SwitchEntity):
    """Switch for Power/Standby."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:power"
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_power"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return "Power"

    @property
    def is_on(self) -> bool:
        """Return true if powered on."""
        status = self.coordinator.data.get("status", {})
        pwr = status.get("PWR", "").upper()
        if pwr:
            return pwr == "ON"
        return True  # No PWR field = device is on (returns preset data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on power."""
        await self.hass.async_add_executor_job(self.coordinator.send_command, 0x2C)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off power (standby)."""
        await self.hass.async_add_executor_job(self.coordinator.send_command, 0x2D)
        await self.coordinator.async_request_refresh()


class RealiserA16AllSoloSwitch(SwitchEntity):
    """Switch for ALL Solo/Mute mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:account-voice"
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_all_solo"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return "All Solo"

    @property
    def is_on(self) -> bool:
        """Return true if mode is SOLO."""
        assignments = self.coordinator.data.get("assignments", {})
        mode = assignments.get("global", {}).get("MODE", "").upper()
        return mode == "SOLO"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        assignments = self.coordinator.data.get("assignments", {})
        return {
            "test_mode": assignments.get("global", {}).get("TEST", ""),
            "all_mode": assignments.get("global", {}).get("ALL", ""),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on solo mode."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, 0x56
        )  # ALL SOLO
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off solo (mute all)."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, 0x57
        )  # ALL MUTE
        await self.coordinator.async_request_refresh()
