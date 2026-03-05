"""Config flow for Realiser A16 integration."""

import logging
import socket
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant

from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)


class RealiserA16ConfigFlow(config_entries.ConfigFlow, domain="realiser_a16"):
    """Handle a config flow for Realiser A16."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._host = ""
        self._port = 4101
        self._timeout = 30.0  # Longer timeout for reliable connection
        self._update_interval = 10

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, 4101)
            self._timeout = user_input.get(CONF_TIMEOUT, 5.0)
            self._update_interval = user_input.get("update_interval", 10)

            # Test connection with retry logic
            try:
                await self._test_connection()

                await self.async_set_unique_id(f"{self._host}:{self._port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Realiser A16 ({self._host})",
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_TIMEOUT: self._timeout,
                        "update_interval": self._update_interval,
                    },
                )

            except ConnectionRefusedError:
                _LOGGER.error("Connection refused by device")
                errors["base"] = "cannot_connect"
            except socket.timeout:
                _LOGGER.error("Connection timeout")
                errors["base"] = "timeout"
            except OSError as err:
                _LOGGER.error("Network error: %s", err)
                errors["base"] = "network_error"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during connection test")
                errors["base"] = "unknown"

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host): str,
                vol.Optional(CONF_PORT, default=self._port): vol.All(
                    vol.Coerce(int), vol.Range(min=512, max=65535)
                ),
                vol.Optional(CONF_TIMEOUT, default=self._timeout): vol.All(
                    vol.Coerce(float), vol.Range(min=5.0, max=30.0)
                ),
                vol.Optional("update_interval", default=self._update_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=300)
                ),
            }
        )

        # More helpful error descriptions
        base_errors = {}
        if errors:
            base_errors["base"] = errors.get("base", "cannot_connect")
            # Add more detailed hints based on error type could be expanded

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "default_port": "4101",
                "default_interval": "10",
                "timeout": "15",
            },
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "default_port": "4101",
                "default_interval": "10",
            },
        )

    async def _test_connection(self):
        """Test connection to the A16 with retry and multiple commands."""
        client = None
        try:
            # Connect with longer timeout for initial handshake
            client = RealiserA16Hex(self._host, self._port, timeout=30.0)
            await self.hass.async_add_executor_job(client.connect)
            _LOGGER.debug("TCP connection established to %s:%s", self._host, self._port)

            # Try different commands - some A16 firmware versions only respond to certain commands
            # depending on state. Try STATUS first (quick), then ASSIGNMENTS, then VERSION.
            test_commands = [
                (0x45, "STATUS"),
                (0x37, "ASSIGNMENTS"),
                (0x40, "VERSION"),
                (0x41, "MODEL"),
                (0x01, "POWER_ON"),  # Some devices only respond after power command
            ]

            for cmd, name in test_commands:
                try:
                    _LOGGER.debug("Sending test command: 0x%02x (%s)", cmd, name)
                    response = await self.hass.async_add_executor_job(client.send, cmd)
                    if response:
                        _LOGGER.debug(
                            "Command 0x%02x (%s) successful: %s",
                            cmd,
                            name,
                            response[:200],
                        )
                        # We got a response - connection works!
                        return True
                    else:
                        _LOGGER.debug(
                            "Command 0x%02x (%s) returned empty response", cmd, name
                        )
                except socket.timeout:
                    _LOGGER.debug(
                        "Command 0x%02x (%s) timed out, trying next...", cmd, name
                    )
                    continue
                except Exception as err:
                    _LOGGER.debug("Command 0x%02x (%s) failed: %s", cmd, name, err)
                    continue

            # No command succeeded
            _LOGGER.warning(
                "All test commands failed - device may not support TCP protocol"
            )
            return False

        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
