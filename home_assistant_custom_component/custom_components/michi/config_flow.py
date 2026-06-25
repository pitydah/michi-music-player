"""Config flow for Michi Music Player."""
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN, DEFAULT_NAME

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST, default=""): str,
    vol.Required(CONF_PORT, default=8124): int,
    vol.Required(CONF_TOKEN): str,
})


class MichiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=DEFAULT_NAME, data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors)
