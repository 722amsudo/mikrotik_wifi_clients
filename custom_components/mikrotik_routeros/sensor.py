from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .const import CONF_IDENTITY, CONF_RESOURCE
from .const import LOGGER_NAME

SENSOR_TYPES = {
    "uptime": {
        "name": "Router Uptime",
        "icon": "mdi:timer-sand",
        "resource": CONF_RESOURCE,
        "attribute": "uptime",
    },
    "version": {
        "name": "Software Version",
        "icon": "mdi:chip",
        "resource": CONF_RESOURCE,
        "attribute": "version",
    },
    "board_name": {
        "name": "Board Name",
        "icon": "mdi:router-wireless",
        "resource": CONF_RESOURCE,
        "attribute": "board-name",
    },
    "identity": {
        "name": "Router Identity",
        "icon": "mdi:identifier",
        "resource": CONF_IDENTITY,
        "attribute": "name",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MikroTikSensor] = []

    for key, description in SENSOR_TYPES.items():
        entities.append(
            MikroTikSensor(
                coordinator,
                key,
                description["name"],
                description["icon"],
                description["resource"],
                description["attribute"],
            )
        )

    async_add_entities(entities, True)


class MikroTikSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        key: str,
        name: str,
        icon: str,
        resource: str,
        attribute: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.host}_{key}"
        self._attr_icon = icon
        self._resource = resource
        self._attribute = attribute
        self._attr_native_value = None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._resource, {})
        return data.get(self._attribute)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.host)},
            "name": self.coordinator.host,
            "manufacturer": "MikroTik",
            "model": self.coordinator.data.get(CONF_RESOURCE, {}).get("board-name"),
            "sw_version": self.coordinator.data.get(CONF_RESOURCE, {}).get("version"),
        }
