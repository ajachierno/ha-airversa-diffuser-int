"""Persistent BLE connection manager for an Airversa Scenta diffuser.

This is the integration equivalent of the original add-on's ``diffuser_daemon.py``.
The key difference: instead of talking to BlueZ directly with a bare
``BleakScanner`` / ``BleakClient`` (which only ever sees the host's own
adapter), it goes through Home Assistant's Bluetooth stack:

* ``bluetooth.async_ble_device_from_address(..., connectable=True)`` returns a
  ``BLEDevice`` that may live behind an ESPHome / Shelly **Bluetooth proxy**.
* ``bleak_retry_connector.establish_connection`` routes the connection through
  whichever adapter or proxy actually has the best path to the device.

The result is the same persistent-connection + keepalive + auto-reconnect
behaviour as the add-on, but no longer limited to the host's internal antenna.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from .const import (
    ACK_OFF,
    ACK_ON,
    CHAR_UUID,
    CMD_OFF,
    CMD_ON,
    DEVICE_WAIT_TIMEOUT,
    HANDSHAKE,
    HANDSHAKE_SETTLE,
    KEEPALIVE,
    KEEPALIVE_SETTLE,
    RECONNECT_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class AirversaDiffuser:
    """Maintains one always-on BLE connection to a single diffuser."""

    def __init__(
        self, hass: HomeAssistant, address: str, keepalive: float
    ) -> None:
        """Initialise the connection manager."""
        self.hass = hass
        self.address = address.upper()
        self.keepalive = keepalive

        self._client: BleakClientWithServiceCache | None = None
        self._run_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

        self._connected = False
        self._is_on: bool | None = None  # last ACK-confirmed state
        self._desired: bool | None = None  # last requested state (queued)

        self._listeners: set[CALLBACK_TYPE] = set()

    # ------------------------------------------------------------------ state
    @property
    def connected(self) -> bool:
        """Return True while a live BLE link is held."""
        return self._connected

    @property
    def is_on(self) -> bool | None:
        """Return the last ACK-confirmed on/off state (None if unknown)."""
        return self._is_on

    @callback
    def add_listener(self, update_callback: CALLBACK_TYPE) -> Callable[[], None]:
        """Register an entity callback fired when state changes."""
        self._listeners.add(update_callback)

        def _remove() -> None:
            self._listeners.discard(update_callback)

        return _remove

    @callback
    def _notify_listeners(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    # ------------------------------------------------------------- lifecycle
    async def async_start(self) -> None:
        """Start the background connection task."""
        self._stop.clear()
        self._run_task = self.hass.async_create_background_task(
            self._run(), name=f"airversa_diffuser[{self.address}]"
        )

    async def async_stop(self) -> None:
        """Stop the background task and tear down any live connection."""
        self._stop.set()
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None
        await self._async_disconnect()

    async def _async_disconnect(self) -> None:
        client = self._client
        self._client = None
        self._connected = False
        if client is not None:
            try:
                await client.disconnect()
            except BleakError as err:
                _LOGGER.debug("%s: error during disconnect: %s", self.address, err)
        self._notify_listeners()

    # -------------------------------------------------------------- commands
    async def async_turn_on(self) -> None:
        """Request the diffuser turn on."""
        await self._async_send(CMD_ON, desired=True)

    async def async_turn_off(self) -> None:
        """Request the diffuser turn off."""
        await self._async_send(CMD_OFF, desired=False)

    async def _async_send(self, command: bytes, desired: bool) -> None:
        self._desired = desired
        client = self._client
        if client is None or not client.is_connected:
            _LOGGER.debug(
                "%s: queued %s (not connected yet)",
                self.address,
                "ON" if desired else "OFF",
            )
            return
        try:
            await client.write_gatt_char(CHAR_UUID, command, response=False)
            _LOGGER.debug("%s: sent %s", self.address, "ON" if desired else "OFF")
        except BleakError as err:
            _LOGGER.warning(
                "%s: failed to send %s: %s",
                self.address,
                "ON" if desired else "OFF",
                err,
            )

    # ----------------------------------------------------------- ble notify
    @callback
    def _on_notify(self, _char, data: bytearray) -> None:
        payload = bytes(data)
        if payload == ACK_ON:
            self._is_on = True
            _LOGGER.debug("%s: ACK ON", self.address)
            self._notify_listeners()
        elif payload == ACK_OFF:
            self._is_on = False
            _LOGGER.debug("%s: ACK OFF", self.address)
            self._notify_listeners()

    @callback
    def _on_disconnect(self, _client) -> None:
        _LOGGER.debug("%s: link dropped", self.address)
        self._connected = False
        self._notify_listeners()

    # ------------------------------------------------------------- main loop
    async def _run(self) -> None:
        """Connect, hold, keepalive, and reconnect for the entry's lifetime."""
        while not self._stop.is_set():
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is None:
                _LOGGER.debug(
                    "%s: not currently advertising; waiting for it to appear",
                    self.address,
                )
                await self._async_wait_for_device()
                continue

            try:
                await self._async_connect_and_maintain(device)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the loop alive
                _LOGGER.debug("%s: connection error: %s", self.address, err)
            finally:
                await self._async_disconnect()

            if not self._stop.is_set():
                await asyncio.sleep(RECONNECT_DELAY)

    async def _async_wait_for_device(self) -> None:
        """Block until the device is seen by any adapter/proxy, or timeout."""
        found = asyncio.Event()

        @callback
        def _on_advert(
            _service_info: bluetooth.BluetoothServiceInfoBleak,
            _change: bluetooth.BluetoothChange,
        ) -> None:
            found.set()

        cancel = bluetooth.async_register_callback(
            self.hass,
            _on_advert,
            bluetooth.BluetoothCallbackMatcher(
                address=self.address, connectable=True
            ),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        try:
            await asyncio.wait_for(found.wait(), timeout=DEVICE_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            pass
        finally:
            cancel()

    async def _async_connect_and_maintain(self, device: BLEDevice) -> None:
        """Open the connection, handshake, then loop sending keepalives."""
        _LOGGER.debug("%s: connecting", self.address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            self.address,
            disconnected_callback=self._on_disconnect,
        )
        self._client = client
        try:
            await client.start_notify(CHAR_UUID, self._on_notify)
            await asyncio.sleep(HANDSHAKE_SETTLE)
            await client.write_gatt_char(CHAR_UUID, HANDSHAKE, response=False)
            await asyncio.sleep(KEEPALIVE_SETTLE)
            await client.write_gatt_char(CHAR_UUID, KEEPALIVE, response=False)

            self._connected = True
            self._notify_listeners()
            _LOGGER.info("%s: connected + handshaked", self.address)

            # Re-apply the last requested state across reconnects.
            if self._desired is not None:
                await asyncio.sleep(HANDSHAKE_SETTLE)
                await client.write_gatt_char(
                    CHAR_UUID,
                    CMD_ON if self._desired else CMD_OFF,
                    response=False,
                )

            while client.is_connected and not self._stop.is_set():
                await asyncio.sleep(self.keepalive)
                try:
                    await client.write_gatt_char(
                        CHAR_UUID, KEEPALIVE, response=False
                    )
                except BleakError as err:
                    _LOGGER.debug(
                        "%s: keepalive failed (%s); reconnecting",
                        self.address,
                        err,
                    )
                    break
        finally:
            try:
                await client.stop_notify(CHAR_UUID)
            except Exception as err:  # noqa: BLE001 - best-effort cleanup
                _LOGGER.debug("%s: stop_notify failed: %s", self.address, err)
