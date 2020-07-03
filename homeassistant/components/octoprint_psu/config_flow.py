"""Config flow for Octoprint PSU integration."""
import asyncio
import logging
from typing import Optional

from octorest import AuthorizationRequestPollingResult, WorkflowAppKeyRequestResult
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL, CONF_USERNAME

from .api import RestClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octoprint PSU."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize flow."""
        self._url: Optional[str] = None
        self._username: Optional[str] = None
        self._client: Optional[RestClient] = None
        self._workflow_url: Optional[str] = None
        self._workflow_result: Optional[WorkflowAppKeyRequestResult] = None
        self._api_key: Optional[str] = None
        self._name: Optional[str] = None

    async def _async_init_workflow(self):
        """Init the app keys workflow."""
        self._client = RestClient(url=self._url)
        supported = await self.hass.async_add_executor_job(
            self._client.probe_app_keys_workflow_support
        )
        if not supported:
            return False
        workflow_url = await self.hass.async_add_executor_job(
            self._client.start_authorization_process,
            f"Home Assistant ({self.flow_id})",
            self._username,
        )
        self.hass.async_create_task(self._async_poll_workflow(workflow_url))
        return True

    async def _async_poll_workflow(self, url, timeout=60):
        """Poll the app keys workflow."""
        interval = 1
        elapsed = 0

        while elapsed < timeout:
            _LOGGER.debug("Checking workflow url: %s", url)
            # TODO: Try/catch
            (polling_result, api_key) = await self.hass.async_add_executor_job(
                self._client.poll_auth_request_decision, url
            )
            if polling_result == AuthorizationRequestPollingResult.NOPE:
                return await self._async_finish_workflow(
                    WorkflowAppKeyRequestResult.NOPE
                )
            if polling_result == AuthorizationRequestPollingResult.GRANTED:
                return await self._async_finish_workflow(
                    WorkflowAppKeyRequestResult.GRANTED, api_key,
                )
            _LOGGER.debug("No workflow status yet: %s", url)
            await asyncio.sleep(interval)
            elapsed += interval
        await self._async_finish_workflow(WorkflowAppKeyRequestResult.TIMED_OUT)

    async def _async_finish_workflow(self, result, api_key=None):
        _LOGGER.debug("Finishing workflow: %s %s", result, api_key)
        if result == WorkflowAppKeyRequestResult.GRANTED:
            await self._async_set_api_key(api_key)
            await self._async_get_name()
        await self.hass.config_entries.flow.async_configure(
            self.flow_id, {"result": result},
        )

    async def _async_set_api_key(self, api_key):
        self._api_key = api_key
        await self.hass.async_add_executor_job(self._client.load_api_key, api_key)

    async def _async_get_name(self):
        settings = await self.hass.async_add_executor_job(self._client.settings)
        _LOGGER.debug("Got settings: %s", settings)
        self._name = settings["appearance"]["name"]

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        data_schema = vol.Schema({CONF_URL: str, CONF_USERNAME: str})
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=data_schema)

        errors = {}
        try:
            self._url = user_input[CONF_URL]
            self._username = user_input[CONF_USERNAME]
            workflow = await self._async_init_workflow()
            _LOGGER.debug("Workflow supported: %s", workflow)
            if workflow:
                return await self.async_step_app_keys_workflow()
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_app_keys_workflow(self, user_input=None):
        """Handle the workflow step."""
        if not user_input:
            return self.async_external_step(step_id="app_keys_workflow", url=self._url)
        self._workflow_result = user_input["result"]
        return self.async_external_step_done(next_step_id="app_keys_workflow_result")

    async def async_step_app_keys_workflow_result(self, user_input=None):
        """Handle the workflow result step."""
        _LOGGER.debug("Workflow result step: %s %s", self._api_key, self._name)
        if self._workflow_result == WorkflowAppKeyRequestResult.GRANTED:
            return await self.async_step_finish()
        if self._workflow_result == WorkflowAppKeyRequestResult.NOPE:
            return self.async_abort(reason="auth_denied")
        if self._workflow_result == WorkflowAppKeyRequestResult.TIMED_OUT:
            return self.async_abort(reason="timed_out")
        return self.async_abort(reason="unknown")

    async def async_step_finish(self, user_input=None):
        """Handle the final step."""
        data_schema = vol.Schema({vol.Optional(CONF_NAME, default=self._name): str})
        if user_input is None:
            return self.async_show_form(step_id="finish", data_schema=data_schema)
        self._name = user_input[CONF_NAME]
        data = {
            CONF_NAME: self._name,
            CONF_URL: self._url,
            CONF_USERNAME: self._username,
            CONF_API_KEY: self._api_key,
        }
        _LOGGER.debug("Creating entry: %s %s", self._name, data)
        return self.async_create_entry(title=self._name, data=data)
