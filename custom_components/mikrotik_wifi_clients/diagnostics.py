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
        "ethernet_clients": [
            {
                "mac": client.mac,
                "ip": client.ip,
                "hostname": client.hostname,
                "interface": client.interface,
                "connected": client.connected,
                "last_seen": client.last_seen,
                "rx_bytes": client.rx_bytes,
                "tx_bytes": client.tx_bytes,
                "rx_rate": client.rx_rate,
                "tx_rate": client.tx_rate,
            }
            for client in coordinator.ethernet_clients.values()
        ],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device
) -> dict[str, object]:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "device_id": device.id,
        "known_clients": [client.mac for client in coordinator.data.values()],
        "known_ethernet_clients": list(coordinator.ethernet_clients),
    }
