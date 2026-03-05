"""Config flow for Realiser A16 integration."""

import logging
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
        self._timeout = 5.0
        self._update_interval = 10

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, 4101)
            self._timeout = user_input.get(CONF_TIMEOUT, 5.0)
            self._update_interval = user_input.get("update_interval", 10)

            # Test connection
            try:
                client = RealiserA16Hex(self._host, self._port, self._timeout)
                await self.hass.async_add_executor_job(client.connect)
                await self.hass.async_add_executor_job(client.send, 0x45)
                client.close()

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

            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Connection test failed")
                errors["base"] = "cannot_connect"

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host): str,
                vol.Optional(CONF_PORT, default=self._port): vol.All(
                    vol.Coerce(int), vol.Range(min=512, max=65535)
                ),
                vol.Optional(CONF_TIMEOUT, default=self._timeout): vol.All(
                    vol.Coerce(float), vol.Range(min=1.0, max=30.0)
                ),
                vol.Optional("update_interval", default=self._update_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=300)
                ),
            }
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
