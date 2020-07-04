"""Switch platform for OctoPrint PSU integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .entity import OctoPrintPsuEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up switch based on a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    state = await client.rest.async_get_psu_state()
    async_add_entities(
        [
            OctoPrintPsuSwitchEntity(
                entry_id=entry.entry_id,
                name=entry.data[CONF_NAME],
                client=client,
                state=state,
            )
        ]
    )


class OctoPrintPsuSwitchEntity(OctoPrintPsuEntity, SwitchEntity):
    """An class for OctoPrint PSU switches."""

    def __init__(
        self, state: bool = False, *args, **kwargs,
    ):
        """Initialize the switch."""
        super().__init__(*args, **kwargs)
        self._state = state

    @callback
    def async_handle_octoprint_event(self, event):
        """Handle OctoPrint SockJS API client event."""
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
