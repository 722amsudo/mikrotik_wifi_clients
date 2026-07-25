from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .compat import load_main_module

main_module = load_main_module()
MikroTikAuthError = main_module.MikroTikAuthError
MikroTikConnectionError = main_module.MikroTikConnectionError
MikroTikRestClient = main_module.MikroTikRestClient
CONF_BASE_URL = main_module.CONF_BASE_URL
DEFAULT_ENTRY_DATA = main_module.DEFAULT_ENTRY_DATA

_LOGGER = logging.getLogger(__name__)

DOMAIN = "mikrotik_routeros"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _normalize_base_url(host: str) -> str:
    parsed = urlparse(host.strip(), scheme="https")
    if not parsed.netloc:
        parsed = parsed._replace(netloc=parsed.path, path="")

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS is supported for RouterOS REST API")

    return urlunparse(parsed._replace(path="", params="", query="", fragment=""))


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    base_url = _normalize_base_url(data[CONF_HOST])
    client = MikroTikRestClient(
        hass,
        base_url,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        bool(data[CONF_VERIFY_SSL]),
    )

    try:
        await client.async_get_registration_table()
    except MikroTikAuthError as err:
        _LOGGER.debug("MikroTik authentication failed: %s", err)
        raise
    except MikroTikConnectionError as err:
        _LOGGER.debug("MikroTik connection failed: %s", err)
        raise

    return {"title": base_url, CONF_BASE_URL: base_url}


class MikroTikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                validated = await validate_input(self.hass, user_input)
            except MikroTikAuthError:
                errors["base"] = "invalid_auth"
            except (MikroTikConnectionError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                entry_data = {
                    CONF_BASE_URL: validated[CONF_BASE_URL],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    **DEFAULT_ENTRY_DATA,
                }
                return self.async_create_entry(
                    title=validated["title"],
                    data=entry_data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
