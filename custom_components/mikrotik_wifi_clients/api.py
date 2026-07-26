from __future__ import annotations

import logging
import ssl
from typing import Any

import async_timeout
from aiohttp import BasicAuth, ClientError
from aiohttp.client_exceptions import ContentTypeError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    LOGGER_NAME,
    REST_ENDPOINT_REGISTRATION_TABLE,
    REST_ENDPOINT_ARP,
)

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
        host: str,
        port: int | None,
        username: str,
        password: str,
        use_ssl: bool,
        verify_ssl: bool,
    ) -> None:
        self._session = async_create_clientsession(hass)
        self._auth = BasicAuth(username, password)
        self._host = host.rstrip("/")
        self._port = port
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl

    def _build_url(self) -> str:
        scheme = "https" if self._use_ssl else "http"
        netloc = self._host
        if self._port is not None:
            netloc = f"{netloc}:{self._port}"
        return f"{scheme}://{netloc}{REST_ENDPOINT_REGISTRATION_TABLE}"

    def _build_endpoint_url(self, endpoint: str) -> str:
        scheme = "https" if self._use_ssl else "http"
        netloc = self._host

        if self._port is not None:
            netloc = f"{netloc}:{self._port}"

        return f"{scheme}://{netloc}{endpoint}"
    
    def _ssl_context(self) -> ssl.SSLContext | bool:
        if self._verify_ssl:
            return ssl.create_default_context()
        return False

    async def async_get_registration_table(self) -> list[dict[str, Any]]:
        url = self._build_url()

        ssl_context = self._ssl_context()

        try:
            async with async_timeout.timeout(30):
                async with self._session.get(
                    url,
                    auth=self._auth,
                    ssl=ssl_context,
                ) as response:
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

    async def async_get_arp_table(self) -> list[dict[str, Any]]:
        url = self._build_endpoint_url(REST_ENDPOINT_ARP)

        ssl_context = self._ssl_context()

        try:
            async with async_timeout.timeout(30):
                async with self._session.get(
                    url,
                    auth=self._auth,
                    ssl=ssl_context,
                ) as response:
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
            raise MikroTikResponseError("Expected a JSON list from ARP table")

        return data
