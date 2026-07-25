# MikroTik WiFi Clients Home Assistant Integration

A Home Assistant custom integration for MikroTik RouterOS using the RouterOS REST API.

## Installation

1. Add this repository to HACS under `Custom repositories`.
2. Set the category to `Integration`.
3. Install the integration from HACS.
4. Restart Home Assistant.

## Configuration

This integration uses a UI config flow and does not require YAML.

1. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `MikroTik WiFi Clients`.
3. Enter your router address, username, password, and SSL verification preference.

## Supported entities

- WiFi client signal
- TX/RX rate
- TX/RX throughput
- TX/RX bytes
- TX/RX packets
- SSID
- Interface
- Band
- Auth type
- Uptime
- Last activity
- Connected binary sensor

## Notes

- Uses the MikroTik RouterOS REST API exclusively.
- Uses Home Assistant's built-in `aiohttp` client session.
- Polls the registration table once per update.
- Supports multiple MikroTik routers via multiple config entries.
