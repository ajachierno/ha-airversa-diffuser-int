"""Switch platform for the Airversa Scenta Diffuser integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .diffuser import AirversaDiffuser


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the diffuser switch from a config entry."""
    diffuser: AirversaDiffuser = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AirversaDiffuserSwitch(diffuser, entry)])


class AirversaDiffuserSwitch(SwitchEntity):
    """A switch representing one Airversa Scenta diffuser."""

    _attr_has_entity_name = True
    _attr_name = None  # use the device name
    _attr_icon = "mdi:scent"

    def __init__(self, diffuser: AirversaDiffuser, entry: ConfigEntry) -> None:
        """Initialise the switch entity."""
        self._diffuser = diffuser
        self._attr_unique_id = diffuser.address
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, diffuser.address)},
            identifiers={(DOMAIN, diffuser.address)},
            name=entry.title,
            manufacturer="Airversa",
            model="Scenta SP3M",
        )

    @property
    def available(self) -> bool:
        """Return True while a live BLE link is held."""
        return self._diffuser.connected

    @property
    def is_on(self) -> bool | None:
        """Return the last ACK-confirmed state."""
        return self._diffuser.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the diffuser on."""
        await self._diffuser.async_turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the diffuser off."""
        await self._diffuser.async_turn_off()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to connection-state updates."""
        self.async_on_remove(
            self._diffuser.add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
