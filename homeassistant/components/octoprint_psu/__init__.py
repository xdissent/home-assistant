"""The Octoprint PSU integration."""
import asyncio

from octorest import OctoRest
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["switch"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Octoprint PSU component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Octoprint PSU from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = OctoRest(url=entry.data[CONF_URL])
    await hass.async_add_executor_job(client.load_api_key, entry.data[CONF_API_KEY])
    hass.data[DOMAIN][entry.entry_id] = client

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
