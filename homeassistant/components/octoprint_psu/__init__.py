"""The OctoPrint PSU integration."""
import asyncio
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .api import OctoPrintAPIClient, RestClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["switch"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the OctoPrint PSU component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up OctoPrint PSU from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = OctoPrintAPIClient(
        hass,
        entry.data[CONF_URL],
        username=entry.data[CONF_USERNAME],
        api_key=entry.data[CONF_API_KEY],
    )
    await client.async_open()
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
        client = hass.data[DOMAIN][entry.entry_id]
        await client.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Remove a config entry."""
    try:
        _LOGGER.debug("Revoking API Key: %s", entry.data[CONF_API_KEY])
        rest = RestClient(hass, entry.data[CONF_URL])
        await rest.async_load_api_key(entry.data[CONF_API_KEY])
        await rest.async_revoke_key(entry.data[CONF_API_KEY])
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
