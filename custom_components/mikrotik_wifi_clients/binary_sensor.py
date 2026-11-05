from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    CONF_KNOWN_ETHERNET_CLIENTS,
    DOMAIN,
)
from .coordinator import (
    MikroTikClient,
    MikroTikCoordinator,
    MikroTikEthernetClient,
    MikroTikInterface,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_macs = set(entry.data.get("known_clients", [])) | set(coordinator.data)
    known_ethernet_macs = set(
        entry.data.get(CONF_KNOWN_ETHERNET_CLIENTS, [])
    ) | set(coordinator.ethernet_clients)
    existing_macs: set[str] = set()
    existing_ethernet_macs = set(known_ethernet_macs)

    entities: list[MikroTikClientBinarySensor] = []
    for mac in sorted(known_macs):
        for description in BINARY_SENSOR_DESCRIPTIONS:
            entities.append(MikroTikClientBinarySensor(coordinator, entry.entry_id, mac, description))
        existing_macs.add(mac)

    if entities:
        async_add_entities(entities)

    ethernet_entities = [
        MikroTikEthernetClientBinarySensor(
            coordinator, entry.entry_id, mac
        )
        for mac in sorted(known_ethernet_macs)
    ]
    if ethernet_entities:
        async_add_entities(ethernet_entities)

    existing_interfaces = set(coordinator.interfaces)
    interface_entities = [
        MikroTikInterfaceBinarySensor(coordinator, entry.entry_id, name)
        for name in sorted(existing_interfaces)
    ]
    if interface_entities:
        async_add_entities(interface_entities)

    def _add_new_entities() -> None:
        new_macs = set(coordinator.data) - existing_macs
        new_ethernet_macs = set(coordinator.ethernet_clients) - existing_ethernet_macs
        new_interfaces = set(coordinator.interfaces) - existing_interfaces
        if not new_macs and not new_ethernet_macs and not new_interfaces:
            return

        new_entities: list[MikroTikClientBinarySensor] = []
        for mac in sorted(new_macs):
            for description in BINARY_SENSOR_DESCRIPTIONS:
                new_entities.append(MikroTikClientBinarySensor(coordinator, entry.entry_id, mac, description))
            existing_macs.add(mac)

        if new_entities:
            async_add_entities(new_entities)

        if new_ethernet_macs:
            async_add_entities(
                [
                    MikroTikEthernetClientBinarySensor(
                        coordinator, entry.entry_id, mac
                    )
                    for mac in sorted(new_ethernet_macs)
                ]
            )
            existing_ethernet_macs.update(new_ethernet_macs)

        if new_interfaces:
            async_add_entities(
                [
                    MikroTikInterfaceBinarySensor(coordinator, entry.entry_id, name)
                    for name in sorted(new_interfaces)
                ]
            )
            existing_interfaces.update(new_interfaces)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class MikroTikClientBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        mac: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{mac}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def _client(self) -> MikroTikClient | None:
        return self.coordinator.data.get(self._mac)

    @property
    def is_on(self) -> bool:
        client = self._client
        return bool(client and client.connected)

    @property
    def available(self) -> bool:
        return bool(self._client and self.coordinator.last_update_success)

    @property
    def device_info(self) -> DeviceInfo:
        client = self._client
        name = client.name if client else self._mac
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": name,
            "manufacturer": client.manufacturer if client else None,
            "model": "WiFi Client",
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "via_device": (DOMAIN, self.coordinator.base_url),
        }


class MikroTikInterfaceBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        interface_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._interface_name = interface_name
        self._attr_unique_id = f"{entry_id}_interface_{interface_name}_running"
        self._attr_name = "Link"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_has_entity_name = True

    @property
    def _interface(self) -> MikroTikInterface | None:
        return self.coordinator.interfaces.get(self._interface_name)

    @property
    def is_on(self) -> bool:
        interface = self._interface
        return bool(interface and interface.running)

    @property
    def available(self) -> bool:
        return bool(self._interface and self.coordinator.last_update_success)

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {
                (DOMAIN, f"{self.coordinator.base_url}_interface_{self._interface_name}")
            },
            "name": self._interface_name,
            "manufacturer": "MikroTik",
            "model": "Router Interface",
            "via_device": (DOMAIN, self.coordinator.base_url),
        }


class MikroTikEthernetClientBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        mac: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{entry_id}_{mac}_ethernet_connected"
        self._attr_has_entity_name = True
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def _client(self) -> MikroTikEthernetClient | None:
        return self.coordinator.ethernet_clients.get(self._mac)

    @property
    def is_on(self) -> bool:
        return self._client is not None

    @property
    def available(self) -> bool:
        return bool(self._client and self.coordinator.last_update_success)

    @property
    def device_info(self) -> DeviceInfo:
        client = self._client
        return {
            "identifiers": {(DOMAIN, f"ethernet_{self._mac}")},
            "name": client.name if client else self._mac,
            "model": "Ethernet Client",
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "via_device": (DOMAIN, self.coordinator.base_url),
        }
