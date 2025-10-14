import voluptuous as vol
from homeassistant import config_entries
from .const import *

class HATunnelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=f"Tunnel to {user_input[CONF_HOST]}", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=22): int,
            vol.Required(CONF_USER): str,
            vol.Required(CONF_KEY): str,
            vol.Required(CONF_LOCAL_PORT): int,
            vol.Required(CONF_REMOTE): str,
            vol.Required(CONF_REMOTE_PORT): int,
            vol.Optional(CONF_AUTO_RECONNECT, default=True): bool,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema)
