from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (
    CONF_KNOWN_ETHERNET_CLIENTS,
    DOMAIN,
    ETHERNET_CLIENT_SENSOR_DESCRIPTIONS,
    INTERFACE_SENSOR_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
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

    entities: list[MikroTikClientSensor] = []
    for mac in sorted(known_macs):
        for description in SENSOR_DESCRIPTIONS:
            entities.append(MikroTikClientSensor(coordinator, entry.entry_id, mac, description))
        existing_macs.add(mac)

    if entities:
        async_add_entities(entities)

    ethernet_entities = [
        MikroTikEthernetClientSensor(
            coordinator, entry.entry_id, mac, description
        )
        for mac in sorted(known_ethernet_macs)
        for description in ETHERNET_CLIENT_SENSOR_DESCRIPTIONS
    ]
    if ethernet_entities:
        async_add_entities(ethernet_entities)

    existing_interfaces = set(coordinator.interfaces)
    interface_entities = [
        MikroTikInterfaceSensor(coordinator, entry.entry_id, name, description)
        for name in sorted(existing_interfaces)
        for description in INTERFACE_SENSOR_DESCRIPTIONS
    ]
    if interface_entities:
        async_add_entities(interface_entities)

    if (
        sorted(known_macs) != entry.data.get("known_clients", [])
        or sorted(known_ethernet_macs)
        != entry.data.get(CONF_KNOWN_ETHERNET_CLIENTS, [])
    ):
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                "known_clients": sorted(known_macs),
                CONF_KNOWN_ETHERNET_CLIENTS: sorted(known_ethernet_macs),
            },
        )

    def _add_new_entities() -> None:
        new_macs = set(coordinator.data) - existing_macs
        new_ethernet_macs = set(coordinator.ethernet_clients) - existing_ethernet_macs
        new_interfaces = set(coordinator.interfaces) - existing_interfaces
        if not new_macs and not new_ethernet_macs and not new_interfaces:
            return

        new_entities: list[MikroTikClientSensor] = []
        for mac in sorted(new_macs):
            for description in SENSOR_DESCRIPTIONS:
                new_entities.append(MikroTikClientSensor(coordinator, entry.entry_id, mac, description))
            existing_macs.add(mac)

        if new_entities:
            async_add_entities(new_entities)
        if new_ethernet_macs:
            async_add_entities(
                [
                    MikroTikEthernetClientSensor(
                        coordinator, entry.entry_id, mac, description
                    )
                    for mac in sorted(new_ethernet_macs)
                    for description in ETHERNET_CLIENT_SENSOR_DESCRIPTIONS
                ]
            )
            existing_ethernet_macs.update(new_ethernet_macs)

        if new_entities or new_ethernet_macs:
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "known_clients": sorted(existing_macs | known_macs),
                    CONF_KNOWN_ETHERNET_CLIENTS: sorted(existing_ethernet_macs),
                },
            )

        if new_interfaces:
            async_add_entities(
                [
                    MikroTikInterfaceSensor(coordinator, entry.entry_id, name, description)
                    for name in sorted(new_interfaces)
                    for description in INTERFACE_SENSOR_DESCRIPTIONS
                ]
            )
            existing_interfaces.update(new_interfaces)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class MikroTikClientSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        mac: str,
        description: SensorEntityDescription,
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
    def available(self) -> bool:
        client = self._client
        return bool(client and self.coordinator.last_update_success)

    @property
    def native_value(self):
        client = self._client
        if client is None:
            return None

        return getattr(client, self.entity_description.key, None)

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


class MikroTikInterfaceSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        interface_name: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._interface_name = interface_name
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_interface_{interface_name}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def _interface(self) -> MikroTikInterface | None:
        return self.coordinator.interfaces.get(self._interface_name)

    @property
    def available(self) -> bool:
        return bool(self._interface and self.coordinator.last_update_success)

    @property
    def native_value(self) -> int | float | None:
        interface = self._interface
        if interface is None:
            return None
        return getattr(interface, self.entity_description.key)

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.base_url}_interface_{self._interface_name}")},
            "name": self._interface_name,
            "manufacturer": "MikroTik",
            "model": "Router Interface",
            "via_device": (DOMAIN, self.coordinator.base_url),
        }


class MikroTikEthernetClientSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: MikroTikCoordinator,
        entry_id: str,
        mac: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{mac}_ethernet_{description.key}"
        self._attr_has_entity_name = True

    @property
    def _client(self) -> MikroTikEthernetClient | None:
        return self.coordinator.ethernet_clients.get(self._mac)

    @property
    def available(self) -> bool:
        return bool(self._client and self.coordinator.last_update_success)

    @property
    def native_value(self) -> str | None:
        client = self._client
        if client is None:
            return None
        return getattr(client, self.entity_description.key)

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
