import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
sys.modules["homeassistant"] = homeassistant

config_entries = types.ModuleType("homeassistant.config_entries")


class ConfigEntry:  # pragma: no cover - simple stub
    pass


config_entries.ConfigEntry = ConfigEntry
sys.modules["homeassistant.config_entries"] = config_entries

core = types.ModuleType("homeassistant.core")


class HomeAssistant:  # pragma: no cover - simple stub
    pass


core.HomeAssistant = HomeAssistant
sys.modules["homeassistant.core"] = core

exceptions = types.ModuleType("homeassistant.exceptions")


class ConfigEntryNotReady(Exception):  # pragma: no cover - simple stub
    pass


exceptions.ConfigEntryNotReady = ConfigEntryNotReady
sys.modules["homeassistant.exceptions"] = exceptions

helpers = types.ModuleType("homeassistant.helpers")
helpers.__path__ = []
sys.modules["homeassistant.helpers"] = helpers

device_registry = types.ModuleType("homeassistant.helpers.device_registry")


class DummyDeviceRegistry:
    def async_get_or_create(self, *args, **kwargs):
        return None


def async_get(*args, **kwargs):
    return DummyDeviceRegistry()


device_registry.async_get = async_get
sys.modules["homeassistant.helpers.device_registry"] = device_registry

aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")


def async_create_clientsession(*args, **kwargs):
    return object()


aiohttp_client.async_create_clientsession = async_create_clientsession
sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client

update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")


class DataUpdateCoordinator:  # pragma: no cover - simple stub
    def __init__(self, *args, **kwargs):
        pass

    def __class_getitem__(cls, item):
        return cls


class UpdateFailed(Exception):  # pragma: no cover - simple stub
    pass


update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator

components = types.ModuleType("homeassistant.components")
components.__path__ = []
sys.modules["homeassistant.components"] = components

binary_sensor = types.ModuleType("homeassistant.components.binary_sensor")


class BinarySensorDeviceClass:
    CONNECTIVITY = "connectivity"


class BinarySensorEntityDescription:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


binary_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
binary_sensor.BinarySensorEntityDescription = BinarySensorEntityDescription
sys.modules["homeassistant.components.binary_sensor"] = binary_sensor

sensor = types.ModuleType("homeassistant.components.sensor")


class SensorDeviceClass:
    SIGNAL_STRENGTH = "signal_strength"
    DURATION = "duration"


class SensorEntityDescription:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class SensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


sensor.SensorDeviceClass = SensorDeviceClass
sensor.SensorEntityDescription = SensorEntityDescription
sensor.SensorStateClass = SensorStateClass
sys.modules["homeassistant.components.sensor"] = sensor

const_module = types.ModuleType("homeassistant.const")


class UnitOfDataRate:
    MEGABITS_PER_SECOND = "Mb/s"
    BITS_PER_SECOND = "b/s"


class UnitOfInformation:
    BYTES = "B"


const_module.CONF_PASSWORD = "password"
const_module.CONF_USERNAME = "username"
const_module.CONF_VERIFY_SSL = "verify_ssl"
const_module.UnitOfDataRate = UnitOfDataRate
const_module.UnitOfInformation = UnitOfInformation
sys.modules["homeassistant.const"] = const_module

from custom_components.mikrotik_wifi_clients import api as api_module


def test_rest_client_accepts_host_and_port() -> None:
    hass = MagicMock()

    with patch.object(api_module, "async_create_clientsession", return_value=MagicMock()):
        client = api_module.MikroTikRestClient(
            hass,
            "router.local",
            443,
            "user",
            "pass",
            True,
            False,
        )

    assert client._host == "router.local"
    assert client._port == 443
    assert client._use_ssl is True
    assert client._verify_ssl is False
