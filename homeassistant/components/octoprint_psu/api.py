"""OctoPrint API Client."""
import asyncio
from typing import Optional, Tuple

from octorest import (
    AuthorizationRequestPollingResult,
    OctoRest,
    WorkflowAppKeyRequestResult,
)

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

    async def async_try_get_api_key(
        self, app_name: str, user: Optional[str], timeout: int = 60
    ) -> Tuple[WorkflowAppKeyRequestResult, Optional[str]]:
        """Run the Application Keys Plugin Workflow."""
        workflow_supported = await self.async_probe_app_keys_workflow_support()

        if not workflow_supported:
            return (WorkflowAppKeyRequestResult.WORKFLOW_UNSUPPORTED, None)

        polling_url = await self.async_start_authorization_process(app_name, user)

        interval = 1
        elapsed = 0

        while elapsed < timeout:
            (polling_result, api_key) = await self.async_poll_auth_request_decision(
                polling_url
            )

            if polling_result == AuthorizationRequestPollingResult.NOPE:
                return (WorkflowAppKeyRequestResult.NOPE, None)

            if polling_result == AuthorizationRequestPollingResult.GRANTED:
                return (WorkflowAppKeyRequestResult.GRANTED, api_key)

            await asyncio.sleep(interval)
            elapsed += interval

        return (WorkflowAppKeyRequestResult.TIMED_OUT, None)

    async def _async_post(self, path, data=None, files=None, json=None, ret=True):
        return await self.hass.async_add_executor_job(
            self._post, path, data, files, json, ret
        )

    async def async_turn_psu_on(self) -> None:
        """Turn on the PSU."""
        return await self._async_post(
            "/api/plugin/psucontrol", json={"command": "turnPSUOn"}, ret=False
        )

    async def async_turn_psu_off(self) -> None:
        """Turn off the PSU."""
        return await self._async_post(
            "/api/plugin/psucontrol", json={"command": "turnPSUOff"}, ret=False
        )
