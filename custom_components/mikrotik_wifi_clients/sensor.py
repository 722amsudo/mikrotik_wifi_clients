from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import DOMAIN, SENSOR_DESCRIPTIONS
from .coordinator import MikroTikClient, MikroTikCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_macs = set(entry.data.get("known_clients", [])) | set(coordinator.data)
    existing_macs: set[str] = set()

    entities: list[MikroTikClientSensor] = []
    for mac in sorted(known_macs):
        for description in SENSOR_DESCRIPTIONS:
            entities.append(MikroTikClientSensor(coordinator, entry.entry_id, mac, description))
        existing_macs.add(mac)

    if entities:
        async_add_entities(entities)

    if sorted(known_macs) != entry.data.get("known_clients", []):
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "known_clients": sorted(known_macs)},
        )

    def _add_new_entities() -> None:
        new_macs = set(coordinator.data) - existing_macs
        if not new_macs:
            return

        new_entities: list[MikroTikClientSensor] = []
        for mac in sorted(new_macs):
            for description in SENSOR_DESCRIPTIONS:
                new_entities.append(MikroTikClientSensor(coordinator, entry.entry_id, mac, description))
            existing_macs.add(mac)

        async_add_entities(new_entities)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "known_clients": sorted(existing_macs | known_macs)},
        )

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
