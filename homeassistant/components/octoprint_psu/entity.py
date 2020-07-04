"""Base Entity for OctoPrint PSU integration."""
import logging
from typing import Optional

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .api import API_EVENT, OctoPrintAPIClient

_LOGGER = logging.getLogger(__name__)


class OctoPrintEntity(Entity):
    """An class for OctoPrint PSU entities."""

    def __init__(
        self, entry_id: str, client: OctoPrintAPIClient, name: Optional[str] = None
    ):
        """Initialize the switch."""
        self._entry_id = entry_id
        self._client = client
        self._name = name

    @property
    def name(self) -> Optional[str]:
        """Return the name of the switch if any."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._entry_id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._client.connected

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        _LOGGER.debug("Added to hass")
        self.async_on_remove(
            self._client.async_add_listener(self.async_handle_octoprint_event)
        )

    @callback
    def async_handle_octoprint_event(self, event: API_EVENT) -> None:
        """Handle OctoPrint SockJS API client event."""
        raise NotImplementedError
