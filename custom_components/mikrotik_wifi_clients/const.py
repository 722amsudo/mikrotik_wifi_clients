from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    UnitOfDataRate,
    UnitOfInformation,
)

DOMAIN = "mikrotik_wifi_clients"
LOGGER_NAME = "mikrotik_wifi_clients"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_BASE_URL = "base_url"
CONF_USE_SSL = "use_ssl"
DEFAULT_SCAN_INTERVAL = 10
REST_ENDPOINT_REGISTRATION_TABLE = "/rest/interface/wifi/registration-table"

SENSOR_DESCRIPTION_MAP: dict[str, dict[str, object]] = {
    "signal": {
        "name": "Signal",
        "icon": "mdi:wifi",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "native_unit_of_measurement": "dBm",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "tx_rate": {
        "name": "TX Rate",
        "icon": "mdi:upload",
        "native_unit_of_measurement": UnitOfDataRate.MEGABITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "rx_rate": {
        "name": "RX Rate",
        "icon": "mdi:download",
        "native_unit_of_measurement": UnitOfDataRate.MEGABITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "tx_throughput": {
        "name": "TX Throughput",
        "icon": "mdi:upload-network",
        "native_unit_of_measurement": UnitOfDataRate.BITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "rx_throughput": {
        "name": "RX Throughput",
        "icon": "mdi:download-network",
        "native_unit_of_measurement": UnitOfDataRate.BITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "tx_bytes": {
        "name": "TX Bytes",
        "icon": "mdi:upload",
        "native_unit_of_measurement": UnitOfInformation.BYTES,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "rx_bytes": {
        "name": "RX Bytes",
        "icon": "mdi:download",
        "native_unit_of_measurement": UnitOfInformation.BYTES,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "tx_packets": {
        "name": "TX Packets",
        "icon": "mdi:swap-vertical",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "rx_packets": {
        "name": "RX Packets",
        "icon": "mdi:swap-vertical",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "ssid": {
        "name": "SSID",
        "icon": "mdi:wifi",
    },
    "interface": {
        "name": "Interface",
        "icon": "mdi:ethernet",
    },
    "band": {
        "name": "Band",
        "icon": "mdi:signal-variant",
    },
    "auth_type": {
        "name": "Auth Type",
        "icon": "mdi:lock",
    },
    "uptime": {
        "name": "Uptime",
        "icon": "mdi:timer",
        "device_class": SensorDeviceClass.DURATION,
        "native_unit_of_measurement": "s",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "last_activity": {
        "name": "Last Activity",
        "icon": "mdi:clock-time-four",
    },
}

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = tuple(
    SensorEntityDescription(key=key, **description)
    for key, description in SENSOR_DESCRIPTION_MAP.items()
)

BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="connected",
        name="Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)

DEFAULT_ENTRY_DATA = {
    CONF_VERIFY_SSL: True,
    CONF_USE_SSL: True,
}
