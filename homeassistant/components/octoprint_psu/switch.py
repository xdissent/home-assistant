"""Switch platform for OctoPrint PSU integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up switch based on a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    state = await client.rest.async_get_psu_state()
    async_add_entities(
        [OctoPrintPsuSwitchEntity(entry.entry_id, entry.data[CONF_NAME], client, state)]
    )


class OctoPrintPsuSwitchEntity(SwitchEntity):
    """An class for OctoPrint PSU switches."""

    def __init__(self, unique_id, name, client, state):
        """Initialize the switch."""
        self._unique_id = unique_id
        self._name = name
        self._state = state
        self._client = client

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._client.async_add_listener(self._async_handle_sockjs_event)
        )

    @callback
    def _async_handle_sockjs_event(self, event):
        _LOGGER.debug("Sockjs event received: %s", event)
        if (
            event["type"] == "message"
            and "plugin" in event["message"]
            and event["message"]["plugin"]["plugin"] == "psucontrol"
        ):
            self._state = event["message"]["plugin"]["data"]["isPSUOn"]
            _LOGGER.debug("Updated state: %s", self._state)
        self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch if any."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._client.connected

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            await self._client.rest.async_turn_psu_on()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        try:
            await self._client.rest.async_turn_psu_off()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
