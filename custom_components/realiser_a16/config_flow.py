"""Config flow for Realiser A16 integration."""

import logging
import socket

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT

from .realiser_a16_hex import RealiserA16Hex

_LOGGER = logging.getLogger(__name__)

VOLUPTUOUS_IMPORTED = False
try:
    import voluptuous as vol

    VOLUPTUOUS_IMPORTED = True
except ImportError:
    import homeassistant.helpers.config_validation as vol


class RealiserA16ConfigFlow(config_entries.ConfigFlow, domain="realiser_a16"):
    """Handle a config flow for Realiser A16."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._host = ""
        self._port = 4101
        self._timeout = 30.0
        self._update_interval = 10

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        _LOGGER.info("Config flow started with input: %s", user_input)

        if user_input is not None:
            self._host = user_input.get(CONF_HOST, "")
            self._port = user_input.get(CONF_PORT, 4101)
            self._timeout = user_input.get(CONF_TIMEOUT, 30.0)
            self._update_interval = user_input.get("update_interval", 10)

            _LOGGER.info("Testing connection to %s:%s", self._host, self._port)

            # Test connection
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

            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("Connection test failed: %s", exc)
                errors["base"] = "cannot_connect"

        # Build schema
        schema = {
            vol.Required(CONF_HOST, default=self._host): str,
            vol.Optional(CONF_PORT, default=self._port): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_TIMEOUT, default=self._timeout): vol.All(
                vol.Coerce(float), vol.Range(min=1.0, max=60.0)
            ),
            vol.Optional("update_interval", default=self._update_interval): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=3600)
            ),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"host": "192.168.x.x", "port": "4101"},
        )

    async def _test_connection(self):
        """Test connection to the A16."""
        _LOGGER.info("Starting connection test to %s:%s", self._host, self._port)

        def sync_test():
            try:
                client = RealiserA16Hex(self._host, self._port, timeout=self._timeout)
                _LOGGER.debug("Client created, connecting...")
                client.connect()
                _LOGGER.debug("Connected! Sending STATUS command (0x45)...")
                resp = client.send(0x45)
                _LOGGER.debug("Got response: %s", repr(resp[:100]) if resp else "EMPTY")
                client.close()
                return resp
            except Exception as e:
                _LOGGER.exception("sync_test failed: %s", e)
                raise

        result = await self.hass.async_add_executor_job(sync_test)

        if not result:
            _LOGGER.error("Empty response received from device")
            raise Exception("No valid response from device")

        _LOGGER.info("Connection test successful!")
        return True
