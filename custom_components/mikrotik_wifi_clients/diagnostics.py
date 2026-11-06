from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import MikroTikCoordinator
from .const import CONF_BASE_URL, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, object]:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "config_entry": {
            CONF_BASE_URL: config_entry.data[CONF_BASE_URL],
            CONF_USERNAME: config_entry.data[CONF_USERNAME],
            CONF_VERIFY_SSL: bool(config_entry.data[CONF_VERIFY_SSL]),
        },
        "clients": [client.raw for client in coordinator.data.values() if client.raw is not None],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device
) -> dict[str, object]:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "device_id": device.id,
        "known_clients": [client.mac for client in coordinator.data.values()],
    }
