"""Switch entities for Realiser A16."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN, CONF_SPEAKER_SWITCHES
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switch entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list = [
        RealiserA16PowerSwitch(coordinator),
        RealiserA16AllSoloSwitch(coordinator),
    ]

    # Add per-speaker switches only when explicitly enabled in config
    if entry.data.get(CONF_SPEAKER_SWITCHES, False):
        entities.extend(
            RealiserA16SpeakerSwitch(coordinator, speaker_id)
            for speaker_id in range(1, 51)
        )

    async_add_entities(entities)


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

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


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
        if not self.coordinator.data:
            return False
        mode = self.coordinator.data.get("speaker_mode", "")
        return (mode or "").upper() == "SOLO"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        return {"speaker_mode": self.coordinator.data.get("speaker_mode", "")}

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

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class RealiserA16SpeakerSwitch(SwitchEntity):
    """Switch for individual speaker solo/mute control.

    In SOLO mode: turns this speaker on = solos it; off = unsolos (sends command again).
    In MUTE mode: turns off = mutes it; on = activates it.
    The command (0xB0 + speaker_id) toggles the speaker state.
    """

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False  # Only active when speaker is visible

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, speaker_id: int
    ) -> None:
        """Initialize the speaker switch."""
        self.coordinator = coordinator
        self.speaker_id = speaker_id
        name = RealiserA16Hex.SPEAKER_NAMES.get(speaker_id, f"Spk{speaker_id}")
        self._speaker_name = name
        self._attr_unique_id = f"{coordinator.host}_speaker_{speaker_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return f"Speaker {self._speaker_name}"

    @property
    def icon(self) -> str:
        """Return icon based on speaker type."""
        if self.speaker_id == 4:  # SW = subwoofer
            return "mdi:speaker-wireless"
        return "mdi:speaker"

    @property
    def available(self) -> bool:
        """Return availability based on coordinator and speaker visibility."""
        if not self.coordinator.last_update_success:
            return False
        speakers = (
            self.coordinator.data.get("speakers", {}) if self.coordinator.data else {}
        )
        spk = speakers.get(self.speaker_id)
        if spk is None:
            return False
        return spk.get("visible", False)

    @property
    def is_on(self) -> bool:
        """Return true if speaker is active (not muted)."""
        if not self.coordinator.data:
            return False
        speakers = self.coordinator.data.get("speakers", {})
        spk = speakers.get(self.speaker_id)
        if spk is None:
            return False
        return spk.get("state") == "active"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate/solo this speaker (sends toggle command)."""
        cmd = RealiserA16Hex.CMD_SPEAKER_BASE + self.speaker_id
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Mute/deactivate this speaker (sends toggle command again)."""
        cmd = RealiserA16Hex.CMD_SPEAKER_BASE + self.speaker_id
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
