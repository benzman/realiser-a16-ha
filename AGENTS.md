# AGENTS.md - Guidelines for Agentic Coding Assistants

## Build, Lint, Test Commands

### Environment Setup
```bash
# Create virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (none beyond HA itself)
# No external requirements needed - uses Python stdlib only
```

### Linting/Type Checking
```bash
# Ruff (if available)
ruff check custom_components/realiser_a16/

# Basic Python syntax check
python3 -m py_compile custom_components/realiser_a16/*.py

# Type checking with mypy (optional)
mypy custom_components/realiser_a16/ --ignore-missing-imports
```

### Testing
```bash
# Run integration in Home Assistant (dev mode)
# 1. Copy/c symlink to HA custom_components
cd /path/to/homeassistant
# Link: ln -s /path/to/this/repo/custom_components/realiser_a16 custom_components/

# 2. Restart HA and check logs
tail -f home-assistant.log | grep -i realiser

# Test config flow manually:
# - Settings → Devices & Services → Add Integration → Realiser A16
# - Enter IP: 192.168.160.19, Port: 4101
```

### Single Test Simulation
```bash
# Comprehensive integration test (recommended)
python3 test_integration.py 192.168.160.19

# Basic TCP client test
python3 test_connection.py

# Simpler test with explicit path
python3 test_connection_simple.py

# Or import directly in Python
python3 -c "
from custom_components.realiser_a16.realiser_a16_hex import RealiserA16Hex
with RealiserA16Hex('192.168.160.19', 4101) as amp:
    print('VERSION:', amp.get_version())
    print('STATUS:', amp.get_status())
    print('PRESET A:', amp.get_preset_a()[:200])
"
```

### Quick Commands (from project root)
```bash
# Run ruff linter
ruff check custom_components/

# Syntax check
python3 -m py_compile custom_components/realiser_a16/*.py

# Type check (optional)
mypy custom_components/realiser_a16/ --ignore-missing-imports
```

### Manifest (manifest.json required fields)
```json
{
  "domain": "realiser_a16",
  "name": "Realiser A16",
  "codeowners": ["@yourname"],
  "config_flow": true,
  "documentation": "https://github.com/yourrepo/realiser-a16-firmware",
  "integration_type": "device",
  "iot_class": "local_polling",
  "requirements": [],
  "version": "0.0.1"
}
```

## Code Style Guidelines

### Imports
- **Order**: Standard library → third-party → Home Assistant → local
- **Group with blank lines** between sections
- **Absolute imports** within the integration: `from .realiser_a16_hex import RealiserA16Hex`
- **Never** use `from module import *`

Example:
```python
import logging
from typing import Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .realiser_a16_hex import RealiserA16Hex
```

### Formatting
- **Indentation**: 4 spaces (no tabs)
- **Line length**: 100-120 characters max
- **Trailing commas** in multi-line collections (yes)
- **Blank lines**: 2 between top-level functions/classes, 1 between methods
- **No trailing whitespace**

### Type Hints
- **Required** for all function signatures and public methods
- Use `Optional[...]` for nullable values
- Use explicit return types: `def foo() -> str:`
- Type hints on class attributes via comments if needed:
  ```python
  self._connected: bool = False
  ```

### Naming Conventions
- **Files/modules**: `snake_case.py` (lowercase with underscores)
- **Classes**: `PascalCase` (e.g., `RealiserA16ConfigFlow`)
- **Functions/methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private/internal**: leading underscore `_private_var`
- **Entity unique_id**: `{host}_{zone}` format

### Home Assistant Specifics

#### Entity Naming
- **Entity IDs**: `realiser_a16_zone_a`, `realiser_a16_all_solo`
- **Device Info**: Always populate `device_info` with identifiers, manufacturer, model
- **Entity Category**: Use `EntityCategory.DIAGNOSTIC` for sensors, `CONFIG` for setup entities
- **Has Entity Name**: Set `_attr_has_entity_name = True` and `_attr_name = None`

#### Coordinator Pattern
- All platform entities must use `DataUpdateCoordinator`
- Implement `async_added_to_hass()` to register listener:
  ```python
  async def async_added_to_hass(self):
      await super().async_added_to_hass()
      self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
  ```
- Access data via `self.coordinator.data` (dict) not attributes

#### Config Flow
- Class name: `{IntegrationName}ConfigFlow`
- Inherit: `config_entries.ConfigFlow, domain="realiser_a16"`
- Set `VERSION = 1` and increment on schema changes
- Use `async_set_unique_id()` to prevent duplicates
- Test connection in `async_step_user()` before creating entry

### Error Handling
- **Log exceptions**: `_LOGGER.exception("message")` for unexpected errors
- **User-friendly errors**: Use `errors["base"] = "cannot_connect"` in config flow
- **Connection failures**: Always handle socket timeouts/errors gracefully
- **Data parsing**: Be tolerant of missing/invalid fields, use `.get()` with defaults

### Network/IO
- **Blocking calls** MUST use `await self.hass.async_add_executor_job()`
- Never block event loop with `socket` operations directly
- Use context managers for sockets (`with RealiserA16Hex(...) as amp:`)
- Set reasonable timeouts (default 5s for connection, 1-2s for commands)

### Data Structures
The coordinator data dict must contain:
```python
{
    "connected": bool,
    "status": Dict[str, str],      # from 0x45
    "assignments": Dict,            # parsed from 0x37
    "preset_a": Dict[str, str],    # parsed from 0x46
    "preset_b": Dict[str, str],    # parsed from 0x47
}
```

### Protocol Implementation (realiser_a16_hex.py)
- Send: `f"{code:02x}\r\n".encode('ascii')`
- Receive: Loop until `\x00` received
- Return: `resp.decode('ascii', errors='ignore')` (without null terminator)
- Keep client stateless; connect per-session

### Documentation References
- **Device Commands**: See `commands.md` for complete list of IP commands (0x11-0xa0)
- **HA Integration**: Follow Home Assistant integration guidelines

### Documentation
- **Docstrings** for all public classes/functions (Google style):
  ```python
  def method(self, param: int) -> str:
      """Short description.
      
      Longer description if needed.
      
      Args:
          param: Description
      
      Returns:
          Description
      """
  ```
- **Inline comments** only for non-obvious logic
- **TODOs**: Always include `TODO:` with explanation

### Testing Checklist
Before committing:
- [ ] Code is PEP8 compliant (4 spaces, proper blank lines)
- [ ] All functions have type hints
- [ ] All HA entities implement required properties
- [ ] Config flow tests connection before creating entry
- [ ] No blocking calls in async methods
- [ ] Proper error handling and logging
- [ ] Unique IDs are stable across restarts
- [ ] Device info is complete

### Pull Request Guidelines
- Keep PRs small and focused (one feature/bugfix per PR)
- Update README.md if user-facing changes
- Update manifest.json version for releases
- Test with actual A16 hardware before merging
- Do not commit any binary firmware files (*.SVS, *.dc7) or captures

## Repository-Specific Notes

- Integration domain: **realiser_a16**
- Default port: **4101** (configurable 512-65535)
- Polling interval: **10 seconds** (configurable 5-300s)
- Protocol: Hex commands + `\r\n`, responses null-terminated
- Entities: 2x media_player, 2x sensor, 1x switch, 1x select
- Device Protocol: See `commands.md` for complete command list

## Gotchas
- HACS requires `config_flow: true` in manifest
- Config Flow class MUST have `domain="realiser_a16"` as second base
- FlowResult must be imported from `homeassistant.core`, not `data_entry_flow`
- Manifest version must match git tag for HACS downloads
- Never use `voluptuous` in production code directly - it's HA dependency
