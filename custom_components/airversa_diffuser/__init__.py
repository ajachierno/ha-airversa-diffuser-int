"""The Airversa Scenta Diffuser integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_KEEPALIVE, DEFAULT_KEEPALIVE, DOMAIN
from .diffuser import AirversaDiffuser

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Airversa Scenta Diffuser from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    keepalive: float = entry.options.get(CONF_KEEPALIVE, DEFAULT_KEEPALIVE)

    diffuser = AirversaDiffuser(hass, address, keepalive)
    await diffuser.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = diffuser

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        diffuser: AirversaDiffuser = hass.data[DOMAIN].pop(entry.entry_id)
        await diffuser.async_stop()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
