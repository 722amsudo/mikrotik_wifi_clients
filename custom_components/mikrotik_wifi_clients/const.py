from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DATA_RATE_MEGABITS_PER_SECOND,
    ELECTRIC_POTENTIAL_DBM,
    STORAGE_BYTES,
)

DOMAIN = "mikrotik_wifi_clients"
LOGGER_NAME = "mikrotik_wifi_clients"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_BASE_URL = "base_url"
DEFAULT_SCAN_INTERVAL = 10
REST_ENDPOINT_REGISTRATION_TABLE = "/rest/interface/wifi/registration-table"

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="signal",
        name="Signal",
        icon="mdi:wifi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_DBM,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tx_rate",
        name="TX Rate",
        icon="mdi:upload",
        native_unit_of_measurement=DATA_RATE_MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="rx_rate",
        name="RX Rate",
        icon="mdi:download",
        native_unit_of_measurement=DATA_RATE_MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tx_throughput",
        name="TX Throughput",
        icon="mdi:upload-network",
        native_unit_of_measurement="bps",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="rx_throughput",
        name="RX Throughput",
        icon="mdi:download-network",
        native_unit_of_measurement="bps",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tx_bytes",
        name="TX Bytes",
        icon="mdi:upload",
        native_unit_of_measurement=STORAGE_BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="rx_bytes",
        name="RX Bytes",
        icon="mdi:download",
        native_unit_of_measurement=STORAGE_BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="tx_packets",
        name="TX Packets",
        icon="mdi:swap-vertical",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="rx_packets",
        name="RX Packets",
        icon="mdi:swap-vertical",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="ssid",
        name="SSID",
        icon="mdi:wifi",
    ),
    SensorEntityDescription(
        key="interface",
        name="Interface",
        icon="mdi:ethernet",
    ),
    SensorEntityDescription(
        key="band",
        name="Band",
        icon="mdi:signal-variant",
    ),
    SensorEntityDescription(
        key="auth_type",
        name="Auth Type",
        icon="mdi:lock",
    ),
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:timer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="last_activity",
        name="Last Activity",
        icon="mdi:clock-time-four",
    ),
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
}
