"""Media player entities for Realiser A16 zones."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

VOLUME_MIN = RealiserA16Hex.VOLUME_MIN  # 27
VOLUME_MAX = RealiserA16Hex.VOLUME_MAX  # 99


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up media player entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            RealiserA16Zone(coordinator, "A"),
            RealiserA16Zone(coordinator, "B"),
        ]
    )


class RealiserA16Zone(MediaPlayerEntity):
    """Media player entity for a Realiser A16 user zone."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:amplifier"
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str
    ) -> None:
        """Initialize the media player."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._attr_unique_id = f"{coordinator.host}_zone_{self.zone.lower()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }

    @property
    def name(self) -> str:
        """Return the name."""
        return f"Zone {self.zone}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def _status(self) -> Dict[str, str]:
        """Shortcut to coordinator status dict."""
        if self.coordinator.data:
            return self.coordinator.data.get("status", {})
        return {}

    @property
    def state(self) -> MediaPlayerState:
        """Return the state based on PWR key."""
        pwr = self._status.get("PWR", "").upper()
        if pwr in ("STANDBY", "OFF", "BOOT"):
            return MediaPlayerState.OFF
        if pwr == "ON":
            return MediaPlayerState.ON
        # Fallback: if VA exists, device is on
        if self._status.get("VA"):
            return MediaPlayerState.ON
        return MediaPlayerState.OFF

    @property
    def volume_level(self) -> Optional[float]:
        """Return volume mapped from 27-99 to 0.0-1.0."""
        vol_key = "VA" if self.zone == "A" else "VB"
        val = self._status.get(vol_key)
        if val is None:
            return None
        try:
            vol = int(val)
            return max(0.0, min(1.0, (vol - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN)))
        except (ValueError, TypeError):
            return None

    @property
    def is_volume_muted(self) -> bool:
        """Return mute state from MUTEA/MUTEB key."""
        mute_key = "MUTEA" if self.zone == "A" else "MUTEB"
        return self._status.get(mute_key, "").upper() == "MUTE"

    @property
    def source(self) -> Optional[str]:
        """Return the current input source (Zone A only via IN=)."""
        if self.zone == "A":
            return self._status.get("IN", "").strip() or None
        return None

    @property
    def source_list(self) -> list[str]:
        """Return list of available input sources."""
        return [
            "eARC",
            "HDMI-1",
            "HDMI-2",
            "HDMI-3",
            "HDMI-4",
            "USB",
            "LINE",
            "STEREO",
            "COAXIAL",
            "OPTICAL",
        ]

    @property
    def media_title(self) -> Optional[str]:
        """Return current preset/headphone name."""
        key = "AQNAME" if self.zone == "A" else "BQNAME"
        return self._status.get(key, "").strip() or None

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, RealiserA16Hex.CMD_POWER_ON
        )
        # Full refresh after power change
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Put the device into standby."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, RealiserA16Hex.CMD_POWER_OFF
        )
        # Full refresh after power change
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        """Increase volume by one step."""
        cmd = (
            RealiserA16Hex.CMD_VOL_A_UP
            if self.zone == "A"
            else RealiserA16Hex.CMD_VOL_B_UP
        )
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        # No full refresh - volume change is local, will be updated on next poll

    async def async_volume_down(self) -> None:
        """Decrease volume by one step."""
        cmd = (
            RealiserA16Hex.CMD_VOL_A_DN
            if self.zone == "A"
            else RealiserA16Hex.CMD_VOL_B_DN
        )
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        # No full refresh

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute/unmute (toggle - the A16 toggles on each MUTE command)."""
        cmd = (
            RealiserA16Hex.CMD_MUTE_A if self.zone == "A" else RealiserA16Hex.CMD_MUTE_B
        )
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        # No full refresh - will be updated on next poll

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        source_map = {
            "eARC": RealiserA16Hex.CMD_SOURCE_EARC,
            "HDMI-1": RealiserA16Hex.CMD_SOURCE_HDMI1,
            "HDMI-2": RealiserA16Hex.CMD_SOURCE_HDMI2,
            "HDMI-3": RealiserA16Hex.CMD_SOURCE_HDMI3,
            "HDMI-4": RealiserA16Hex.CMD_SOURCE_HDMI4,
            "USB": RealiserA16Hex.CMD_SOURCE_USB,
            "LINE": RealiserA16Hex.CMD_SOURCE_LINE,
            "STEREO": RealiserA16Hex.CMD_SOURCE_STEREO,
            "COAXIAL": RealiserA16Hex.CMD_SOURCE_COAXIAL,
            "OPTICAL": RealiserA16Hex.CMD_SOURCE_OPTICAL,
        }
        cmd = source_map.get(source)
        if cmd is None:
            _LOGGER.warning("Unknown source: %s", source)
            return
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        # Source change triggers internal update, will be picked up on next poll

    async def async_added_to_hass(self) -> None:
        """Register update listener."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
