from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MikroTikConnectionError, MikroTikResponseError, MikroTikRestClient
from .const import (
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER_NAME,
)

_LOGGER = logging.getLogger(LOGGER_NAME)

_MAC_CLEANER = re.compile(r"[^0-9A-Fa-f]")


@dataclass
class MikroTikClient:
    mac: str
    hostname: str | None = None
    ssid: str | None = None
    interface: str | None = None
    band: str | None = None
    auth_type: str | None = None
    signal: int | None = None
    tx_rate: float | None = None
    rx_rate: float | None = None
    tx_throughput: int | None = None
    rx_throughput: int | None = None
    tx_bytes: int | None = None
    rx_bytes: int | None = None
    tx_packets: int | None = None
    rx_packets: int | None = None
    uptime: int | None = None
    last_activity: str | None = None
    connected: bool = True
    manufacturer: str | None = None
    raw: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        return self.hostname or self.mac


def _normalize_mac(raw_mac: str | None) -> str | None:
    if not raw_mac:
        return None

    cleaned = _MAC_CLEANER.sub("", raw_mac)
    if len(cleaned) != 12:
        return None

    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2)).lower()


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_duration(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    if text.lower().startswith("0x"):
        return None

    matches = re.findall(r"(?P<value>\d+)(?P<unit>[smhdw])", text.lower())
    if matches:
        seconds = 0
        for raw_value, unit in matches:
            number = int(raw_value)
            if unit == "s":
                seconds += number
            elif unit == "m":
                seconds += number * 60
            elif unit == "h":
                seconds += number * 3600
            elif unit == "d":
                seconds += number * 86400
            elif unit == "w":
                seconds += number * 604800
        return seconds

    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            parts_int = [int(part) for part in parts]
        except ValueError:
            return None
        if len(parts_int) == 2:
            return parts_int[0] * 60 + parts_int[1]
        return parts_int[0] * 3600 + parts_int[1] * 60 + parts_int[2]

    return _parse_int(text)


def _get_field(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _parse_client(row: dict[str, Any]) -> MikroTikClient | None:
    mac = _normalize_mac(_get_field(row, "mac-address", "mac_address", "mac"))
    if mac is None:
        return None

    return MikroTikClient(
        mac=mac,
        hostname=_get_field(row, "host-name", "host_name", "hostname", "station-name", "name"),
        ssid=_get_field(row, "ssid"),
        interface=_get_field(row, "interface"),
        band=_get_field(row, "band"),
        auth_type=_get_field(row, "auth", "authentication"),
        signal=_parse_int(_get_field(row, "signal-strength", "signal")),
        tx_rate=_parse_float(_get_field(row, "tx-rate", "tx_rate")),
        rx_rate=_parse_float(_get_field(row, "rx-rate", "rx_rate")),
        tx_throughput=_parse_int(_get_field(row, "tx-byte-rate", "tx_byte_rate", "tx-throughput")),
        rx_throughput=_parse_int(_get_field(row, "rx-byte-rate", "rx_byte_rate", "rx-throughput")),
        tx_bytes=_parse_int(_get_field(row, "tx-byte", "tx_byte")),
        rx_bytes=_parse_int(_get_field(row, "rx-byte", "rx_byte")),
        tx_packets=_parse_int(_get_field(row, "tx-packet", "tx_packet")),
        rx_packets=_parse_int(_get_field(row, "rx-packet", "rx_packet")),
        uptime=_parse_duration(_get_field(row, "uptime")),
        last_activity=_get_field(row, "last-activity", "last_activity"),
        manufacturer=_get_field(row, "manufacturer", "vendor"),
        raw=row,
    )


class MikroTikCoordinator(DataUpdateCoordinator[dict[str, MikroTikClient]]):
    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        username: str,
        password: str,
        use_ssl: bool,
        verify_ssl: bool,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {base_url}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.base_url = base_url
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.netloc or base_url
        port = parsed.port
        self._client = MikroTikRestClient(hass, host, port, username, password, use_ssl, verify_ssl)

    async def _async_update_data(self) -> dict[str, MikroTikClient]:
        try:
            registration_table = await self._client.async_get_registration_table()
            clients: dict[str, MikroTikClient] = {}
            for client_row in registration_table:
                client = _parse_client(client_row)
                if client is None:
                    continue
                clients[client.mac] = client
            return clients
        except (MikroTikConnectionError, MikroTikResponseError) as err:
            raise UpdateFailed(f"Unable to update MikroTik data: {err}") from err
