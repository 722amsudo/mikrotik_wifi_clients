# MikroTik RouterOS Home Assistant Integration

A lightweight Home Assistant custom integration for MikroTik RouterOS devices using the RouterOS API.

## Installation

1. Add this repository to HACS under `Custom repositories`.
2. Set the category to `Integration`.
3. Install the integration from HACS.
4. Restart Home Assistant.

## Configuration

This integration uses a UI config flow.

1. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `MikroTik RouterOS`.
3. Enter your router host, username, and password.

## Supported entities

- Router uptime
- Router software version
- Board name
- Router identity

## Requirements

- `librouteros`

## Notes

This integration connects to MikroTik devices via the RouterOS API. Make sure the API service is enabled in your MikroTik router and that the account has permission to read system information.
