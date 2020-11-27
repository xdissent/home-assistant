"""The OctoPrint PSU integration."""
import asyncio
import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_BINARY_SENSORS,
    CONF_HOST,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_PATH,
    CONF_PORT,
    CONF_SENSORS,
    CONF_SSL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify as util_slugify

from .api import OctoPrintAPIClient, RestClient
from .const import (
    BINARY_SENSOR_TYPES,
    CONF_BED,
    CONF_NUMBER_OF_TOOLS,
    CONF_REVOKE_API_KEY,
    DEFAULT_NAME,
    DOMAIN,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["switch"]

BINARY_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_MONITORED_CONDITIONS, default=list(BINARY_SENSOR_TYPES)
        ): vol.All(cv.ensure_list, [vol.In(BINARY_SENSOR_TYPES)])
    }
)

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        )
    }
)


def has_all_unique_names(value):
    """Validate that printers have an unique name."""
    names = [util_slugify(printer["name"]) for printer in value]
    vol.Schema(vol.Unique())(names)
    return value


def ensure_valid_path(value):
    """Validate the path, ensuring it starts and ends with a /."""
    vol.Schema(cv.string)(value)
    if value[0] != "/":
        value = f"/{value}"
    if value[-1] != "/":
        value += "/"
    return value


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_API_KEY): cv.string,
                        vol.Optional(CONF_USERNAME): cv.string,
                        vol.Required(CONF_HOST): cv.string,
                        vol.Optional(CONF_SSL, default=False): cv.boolean,
                        vol.Optional(CONF_PORT, default=80): cv.port,
                        vol.Optional(CONF_PATH, default="/"): ensure_valid_path,
                        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                        vol.Optional(CONF_NUMBER_OF_TOOLS, default=0): cv.positive_int,
                        vol.Optional(CONF_BED, default=False): cv.boolean,
                        vol.Optional(CONF_SENSORS, default={}): SENSOR_SCHEMA,
                        vol.Optional(
                            CONF_BINARY_SENSORS, default={}
                        ): BINARY_SENSOR_SCHEMA,
                    }
                )
            ],
            has_all_unique_names,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the OctoPrint PSU component."""
    if DOMAIN not in config:
        return True

    for data in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=data
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OctoPrint PSU from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Setting up entry %s", entry)

    client = OctoPrintAPIClient(
        hass,
        entry.data[CONF_URL],
        username=entry.data[CONF_USERNAME],
        api_key=entry.data[CONF_API_KEY],
    )
    _LOGGER.debug("Opening client %s", entry.data[CONF_URL])
    await client.async_open()
    _LOGGER.debug("Opened client %s", entry.data[CONF_URL])
    hass.data[DOMAIN][entry.entry_id] = client

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
        # TODO: try/catch
        await client.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    if not entry.data[CONF_REVOKE_API_KEY]:
        return
    try:
        _LOGGER.debug("Revoking API Key: %s", entry.data[CONF_API_KEY])
        rest = RestClient(hass, entry.data[CONF_URL])
        await rest.async_load_api_key(entry.data[CONF_API_KEY])
        await rest.async_revoke_key(entry.data[CONF_API_KEY])
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
