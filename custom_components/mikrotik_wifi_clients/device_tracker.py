from __future__ import annotations

from homeassistant.components.device_tracker import (
    SourceType,
    TrackerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_KNOWN_ETHERNET_CLIENTS, DOMAIN
from .coordinator import MikroTikCoordinator, MikroTikEthernetClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MikroTikCoordinator = hass.data[DOMAIN][entry.entry_id]
    existing_macs = set(
        entry.data.get(CONF_KNOWN_ETHERNET_CLIENTS, [])
    ) | set(coordinator.ethernet_clients)

    if existing_macs:
        async_add_entities(
            [
                MikroTikEthernetDeviceTracker(coordinator, entry.entry_id, mac)
                for mac in sorted(existing_macs)
            ]
        )

    def _add_new_trackers() -> None:
        new_macs = set(coordinator.ethernet_clients) - existing_macs
        if not new_macs:
            return
        async_add_entities(
            [
                MikroTikEthernetDeviceTracker(coordinator, entry.entry_id, mac)
                for mac in sorted(new_macs)
            ]
        )
        existing_macs.update(new_macs)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_trackers))


class MikroTikEthernetDeviceTracker(CoordinatorEntity, TrackerEntity):
    _attr_source_type = SourceType.ROUTER

    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        mac: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{entry_id}_{mac}_ethernet_tracker"
        self._attr_has_entity_name = True

    @property
    def _client(self) -> MikroTikEthernetClient | None:
        return self.coordinator.ethernet_clients.get(self._mac)

    @property
    def is_connected(self) -> bool:
        client = self._client
        return bool(client and client.connected)

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def ip_address(self) -> str | None:
        client = self._client
        return client.ip if client else None

    @property
    def name(self) -> str:
        client = self._client
        return client.name if client else self._mac

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        client = self._client
        if client is None:
            return {}
        return {
            "ip_address": client.ip,
            "mac_address": client.mac,
            "host_name": client.hostname,
            "interface": client.interface,
            "last_seen": client.last_seen,
        }

    @property
    def device_info(self) -> DeviceInfo:
        client = self._client
        return {
            "identifiers": {(DOMAIN, f"ethernet_{self._mac}")},
            "name": client.name if client else self._mac,
            "model": "Ethernet Client",
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "via_device_id": self.coordinator.router_device_id,
        }
