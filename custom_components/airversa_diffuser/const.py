"""Constants for the Airversa Scenta Diffuser integration."""

from __future__ import annotations

DOMAIN = "airversa_diffuser"

# Config / options keys
CONF_ADDRESS = "address"
CONF_NAME = "name"
CONF_KEEPALIVE = "keepalive_seconds"

DEFAULT_KEEPALIVE = 2.0

# ---------------------------------------------------------------------------
# Airversa Scenta BLE protocol (identical to the original add-on / daemon).
# ---------------------------------------------------------------------------
# GATT characteristic everything is written to / notified from.
CHAR_UUID = "0000fff6-0000-1000-8000-00805f9b34fb"

# Handshake frame contains the fixed PIN 8888.
HANDSHAKE = bytes.fromhex("8f383838384f4b3031")
# Sent periodically to keep the session alive.
KEEPALIVE = bytes.fromhex("e0aa55")

# Commands and their notification acknowledgements.
CMD_ON = bytes.fromhex("2d13")
CMD_OFF = bytes.fromhex("2d12")
ACK_ON = bytes.fromhex("ad13")
ACK_OFF = bytes.fromhex("ad12")

# Connection behaviour.
DEVICE_WAIT_TIMEOUT = 60.0  # seconds to wait for an advertisement before retrying
RECONNECT_DELAY = 5.0  # seconds between reconnect attempts
HANDSHAKE_SETTLE = 0.3  # pause after start_notify before handshake
KEEPALIVE_SETTLE = 0.5  # pause after handshake before first keepalive
