# MikroTik WiFi Clients Home Assistant Integration

A Home Assistant custom integration for MikroTik RouterOS using the RouterOS REST API.

This integration monitors WiFi clients connected to MikroTik routers and exposes their information as Home Assistant devices and sensors.

## Installation

### HACS (recommended)

1. Add this repository to HACS under Custom repositories.
2. Select category: Integration.
3. Install MikroTik WiFi Clients from HACS.
4. Restart Home Assistant.

### Manual installation

1. Download this repository.
2. Copy the folder:

custom_components/mikrotik_wifi_clients

into:

/config/custom_components/

3. Restart Home Assistant.

## Configuration

This integration uses Home Assistant UI configuration and does not require YAML.

1. Open:

Settings → Devices & Services → Add Integration

2. Search for:

MikroTik WiFi Clients

3. Enter:

- MikroTik router address
- Username
- Password
- SSL settings
- Certificate verification preference

Multiple MikroTik routers can be added.

## Supported entities

Each WiFi client is created as a separate Home Assistant device.

### WiFi information

- Signal strength
- SSID
- Interface
- Band
- Authentication type
- Connection uptime
- Last activity
- Connected status

### Traffic statistics

- TX rate
- RX rate
- TX throughput
- RX throughput
- TX bytes
- RX bytes
- TX packets
- RX packets

### Client information

- MAC address
- IP address (from MikroTik ARP table)
- Hostname (when available)

## Features

- Uses MikroTik RouterOS REST API.
- Reads clients from /rest/interface/wifi/registration-table
- Resolves IP addresses using /rest/ip/arp
- Automatically creates devices for discovered WiFi clients.
- Keeps known clients when they disconnect.
- Supports multiple MikroTik routers.
- Uses Home Assistant aiohttp session.
- No YAML configuration required.

## Requirements

- MikroTik RouterOS 7.x
- REST API enabled
- WiFi package with registration table support
- User permissions:
  - /interface/wifi
  - /ip/arp

## Notes

- Client hostnames depend on information provided by the device.
- Some devices do not send hostname information. In this case MAC address is used.
- IP address detection depends on ARP table availability.
- Updates are performed periodically.

## Roadmap

Planned improvements:

- Ethernet clients support
- DHCP lease integration
- Better device naming
- Vendor lookup by MAC address
- Network traffic dashboard
- Network topology view

## License

MIT License