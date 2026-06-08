# Airversa Scenta Diffuser — Home Assistant Integration

A custom Home Assistant **integration** for the **Airversa Scenta** BLE diffuser
(model `SP3M`). It keeps a persistent BLE connection open to each diffuser (with
keepalive and auto-reconnect) and exposes each one as a `switch` entity.

This is the successor to the
[`ha-airversa-diffuser`](https://github.com/ajachierno/ha-airversa-diffuser)
**add-on**. The big difference:

> **It works through Bluetooth proxies.**
> The old add-on ran in its own container and could only talk to the Home
> Assistant host's *internal* Bluetooth adapter. This integration uses Home
> Assistant's native Bluetooth stack, so it can reach diffusers through any
> **ESPHome / Shelly Bluetooth proxy** on your network — no longer limited to
> the range of the host antenna.

## Why convert the add-on to an integration?

| | Add-on (old) | Integration (this repo) |
| --- | --- | --- |
| BLE access | Direct BlueZ in a container → **host adapter only** | Home Assistant `bluetooth` component → **host adapters _and_ proxies** |
| Bluetooth proxies (ESPHome/Shelly) | ❌ not possible | ✅ supported |
| Control surface | A file in `/share` + `shell_command` glue | A real `switch` entity per diffuser |
| Setup | Add-on store + edit `configuration.yaml` | UI config flow (auto-discovery or MAC entry) |
| State | `cat` a file via `command_line` sensor | Native entity state from BLE ACK frames |
| Multiple devices | `devices:` list in add-on options | One config entry per diffuser |

The BLE protocol itself is unchanged — same characteristic, handshake (PIN
`8888`), keepalive, and on/off frames — so the same hardware works exactly as
before, just with a better transport and a cleaner Home Assistant surface.

## Requirements

- Home Assistant 2024.11 or newer.
- The Home Assistant **Bluetooth** integration set up with at least one adapter
  **or** one [Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  (an ESPHome device with `bluetooth_proxy:` + `active: true`, or a compatible
  Shelly).
- The Airversa phone app **closed** — a diffuser only allows one BLE central at
  a time.

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/ajachierno/ha-airversa-diffuser-int` as an
   **Integration**.
3. Install **Airversa Scenta Diffuser**, then restart Home Assistant.

### Manual

Copy `custom_components/airversa_diffuser/` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

Most likely Home Assistant will **auto-discover** the diffuser via Bluetooth and
offer it under **Settings → Devices & services**. Just confirm it.

If it isn't discovered automatically (the advertised name varies between
units/firmware):

1. **Settings → Devices & services → Add integration → Airversa Scenta
   Diffuser**.
2. Enter the diffuser's Bluetooth **MAC address** (e.g. `24:42:E3:37:86:E7`).
   Recently-seen Bluetooth devices are listed on the form to help you identify
   it.
3. Optionally give it a name.

Repeat once per diffuser — each becomes its own device with one switch.

## Entities

Each diffuser is exposed as a single `switch`:

- **On / Off** maps to the diffuser's `2d13` / `2d12` BLE commands.
- State reflects the device's own ACK frames (`ad13` / `ad12`), so it shows the
  *confirmed* state, not an assumed one.
- The switch is `unavailable` while the BLE link is down (out of range, off, or
  the phone app is holding it), and recovers automatically when it reconnects.

## Options

Per diffuser (**Configure** on the device):

- **Keepalive interval (seconds)** — default `2.0`. How often the keepalive
  frame is sent over the open link. Lower it if a session ever times out.

## Migrating from the add-on

1. Install and set up this integration for each diffuser.
2. Remove the old `shell_command:` and `command_line:` entries you added for the
   add-on, and any `input_boolean` + automation glue used to bridge them.
3. Point your automations/dashboards at the new `switch.<name>` entities
   directly.
4. **Uninstall the "Airversa Diffuser BLE Bridge" add-on** so it stops holding
   the BLE adapter (only one central can hold a diffuser at a time).

## Protocol reference

| Frame | Bytes | Meaning |
| --- | --- | --- |
| Characteristic | `0000fff6-0000-1000-8000-00805f9b34fb` | write + notify |
| Handshake | `8f383838384f4b3031` | contains PIN `8888` |
| Keepalive | `e0aa55` | sent every *keepalive* seconds |
| On | `2d13` | ACK `ad13` |
| Off | `2d12` | ACK `ad12` |

## Troubleshooting

- **Never connects** — confirm the MAC, close the Airversa phone app, and make
  sure an adapter or proxy is actually in range. Enable debug logging (below).
- **Drops after N seconds** — lower the keepalive interval in the device's
  options.
- **Not auto-discovered** — add it manually by MAC; discovery depends on the
  advertised name, which differs across units.

Enable debug logs by adding to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.airversa_diffuser: debug
```

## License

MIT — see [LICENSE](LICENSE).
## Buy me a coffee
Did you find this helpful? Consider buying me a coffee to support additional development: [buymeacoffee](https://buymeacoffee.com/ajachiernoo)
