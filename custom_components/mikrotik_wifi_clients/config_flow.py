from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import MikroTikAuthError, MikroTikConnectionError, MikroTikRestClient
from .const import CONF_BASE_URL, CONF_USE_SSL, DEFAULT_ENTRY_DATA, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_USE_SSL, default=True): bool,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _normalize_base_url(host: str, use_ssl: bool) -> str:
    parsed = urlparse(host.strip(), scheme="https" if use_ssl else "http")
    if not parsed.netloc:
        parsed = parsed._replace(netloc=parsed.path, path="")

    scheme = "https" if use_ssl else "http"
    if parsed.scheme not in {scheme}:
        parsed = parsed._replace(scheme=scheme)

    return urlunparse(parsed._replace(path="", params="", query="", fragment=""))


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    use_ssl = bool(data.get(CONF_USE_SSL, True))
    base_url = _normalize_base_url(data[CONF_HOST], use_ssl)
    client = MikroTikRestClient(
        hass,
        base_url,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        use_ssl,
        bool(data.get(CONF_VERIFY_SSL, True)),
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
                    CONF_USE_SSL: user_input[CONF_USE_SSL],
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
