from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from librouteros import connect

from .const import CONF_IDENTITY, CONF_RESOURCE, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER_NAME, PLATFORMS

_LOGGER = logging.getLogger(LOGGER_NAME)


class MikroTikDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, username: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.host = host
        self.username = username
        self.password = password
        self.api = None

    def _connect(self):
        if self.api is None:
            self.api = connect(host=self.host, username=self.username, password=self.password)
        return self.api

    def _fetch_data(self) -> dict[str, dict]:
        api = self._connect()
        resource = list(api.path("system", "resource"))[0]
        identity = list(api.path("system", "identity"))[0]
        return {CONF_RESOURCE: resource, CONF_IDENTITY: identity}

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch MikroTik data: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MikroTikDataUpdateCoordinator(
        hass,
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data["host"])},
        manufacturer="MikroTik",
        name=entry.data["host"],
        model=coordinator.data[CONF_RESOURCE].get("board-name"),
        sw_version=coordinator.data[CONF_RESOURCE].get("version"),
    )

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
