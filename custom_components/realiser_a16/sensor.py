"""Sensor entities for Realiser A16."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        RealiserA16PresetNameSensor(coordinator, "A"),
        RealiserA16PresetNameSensor(coordinator, "B"),
        RealiserA16AssignmentsSensor(coordinator),
        RealiserA16StatusSensor(coordinator),
    ]
    async_add_entities(sensors)


class RealiserA16PresetNameSensor(SensorEntity):
    """Sensor for preset name of a zone."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:folder"

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._attr_unique_id = f"{coordinator.host}_preset_{self.zone.lower()}_name"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Preset {self.zone} Name"

    @property
    def native_value(self) -> Optional[str]:
        """Return the preset name."""
        preset_data = self.coordinator.data.get(f"preset_{self.zone.lower()}", {})
        name_key = "AQNAME" if self.zone == "A" else "BQNAME"
        value = preset_data.get(name_key, "").strip()
        return value if value else None


class RealiserA16AssignmentsSensor(SensorEntity):
    """Sensor for speaker assignments."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:speaker"
    _attr_entity_registry_enabled_default = False  # Advanced, hidden by default

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_assignments"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return "Speaker Assignments"

    @property
    def native_value(self) -> str:
        """Return a summary of assignments."""
        assignments = self.coordinator.data.get("assignments", {})
        ach_count = len(assignments.get("ach", {}))
        bch_count = len(assignments.get("bch", {}))
        mode = assignments.get("global", {}).get("MODE", "unknown")
        return f"{ach_count} A-ch, {bch_count} B-ch, MODE={mode}"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the full assignment data."""
        return {"assignments": self.coordinator.data.get("assignments", {})}


class RealiserA16StatusSensor(SensorEntity):
    """Sensor for connection status and basic info."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:connection"

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return "Connection Status"

    @property
    def native_value(self) -> str:
        """Return connection status."""
        return "connected" if self.coordinator._connected else "disconnected"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        data = self.coordinator.data
        return {
            "host": self.coordinator.host,
            "port": self.coordinator.port,
            "last_update": self.coordinator.last_update_success,
        }
