"""Switch platform for OctoPrint PSU integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.typing import HomeAssistantType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up switch based on a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [OctoPrintPsuSwitchEntity(entry.entry_id, entry.data[CONF_NAME], client)]
    )


class OctoPrintPsuSwitchEntity(SwitchEntity):
    """An class for OctoPrint PSU switches."""

    def __init__(self, unique_id, name, client):
        """Initialize the switch."""
        self._unique_id = unique_id
        self._name = name
        self._state = True
        self._client = client

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch if any."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._state = False
        self.schedule_update_ha_state()
