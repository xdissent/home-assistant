"""OctoPrint API Client."""

from octorest import OctoRest

from homeassistant.helpers.typing import HomeAssistantType


class RestClient(OctoRest):
    """OctoPrint REST API Client."""

    def __init__(self, hass: HomeAssistantType, url: str):
        """Initialize the client."""
        self.hass: HomeAssistantType = hass
        super().__init__(url=url)

    async def async_load_api_key(self, api_key: str):
        """Load an API Key."""
        return await self.hass.async_add_executor_job(self.load_api_key, api_key)
