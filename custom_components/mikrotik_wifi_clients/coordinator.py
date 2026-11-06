from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    MikroTikAuthError,
    MikroTikConnectionError,
    MikroTikResponseError,
    MikroTikRestClient,
)
from .const import (
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ETHERNET_INTERFACE_DEFAULT_NAMES,
    LOGGER_NAME,
)

_LOGGER = logging.getLogger(LOGGER_NAME)

_MAC_CLEANER = re.compile(r"[^0-9A-Fa-f]")
_MONITORED_INTERFACE_DEFAULT_NAMES = {
    "ether1",
    "ether2",
    "ether3",
    "ether4",
    "ether5",
    "wifi1",
    "wifi2",
}


@dataclass
class MikroTikClient:
    mac: str
    ip: str | None = None
    hostname: str | None = None
    ssid: str | None = None
    interface: str | None = None
    band: str | None = None
    auth_type: str | None = None
    signal: int | None = None
    tx_rate: float | None = None
    rx_rate: float | None = None
    tx_throughput: float | None = None
    rx_throughput: float | None = None
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
        if self.hostname and self.hostname.lower() != self.mac.lower():
            return self.hostname
        return self.mac


@dataclass
class MikroTikInterface:
    name: str
    running: bool
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    rx_packets: int | None = None
    tx_packets: int | None = None
    rx_rate: float | None = None
    tx_rate: float | None = None


@dataclass
class MikroTikEthernetClient:
    mac: str
    ip: str | None = None
    hostname: str | None = None
    interface: str | None = None
    connected: bool = False
    last_seen: str | None = None
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    rx_rate: float | None = None
    tx_rate: float | None = None

    @property
    def name(self) -> str:
        if self.hostname and self.hostname.lower() != self.mac.lower():
            return self.hostname
        return self.mac


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

    text = str(value).strip()

    match = re.search(r"[\d.]+", text)
    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def _build_arp_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    arp_map = {}

    for row in rows:
        mac = _normalize_mac(row.get("mac-address"))
        ip = row.get("address")

        if mac and ip:
            arp_map[mac] = ip

    return arp_map

def _build_hostname_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    hostname_map = {}

    for row in rows:
        mac = _normalize_mac(row.get("mac-address"))
        hostname = row.get("host-name")

        if mac and hostname:
            hostname_map[mac] = hostname

    return hostname_map


def _build_ip_accounting_map(
    rows: list[dict[str, Any]],
) -> dict[str, tuple[int, int]]:
    """Aggregate bytes by IP: destination bytes are RX, source bytes are TX."""
    totals: dict[str, list[int]] = {}
    for row in rows:
        byte_count = _parse_int(_get_field(row, "bytes", "total-bytes"))
        if byte_count is None:
            continue

        source_ip = _get_field(row, "src-address", "src_address")
        destination_ip = _get_field(row, "dst-address", "dst_address")
        if source_ip:
            totals.setdefault(str(source_ip).split("/")[0], [0, 0])[1] += byte_count
        if destination_ip:
            totals.setdefault(str(destination_ip).split("/")[0], [0, 0])[0] += byte_count

    return {ip: (values[0], values[1]) for ip, values in totals.items()}


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


def _last_seen_from_row(row: dict[str, Any], observed_at: datetime) -> str:
    age = _parse_duration(_get_field(row, "age", "last-seen", "last_seen"))
    if age is not None:
        observed_at -= timedelta(seconds=age)
    return observed_at.isoformat()


