"""Button entities for Realiser A16."""

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            RealiserA16RefreshSpeakersButton(coordinator),
        ]
    )


class RealiserA16RefreshSpeakersButton(ButtonEntity):
    """Button to manually refresh speaker status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"
    _attr_entity_category = None  # Not diagnostic, it's an action button

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_refresh_speakers_button"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Refresh Speaker Status"

    async def async_press(self) -> None:
        """Handle the button press - refresh speaker data."""
        await self.hass.async_add_executor_job(self.coordinator.refresh_speakers)
        # Also trigger a coordinator refresh to update all entities
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
