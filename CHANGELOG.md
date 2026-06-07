# Changelog

## 2.0.0

- **Rewritten as a Home Assistant integration** (custom component), replacing the
  former add-on.
- **Bluetooth proxy support.** Uses Home Assistant's native Bluetooth stack
  (`bluetooth.async_ble_device_from_address` + `bleak-retry-connector`), so
  diffusers can be reached through ESPHome/Shelly Bluetooth proxies instead of
  being limited to the host's internal adapter.
- **UI config flow** with Bluetooth auto-discovery and manual MAC entry; one
  config entry (device) per diffuser.
- **Native `switch` entity** per diffuser with confirmed state from BLE ACK
  frames, replacing the `/share` file + `shell_command` control channel.
- Per-device **keepalive interval** option.
- Same BLE protocol as the add-on (characteristic `fff6`, handshake/PIN `8888`,
  keepalive `e0aa55`, on `2d13` / off `2d12`), so existing hardware is unchanged.
