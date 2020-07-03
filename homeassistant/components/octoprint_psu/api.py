"""OctoPrint API Client."""
from typing import Optional, Tuple

from octorest import AuthorizationRequestPollingResult, OctoRest

from homeassistant.helpers.typing import HomeAssistantType


class RestClient(OctoRest):
    """OctoPrint REST API Client."""

    def __init__(self, hass: HomeAssistantType, url: str):
        """Initialize the client."""
        self.hass: HomeAssistantType = hass
        super().__init__(url=url)

    async def async_load_api_key(self, api_key: str) -> None:
        """Load an API Key."""
        return await self.hass.async_add_executor_job(self.load_api_key, api_key)

    async def async_probe_app_keys_workflow_support(self):
        """Check if the Application Keys Plugin workflow is supported."""
        return await self.hass.async_add_executor_job(
            self.probe_app_keys_workflow_support
        )

    async def async_start_authorization_process(
        self, app: str, user: Optional[str] = None
    ) -> str:
        """Start the authorization process."""
        return await self.hass.async_add_executor_job(
            self.start_authorization_process, app, user
        )

    async def async_poll_auth_request_decision(
        self, url: str
    ) -> Tuple[AuthorizationRequestPollingResult, Optional[str]]:
        """Check for an authorization request decision."""
        return await self.hass.async_add_executor_job(
            self.poll_auth_request_decision, url
        )

    async def async_settings(self, settings=None):
        """Retrieve current settings."""
        return await self.hass.async_add_executor_job(self.settings, settings)