def _get_field(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _parse_client(row: dict[str, Any]) -> MikroTikClient | None:
    mac = _normalize_mac(_get_field(row, "mac-address", "mac_address", "mac"))
    if mac is None:
        return None

    bytes_value = _get_field(row, "bytes")
    tx_bytes = _parse_int(_get_field(row, "tx-byte", "tx_bytes"))
    rx_bytes = _parse_int(_get_field(row, "rx-byte", "rx_bytes"))

    if bytes_value and (tx_bytes is None or rx_bytes is None):
        try:
            tx_bytes, rx_bytes = [int(x) for x in str(bytes_value).split(",", 1)]
        except (ValueError, TypeError):
            pass

    packets_value = _get_field(row, "packets")
    tx_packets = _parse_int(_get_field(row, "tx-packet", "tx_packets"))
    rx_packets = _parse_int(_get_field(row, "rx-packet", "rx_packets"))

    if packets_value and (tx_packets is None or rx_packets is None):
        try:
            tx_packets, rx_packets = [int(x) for x in str(packets_value).split(",", 1)]
        except (ValueError, TypeError):
            pass
    
    
    tx_rate = _parse_float(_get_field(row, "tx-rate"))
    rx_rate = _parse_float(_get_field(row, "rx-rate"))
    tx_bps = _parse_float(_get_field(row, "tx-bits-per-second"))
    rx_bps = _parse_float(_get_field(row, "rx-bits-per-second"))
    
    return MikroTikClient(
        mac=mac,
        hostname=_get_field(row, "host-name", "host_name", "hostname", "station-name", "name"),
        ssid=_get_field(row, "ssid"),
        interface=_get_field(row, "interface"),
        band=_get_field(row, "band"),
        auth_type=_get_field(
            row,
            "auth-type",
            "auth_type",
            "auth",
            "authentication",
        ),        
        signal=_parse_int(_get_field(row, "signal-strength", "signal")),
        tx_rate=tx_rate / 1_000_000 if tx_rate is not None else None,
        rx_rate=rx_rate / 1_000_000 if rx_rate is not None else None,
        tx_throughput=tx_bps / 1_000_000 if tx_bps is not None else None,
        rx_throughput=rx_bps / 1_000_000 if rx_bps is not None else None,
        tx_bytes=tx_bytes,
        rx_bytes=rx_bytes,
        tx_packets=tx_packets,
        rx_packets=rx_packets,
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
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        known_ethernet_clients: set[str] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {base_url}",
            update_interval=timedelta(seconds=scan_interval),
        )
        _LOGGER.debug("Created coordinator: interval=%s", self.update_interval)

        self.base_url = base_url
        self.interfaces: dict[str, MikroTikInterface] = {}
        self.ethernet_clients: dict[str, MikroTikEthernetClient] = {
            mac: MikroTikEthernetClient(mac=mac)
            for mac in (known_ethernet_clients or set())
        }
        self._previous_ethernet_counters: dict[str, tuple[int, int, float]] = {}
        self._previous_interface_counters: dict[str, tuple[int, int, float]] = {}
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.netloc or base_url
        port = parsed.port
        self._client = MikroTikRestClient(hass, host, port, username, password, use_ssl, verify_ssl)
        _LOGGER.debug(
            "Coordinator created: interval=%s, listeners=%s",
            self.update_interval,
            len(self._listeners),
        )

    async def _async_update_data(self) -> dict[str, MikroTikClient]:
        _LOGGER.debug(
            "Coordinator update. Interval=%s",
            self.update_interval,
        )
        try:
            registration_table = await self._client.async_get_registration_table()
            arp_table = await self._client.async_get_arp_table()
            dhcp_leases = await self._client.async_get_dhcp_leases()
            interface_rows = await self._client.async_get_interfaces()
            bridge_hosts = await self._client.async_get_bridge_hosts()
            accounting_rows = await self._client.async_get_ip_accounting()

            arp_map = _build_arp_map(arp_table)
            hostname_map = _build_hostname_map(dhcp_leases)
            accounting_map = (
                _build_ip_accounting_map(accounting_rows)
                if accounting_rows is not None
                else {}
            )
            now = time.monotonic()
            observed_at = datetime.now(timezone.utc)
            interfaces: dict[str, MikroTikInterface] = {}
            next_counters: dict[str, tuple[int, int, float]] = {}
            ethernet_interface_names: set[str] = set()
            for row in interface_rows:
                default_name = row.get("default-name")
                name = row.get("name")
                if (
                    default_name in ETHERNET_INTERFACE_DEFAULT_NAMES
                    and isinstance(name, str)
                    and name
                ):
                    ethernet_interface_names.add(name)
                if default_name not in _MONITORED_INTERFACE_DEFAULT_NAMES:
                    continue
                if not isinstance(name, str) or not name:
                    continue
                rx_bytes = _parse_int(row.get("rx-byte"))
                tx_bytes = _parse_int(row.get("tx-byte"))
                running = str(row.get("running", "false")).lower() == "true"
                rx_rate = tx_rate = None
                previous = self._previous_interface_counters.get(name)
                if (
                    previous is not None
                    and rx_bytes is not None
                    and tx_bytes is not None
                ):
                    previous_rx, previous_tx, previous_time = previous
                    elapsed = now - previous_time
                    if elapsed > 0 and rx_bytes >= previous_rx and tx_bytes >= previous_tx:
                        rx_rate = (rx_bytes - previous_rx) * 8 / elapsed / 1_000_000
                        tx_rate = (tx_bytes - previous_tx) * 8 / elapsed / 1_000_000
                if rx_bytes is not None and tx_bytes is not None:
                    next_counters[name] = (rx_bytes, tx_bytes, now)
                interfaces[name] = MikroTikInterface(
                    name=name,
                    running=running,
                    rx_bytes=rx_bytes,
                    tx_bytes=tx_bytes,
                    rx_packets=_parse_int(row.get("rx-packet")),
                    tx_packets=_parse_int(row.get("tx-packet")),
                    rx_rate=rx_rate,
                    tx_rate=tx_rate,
                )
            self.interfaces = interfaces
            self._previous_interface_counters = next_counters

            clients: dict[str, MikroTikClient] = {}
            for client_row in registration_table:
                client = _parse_client(client_row)

                if client is None:
                    continue

                client.ip = arp_map.get(client.mac)
                client.hostname = hostname_map.get(client.mac)

                clients[client.mac] = client

            ethernet_clients: dict[str, MikroTikEthernetClient] = {}
            next_ethernet_counters: dict[str, tuple[int, int, float]] = {}
            for row in bridge_hosts:
                if str(row.get("local", "false")).lower() == "true":
                    continue
                if str(row.get("dynamic", "true")).lower() != "true":
                    continue
                mac = _normalize_mac(
                    _get_field(row, "mac-address", "mac_address", "mac")
                )
                interface_name = _get_field(row, "on-interface", "interface")
                if (
                    mac is None
                    or mac in clients
                    or interface_name not in ethernet_interface_names
                ):
                    continue
                ip = arp_map.get(mac)
                counters = (
                    accounting_map.get(ip, (0, 0))
                    if ip and accounting_rows is not None
                    else None
                )
                rx_bytes, tx_bytes = counters if counters is not None else (None, None)
                previous = self._previous_ethernet_counters.get(mac)
                rx_rate = tx_rate = None
                if previous is not None and counters is not None:
                    previous_rx, previous_tx, previous_time = previous
                    elapsed = now - previous_time
                    if (
                        elapsed > 0
                        and rx_bytes >= previous_rx
                        and tx_bytes >= previous_tx
                    ):
                        rx_rate = (rx_bytes - previous_rx) * 8 / elapsed / 1_000_000
                        tx_rate = (tx_bytes - previous_tx) * 8 / elapsed / 1_000_000
                if counters is not None and rx_bytes is not None and tx_bytes is not None:
                    next_ethernet_counters[mac] = (rx_bytes, tx_bytes, now)
                ethernet_clients[mac] = MikroTikEthernetClient(
                    mac=mac,
                    ip=ip,
                    hostname=hostname_map.get(mac),
                    interface=interface_name,
                    connected=True,
                    last_seen=_last_seen_from_row(row, observed_at),
                    rx_bytes=rx_bytes,
                    tx_bytes=tx_bytes,
                    rx_rate=rx_rate,
                    tx_rate=tx_rate,
                )
            for row in arp_table:
                mac = _normalize_mac(_get_field(row, "mac-address", "mac_address", "mac"))
                interface_name = row.get("interface")
                if (
                    mac is None
                    or mac in clients
                    or mac in ethernet_clients
                    or interface_name not in ethernet_interface_names
                    or str(row.get("dynamic", "true")).lower() != "true"
                ):
                    continue
                ethernet_clients[mac] = MikroTikEthernetClient(
                    mac=mac,
                    ip=arp_map.get(mac),
                    hostname=hostname_map.get(mac),
                    interface=interface_name,
                    connected=True,
                    last_seen=_last_seen_from_row(row, observed_at),
                )
            for mac, previous_client in self.ethernet_clients.items():
                if mac not in ethernet_clients:
                    ethernet_clients[mac] = replace(
                        previous_client,
                        connected=False,
                        rx_rate=0.0 if previous_client.rx_bytes is not None else None,
                        tx_rate=0.0 if previous_client.tx_bytes is not None else None,
                    )
            self._previous_ethernet_counters = next_ethernet_counters
            self.ethernet_clients = ethernet_clients
            return clients
        except (
            MikroTikAuthError,
            MikroTikConnectionError,
            MikroTikResponseError,
        ) as err:
            raise UpdateFailed(f"Unable to update MikroTik data: {err}") from err
