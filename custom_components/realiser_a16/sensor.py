"""Sensor entities for Realiser A16."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

# Volume range per PDF
VOLUME_MIN = RealiserA16Hex.VOLUME_MIN  # 27
VOLUME_MAX = RealiserA16Hex.VOLUME_MAX  # 99


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        RealiserA16VolumeSensor(coordinator, "A"),
        RealiserA16VolumeSensor(coordinator, "B"),
        RealiserA16PresetNameSensor(coordinator, "A"),
        RealiserA16PresetNameSensor(coordinator, "B"),
        RealiserA16StatusSensor(coordinator),
        RealiserA16SpeakerSensor(coordinator),
    ]
    async_add_entities(sensors)


class RealiserA16VolumeSensor(SensorEntity):
    """Volume sensor for a Realiser A16 user zone (raw value 27-99)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:volume-high"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = None  # dimensionless number

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str
    ) -> None:
        """Initialize the volume sensor."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._vol_key = "VA" if self.zone == "A" else "VB"
        self._attr_unique_id = f"{coordinator.host}_volume_{self.zone.lower()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Volume {self.zone}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> Optional[int]:
        """Return the raw volume value (27-99)."""
        status = (
            self.coordinator.data.get("status", {}) if self.coordinator.data else {}
        )
        val = status.get(self._vol_key)
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        vol = self.native_value
        if vol is None:
            return {}
        pct = round((vol - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN) * 100)
        return {
            "volume_percent": pct,
            "volume_min": VOLUME_MIN,
            "volume_max": VOLUME_MAX,
        }

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16PresetNameSensor(SensorEntity):
    """Sensor for preset name of a zone."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:folder-music"

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
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> Optional[str]:
        """Return the preset/headphone name."""
        status = (
            self.coordinator.data.get("status", {}) if self.coordinator.data else {}
        )
        # AQNAME = headphone EQ name for User A, BQNAME for User B
        key = "AQNAME" if self.zone == "A" else "BQNAME"
        val = status.get(key, "").strip()
        return val if val else None

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16StatusSensor(SensorEntity):
    """Diagnostic sensor for connection status."""

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
        if not self.coordinator.last_update_success:
            return "disconnected"
        return "connected"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        return {
            "host": self.coordinator.host,
            "port": self.coordinator.port,
            "last_update_success": self.coordinator.last_update_success,
        }

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16SpeakerSensor(SensorEntity):
    """Sensor exposing speaker overview (mode + per-speaker state) as attributes.

    native_value = number of visible speakers.
    extra_state_attributes = full speakers dict for use in Lovelace custom cards.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:speaker-multiple"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RealiserA16DataUpdateCoordinator) -> None:
        """Initialize the speaker sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_speakers"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Speakers"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> Optional[int]:
        """Return number of visible speakers."""
        speakers = (
            self.coordinator.data.get("speakers", {}) if self.coordinator.data else {}
        )
        if not speakers:
            return None
        return sum(1 for s in speakers.values() if s.get("visible", False))

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return full speaker state for Lovelace custom cards."""
        if not self.coordinator.data:
            return {}
        speakers = self.coordinator.data.get("speakers", {})
        assignments = self.coordinator.data.get("assignments", {})
        mode = assignments.get("global", {}).get("ALL", "UNKNOWN")

        # Serialise speakers with str keys (JSON-safe)
        speakers_serialized = {str(spk_id): info for spk_id, info in speakers.items()}
        return {
            "mode": mode,
            "speakers": speakers_serialized,
        }

    async def async_update_speakers(self) -> None:
        """Trigger an on-demand speaker refresh (call via service or button)."""
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.refresh_speakers
        )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
