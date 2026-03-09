# Realiser A16 Home Assistant Integration

⚠️ **Under Construction** ⚠️

This integration is still in active development and is not yet ready for production use. Some features are incomplete, experimental, or may not work as expected. You may encounter bugs or unexpected behavior. This integration is provided "as-is" and the API/behavior may change as development continues.

## Features

- **Media Player** entities for Zone A and Zone B:
  - Power on/off (via dedicated power switch)
  - Volume up/down (via service calls)
  - Mute toggle
  - Display current input source
  - Display current sound mode
  - Show preset name as media title

- **Sensors**:
  - Preset names for both zones
  - Speaker assignments (detailed mapping)
  - Connection status
  - Power status (on/standby)
  - Speaker overview (for custom Lovelace cards)

- **Switches**:
  - Power toggle (standby/on)
  - All Solo / All Mute toggle
  - **Individual speaker switches** - mute/solo for each of up to 50 speakers (requires enable_speaker_switches: true in config)

- **Automatic polling** (configurable, default 10 seconds)
- **Input source selection** via select entity
- **Custom Lovelace Card** - Realiser Speaker Grid with visual speaker layout (optional)

## Prerequisites

1. Your Realiser A16 must have the **TCP Command Server enabled**:
   - Go to Settings → Network on the A16
   - Enable "TCP Command Server"
   - Note the IP address and port (default: 4101)

2. Ensure your Home Assistant can reach the A16 on the network.

## Installation

### Option 1: Manual (git clone)

1. Clone this repository into your Home Assistant `custom_components` directory:

```bash
cd /path/to/your/homeassistant
git clone <this-repo-url> custom_components/realiser_a16
```

2. Restart Home Assistant.

3. Go to **Settings → Devices & Services → Add Integration** and search for "Realiser A16".

4. Enter the IP address and port of your A16.

5. Configure the update interval (default: 10 seconds).
6. (Optional) Enable "Speaker switches" to get individual speaker control switches.

### Option 2: HACS (recommended)

1. Add this repository to HACS:
   - Open HACS in Home Assistant
   - Go to **Integrations**
   - Click the three dots → **Custom repositories**
   - Add the repository URL and category "Integration"

2. Install "Realiser A16" from HACS.

3. Restart Home Assistant.

4. Set up via **Settings → Devices & Services → Add Integration**.

## Lovelace Custom Card (Optional)

For a visual speaker grid overview similar to the A16's web interface, you can install the optional Realiser Speaker Card:

1. Copy `custom-cards/realiser-speaker-card/realiser-speaker-card.js` to your Home Assistant `/www/` directory.
2. In Lovelace → Settings (three dots) → **Ressourcen**, add:
   - Type: `JavaScript Module`
   - URL: `/local/realiser-speaker-card.js?v=1`
3. Add the card to your dashboard:
   ```yaml
   type: custom:realiser-speaker-card
   entity: sensor.realiser_a16_speakers
   ```

See `custom-cards/realiser-speaker-card/README.md` for detailed documentation.

## Supported Entities

After setup, the following entities are created:

### Media Players
- `media_player.realiser_a16_zone_a`
- `media_player.realiser_a16_zone_b`

### Sensors
- `sensor.realiser_a16_zone_a_preset_name`
- `sensor.realiser_a16_zone_b_preset_name`
- `sensor.realiser_a16_assignments`
- `sensor.realiser_a16_status`
- `sensor.realiser_a16_speakers` - Provides speaker overview for custom cards (includes all 52 speaker positions with visibility and state)
- `sensor.realiser_a16_power_status` (optional)

### Switches
- `switch.realiser_a16_power` - Standby/On toggle
- `switch.realiser_a16_all_solo` - All Solo / All Mute toggle
- **`switch.realiser_a16_speaker_*` (1-50)** - Individual speaker mute/solo switches (50 entities). Only created when `enable_speaker_switches: true` is set in config options.

### Selects
- `select.realiser_a16_input_source` - Select input source (eARC, HDMI1-4, USB, LINE, STEREO, COAXIAL, OPTICAL)

### Not Yet Implemented / Planned
- Volume control via number entities (requires further reverse engineering of command format)
- Direct volume set commands (currently only IR-based up/down available)
- Sound mode presets beyond preset names
- More detailed status information beyond basic on/off and input source
- Integration with the individual speaker switches in the main UI (speaker switches are available but not exposed in the default dashboard)

## Current Limitations

This integration is still being developed and has the following known limitations:

- **Volume Control**: Only supports volume up/down via service calls. Absolute volume setting requires further protocol research.
- **IR-Dependent Features**: Some functionality relies on IR commands which may not work reliably with all TV setups.
- **Protocol Status**: Commands are reverse-engineered from Wireshark captures and partial documentation; some command behaviors may change or be undocumented.
- **Polling Overhead**: Continuous polling (default 10s) may impact performance if the A16 has limited processing power.
- **Error Handling**: Some error conditions may not be gracefully handled yet.

## Protocol Documentation

This integration uses the official Realiser A16 TCP IP Command Protocol.

- Commands are sent as 2-digit hexadecimal numbers followed by `\r\n`.
- Responses are ASCII strings terminated with a null byte (`\x00`).

### Commands Used by This Integration

**Power Control:**
- `0x2C`: Power ON
- `0x2D`: Power OFF
- `0x2E`: Power Status (returns `PWR=ON` or `PWR=STANDBY`)

**Status Queries:**
- `0x45`: Get Status (legacy - returns preset data when powered on)
- `0x37`: Get Speaker Assignments (zone mapping)
- `0x64`: Get Firmware Version

**Presets:**
- `0x46`: Get Preset A (full preset data)
- `0x47`: Get Preset B (full preset data)
- `0x70-0x77`: Load Preset A (presets 1-8)
- `0x97-0x9F`: Load Preset B (presets 8-16)

**Input Selection:**
- `0x20`: Select eARC
- `0x21`: Select HDMI 1
- `0x22`: Select HDMI 2
- `0x23`: Select HDMI 3
- `0x24`: Select HDMI 4
- `0x25`: Select USB
- `0x26`: Select LINE
- `0x27`: Select STEREO
- `0x28`: Select COAXIAL
- `0x29`: Select OPTICAL

**Zone Selection:**
- `0x06`: Select Zone A
- `0x07`: Select Zone B

For the complete command list, see `commands.md` in this repository.

## Troubleshooting

### "Connection failed" error
- Verify the A16's IP address and port are correct.
- Ensure the TCP Command Server is enabled on the A16.
- Check firewall settings on your network.

### No data updates
- Try reducing the update interval in the integration options.
- Check if the A16 is responsive using `telnet <ip> <port>`.

### Volume control not working
The exact command format for setting absolute volume is not yet documented. Currently only volume up/down IR commands are implemented.

## Development

This integration is based on reverse engineering of the protocol from Wireshark captures and the official documentation. The project is actively under development with new features being added regularly.

### File Structure
```
custom_components/realiser_a16/
├── __init__.py              # Config flow, coordinator
├── realiser_a16_hex.py      # Low-level TCP client
├── media_player.py          # Zone media players
├── sensor.py                # Sensors
├── switch.py                # Switches
├── number.py                # Volume numbers (TODO)
└── manifest.json            # Integration metadata
```

## License

MIT License - Use at your own risk.

## Disclaimer

This integration is not officially supported by Smyth Research. It is provided as-is for experimental and development purposes only. The authors are not responsible for any damage to your equipment or data loss resulting from use of this software.

## Credits

- Protocol documentation: "A16-IP-command-server-May-2020-1.pdf" by S. Smyth, Smyth Research.
- Integration developed by benzman.
