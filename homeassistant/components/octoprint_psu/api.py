"""OctoPrint API Client."""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from octorest import (
    AuthorizationRequestPollingResult,
    OctoRest,
    WebSocketEventHandler,
    WorkflowAppKeyRequestResult,
)

from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


API_EVENT = Dict[str, Any]
API_EVENT_LISTENER = Callable[[API_EVENT], None]


class OctoPrintAPIClient:
    """OctoPrint API Client."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        username: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the client."""
        self.hass = hass
        self.url = url
        self.username = username
        self.api_key = api_key

        self.rest = RestClient(hass, url)

        self.connected: bool = False

        self._listeners: List[API_EVENT_LISTENER] = []

        def on_open(ws):
            self._on_sockjs_event({"type": "open"})

        def on_close(ws):
            self._on_sockjs_event({"type": "close"})

        def on_message(ws, message):
            self._on_sockjs_event({"type": "message", "message": message})

        self.sockjs = SockJSClient(
            url, on_open=on_open, on_close=on_close, on_message=on_message,
        )

    async def async_open(self):
        """Open the client."""
        _LOGGER.debug("Opening")
        if self.api_key:
            _LOGGER.debug("Loading REST API Key %s", self.api_key)
            try:
                await self.rest.async_load_api_key(self.api_key)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
        await self.hass.async_add_executor_job(self.sockjs.run)
        _LOGGER.debug("Opened")

    async def async_close(self):
        """Close the client."""
        _LOGGER.debug("Closing")
        await self.hass.async_add_executor_job(self.sockjs.close)
        await self.hass.async_add_executor_job(self.sockjs.wait)
        _LOGGER.debug("Closed")

    @callback
    def async_add_listener(self, listener: API_EVENT_LISTENER) -> Callable[[], None]:
        """Listen for sockjs events."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            """Remove update listener."""
            self.async_remove_listener(listener)

        return remove_listener

    @callback
    def async_remove_listener(self, listener: API_EVENT_LISTENER) -> None:
        """Remove data update."""
        self._listeners.remove(listener)

    def _on_sockjs_event(self, event):
        _LOGGER.debug("Sockjs event received: %s", event)
        if event["type"] == "open":
            self.connected = True
            if self.api_key and self.username:
                self.hass.add_job(self._auth_sockjs)
        if event["type"] == "close":
            self.connected = False
            # TODO: reconnect
        for listener in self._listeners:
            self.hass.add_job(listener, event)

    def _auth_sockjs(self):
        _LOGGER.debug("Authenticating sockjs: %s:%s", self.username, self.api_key)
        self.sockjs.auth(self.username, self.api_key)


class SockJSClient(WebSocketEventHandler):
    """OctoPrint SockJS API Client."""

    def send(self, data):
        """Send a message to the SockJS server."""
        self.socket.send(json.dumps([json.dumps(data)]))

    def close(self):
        """Close the client."""
        self.socket.close()

    def auth(self, username: str, api_key: str):
        """Authenticate the socket with a user and API key."""
        self.send({"auth": f"{username}:{api_key}"})

    def throttle(self, multiplier: int):
        """Throttle status message frequency to multiplier * 500ms."""
        self.send({"throttle": multiplier})


class RestClient(OctoRest):
    """OctoPrint REST API Client."""

    def __init__(self, hass: HomeAssistant, url: str):
        """Initialize the client."""
        self.hass: HomeAssistant = hass
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

    async def async_revoke_key(self, api_key: str):
        """Revoke an API Key."""
        return await self._async_post(
            "/api/plugin/appkeys",
            json={"command": "revoke", "key": api_key},
            ret=False,
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

    async def async_get_psu_state(self) -> None:
        """Turn off the PSU."""
        res = await self._async_post(
            "/api/plugin/psucontrol", json={"command": "getPSUState"}
        )
        return res["isPSUOn"]
