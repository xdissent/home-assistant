"""Switch platform for Octoprint PSU integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.typing import HomeAssistantType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up switch based on a config entry."""
    async_add_entities(
        [OctoprintPsuSwitchEntity(entry.entry_id, entry.data[CONF_NAME])]
    )


class OctoprintPsuSwitchEntity(SwitchEntity):
    """An class for Octoprint PSU switches."""

    def __init__(self, unique_id, name):
        """Initialize the switch."""
        self._unique_id = unique_id
        self._name = name

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return True
