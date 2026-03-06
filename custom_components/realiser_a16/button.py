"""Button entities for Realiser A16 volume control."""

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)


@dataclass
class RealiserButtonDescription(ButtonEntityDescription):
    """Describes a Realiser A16 button."""

    command: int = 0


BUTTON_DESCRIPTIONS: tuple[RealiserButtonDescription, ...] = (
    RealiserButtonDescription(
        key="volume_a_up",
        name="Volume A Up",
        icon="mdi:volume-plus",
        command=RealiserA16Hex.CMD_VOL_A_UP,
    ),
    RealiserButtonDescription(
        key="volume_a_down",
        name="Volume A Down",
        icon="mdi:volume-minus",
        command=RealiserA16Hex.CMD_VOL_A_DN,
    ),
    RealiserButtonDescription(
        key="volume_b_up",
        name="Volume B Up",
        icon="mdi:volume-plus",
        command=RealiserA16Hex.CMD_VOL_B_UP,
    ),
    RealiserButtonDescription(
        key="volume_b_down",
        name="Volume B Down",
        icon="mdi:volume-minus",
        command=RealiserA16Hex.CMD_VOL_B_DN,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RealiserA16Button(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
    )


class RealiserA16Button(ButtonEntity):
    """A button that sends a single command to the Realiser A16."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RealiserA16DataUpdateCoordinator,
        description: RealiserButtonDescription,
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Send the command and refresh data."""
        _LOGGER.debug(
            "Button pressed: %s (0x%02x)",
            self.entity_description.key,
            self.entity_description.command,
        )
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, self.entity_description.command
        )
        await self.coordinator.async_request_refresh()
