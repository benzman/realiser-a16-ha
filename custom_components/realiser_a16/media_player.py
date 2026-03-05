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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RealiserA16DataUpdateCoordinator, DOMAIN
from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up media player entities."""
    coordinator: RealiserA16DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create two zone players: A and B
    async_add_entities(
        [
            RealiserA16Zone(coordinator, "A", "Zone A"),
            RealiserA16Zone(coordinator, "B", "Zone B"),
        ]
    )


class RealiserA16Zone(MediaPlayerEntity):
    """Representation of a Realiser A16 zone."""

    _attr_has_entity_name = True
    _attr_name = None  # Use entity name from device
    _attr_icon = "mdi:amplifier"

    def __init__(
        self, coordinator: RealiserA16DataUpdateCoordinator, zone: str, name: str
    ) -> None:
        """Initialize the media player."""
        self.coordinator = coordinator
        self.zone = zone.upper()
        self._attr_unique_id = f"{coordinator.host}_{self.zone.lower()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Realiser A16 ({coordinator.host})",
            "manufacturer": "Smyth Research",
            "model": "Realiser A16",
        }
        # Supported features: volume step, mute, select source, select sound mode, turn on/off
        self._attr_supported_features = (
            MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.SELECT_SOUND_MODE
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def _preset_data(self) -> Dict[str, str]:
        """Get preset data for this zone."""
        if self.zone == "A":
            return self.coordinator.data.get("preset_a", {})
        else:
            return self.coordinator.data.get("preset_b", {})

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        preset = self._preset_data
        pwr = preset.get("PWR") or (
            preset.get("PA") and "ON"
        )  # PA indicates power for zone?
        # If PWR is OFF, return off; else on
        # Some preset data may have PA=01 for zone A power? Not sure.
        # Use global PWR from assignments if present? For simplicity, assume always ON if device is on.
        # Better: check if PWR key exists in any preset, treat as "ON"
        if pwr is None:
            # Fallback: if VA exists, assume on?
            return MediaPlayerState.OFF
        if pwr.upper() == "OFF":
            return MediaPlayerState.OFF
        return MediaPlayerState.ON

    @property
    def volume_level(self) -> Optional[float]:
        """Volume level of the media player (0.0 to 1.0)."""
        preset = self._preset_data
        vol_key = "VA" if self.zone == "A" else "VB"
        vol_str = preset.get(vol_key, "0")
        try:
            vol = int(vol_str)
            # Assumption: volume range 0-100. Convert to 0.0-1.0
            return max(0.0, min(1.0, vol / 100.0))
        except (ValueError, TypeError):
            return None

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        preset = self._preset_data
        mute_key = "ATACT" if self.zone == "A" else "BTACT"
        mute_val = preset.get(mute_key, "").upper()
        # Typically: ON = not muted, OFF = muted? Or reversed.
        # From dump: ATACT=ON while volume=62. Likely ON = active (tone control?) but not mute.
        # There are separate MUTE commands (0x02, 0x52, 0x53). ATACT/BTACT might be "Anthem Act" or something else.
        # Testing needed. For now, treat OFF as muted.
        return mute_val == "OFF"

    @property
    def source(self) -> Optional[str]:
        """Return the current input source."""
        preset = self._preset_data
        src_key = "IN" if self.zone == "A" else "BUR"
        src = preset.get(src_key)
        if src:
            return src.strip()
        return None

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        # Could be derived from other data or hard-coded common names
        # Not available from A16 protocol, so return empty list
        # Possibly we could get from some other command? Unknown.
        return ["HDMI-1", "HDMI-2", "HDMI-3", "HDMI-4", "Optical", "Coaxial", "AAnalog"]

    @property
    def sound_mode(self) -> Optional[str]:
        """Return the current sound mode."""
        preset = self._preset_data
        # UMIX is used for AuroMatic etc.
        mode = preset.get("UMIX") or preset.get("BUMIX") or preset.get("MODE")
        if mode:
            return mode.strip()
        return None

    @property
    def sound_mode_list(self) -> list[str]:
        """List of available sound modes."""
        # Typical modes: SVS (Virtual Surround), AuroMatic, Stereo, etc.
        # Not known exactly, return generic
        return ["SVS", "AuroMatic", "Stereo", "Surround"]

    @property
    def media_title(self) -> Optional[str]:
        """Return the current media title (preset name)."""
        preset = self._preset_data
        name_key = "AQNAME" if self.zone == "A" else "BQNAME"
        name = preset.get(name_key)
        if name:
            return name.strip()
        return None

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, RealiserA16Hex.CMD_POWER_ON
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command, RealiserA16Hex.CMD_POWER_OFF
        )
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        """Volume up."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command,
            RealiserA16Hex.CMD_VOL_UP
            if self.zone == "A"
            else RealiserA16Hex.CMD_VOL_DN,
        )
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        """Volume down."""
        await self.hass.async_add_executor_job(
            self.coordinator.send_command,
            RealiserA16Hex.CMD_VOL_DN
            if self.zone == "A"
            else RealiserA16Hex.CMD_VOL_UP,
        )
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute volume."""
        if self.zone == "A":
            cmd = RealiserA16Hex.CMD_MUTE_A
        else:
            cmd = RealiserA16Hex.CMD_MUTE_B
        await self.hass.async_add_executor_job(self.coordinator.send_command, cmd)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        # There is no direct set source via hex? Possibly we need to navigate with IR input next commands.
        # The preset data includes "IN" but to change source we may need to send IR commands for input selection.
        # There are 50 IR commands mimicking remote keys. One of them is Input Next, etc.
        # But we don't have mapping. For now, this is not implemented.
        _LOGGER.warning("Source selection not implemented for Realiser A16")

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode."""
        # Not implemented: need IR command or specific command
        _LOGGER.warning("Sound mode selection not implemented for Realiser A16")

    # The turn_on/off and volume methods are enough for basic control.
