from __future__ import annotations

import logging
from typing import Any

import async_timeout
from aiohttp import BasicAuth, ClientError
from aiohttp.client_exceptions import ContentTypeError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import LOGGER_NAME, REST_ENDPOINT_REGISTRATION_TABLE

_LOGGER = logging.getLogger(LOGGER_NAME)


class MikroTikAuthError(Exception):
    pass


class MikroTikConnectionError(Exception):
    pass


class MikroTikResponseError(Exception):
    pass


class MikroTikRestClient:
    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        username: str,
        password: str,
        use_ssl: bool,
        verify_ssl: bool,
    ) -> None:
        self._session = async_create_clientsession(hass)
        self._auth = BasicAuth(username, password)
        self._base_url = base_url.rstrip("/")
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl

    def _build_url(self) -> str:
        return f"{self._base_url}{REST_ENDPOINT_REGISTRATION_TABLE}"

    async def async_get_registration_table(self) -> list[dict[str, Any]]:
        url = self._build_url()

        try:
            async with async_timeout.timeout(30):
                response = await self._session.get(
                    url,
                    auth=self._auth,
                    ssl=self._verify_ssl,
                )
                if response.status == 401:
                    raise MikroTikAuthError("Invalid authentication")
                if response.status >= 400:
                    raise MikroTikConnectionError(
                        f"Unexpected HTTP status code: {response.status}"
                    )
                data = await response.json()
        except ClientError as err:
            raise MikroTikConnectionError(str(err)) from err
        except async_timeout.TimeoutError as err:
            raise MikroTikConnectionError("Request timed out") from err
        except ContentTypeError as err:
            raise MikroTikResponseError("Unable to parse JSON response") from err

        if not isinstance(data, list):
            raise MikroTikResponseError("Expected a JSON list from registration table")

        return data
