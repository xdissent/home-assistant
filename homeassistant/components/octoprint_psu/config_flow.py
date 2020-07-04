"""Config flow for OctoPrint PSU integration."""
from collections import OrderedDict
import logging
from typing import Optional

from octorest import WorkflowAppKeyRequestResult
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL, CONF_USERNAME
from homeassistant.helpers.typing import DiscoveryInfoType

from .api import RestClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OctoPrint PSU."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize flow."""
        self._url: Optional[str] = None
        self._username: Optional[str] = None
        self._client: Optional[RestClient] = None
        self._workflow_result: Optional[WorkflowAppKeyRequestResult] = None
        self._api_key: Optional[str] = None
        self._name: Optional[str] = None

    async def _async_init_workflow(self):
        """Init the app keys workflow."""
        self._client = RestClient(self.hass, self._url)
        supported = await self._client.async_probe_app_keys_workflow_support()
        if not supported:
            return False
        self.hass.async_create_task(self._async_poll_workflow())
        return True

    async def _async_poll_workflow(self):
        """Poll the app keys workflow."""
        (result, api_key) = await self._client.async_try_get_api_key(
            f"Home Assistant ({self.flow_id})", self._username
        )
        if result == WorkflowAppKeyRequestResult.GRANTED:
            await self._async_set_api_key(api_key)
            await self._async_get_name()
        await self.hass.config_entries.flow.async_configure(
            self.flow_id, {"result": result},
        )

    async def _async_set_api_key(self, api_key):
        self._api_key = api_key
        await self._client.async_load_api_key(api_key)

    async def _async_get_name(self):
        settings = await self._client.async_settings()
        self._name = settings["appearance"]["name"]

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        fields = OrderedDict()
        fields[vol.Required(CONF_URL, default=self._url or vol.UNDEFINED)] = str
        fields[
            vol.Required(CONF_USERNAME, default=self._username or vol.UNDEFINED)
        ] = str

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema(fields))

        errors = {}
        try:
            self._url = _normalize_url(user_input[CONF_URL])
            self._username = user_input[CONF_USERNAME]
            workflow = await self._async_init_workflow()
            _LOGGER.debug("Workflow supported: %s", workflow)
            if workflow:
                return await self.async_step_app_keys_workflow()
            else:
                return await self.async_step_manual()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
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
        if self._workflow_result == WorkflowAppKeyRequestResult.WORKFLOW_UNSUPPORTED:
            return await self.async_step_manual()
        if self._workflow_result == WorkflowAppKeyRequestResult.GRANTED:
            return await self.async_step_finish()
        if self._workflow_result == WorkflowAppKeyRequestResult.NOPE:
            return self.async_abort(reason="auth_denied")
        if self._workflow_result == WorkflowAppKeyRequestResult.TIMED_OUT:
            return self.async_abort(reason="timed_out")
        return self.async_abort(reason="unknown")

    async def async_step_manual(self, user_input=None):
        """Handle manual step."""
        data_schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        if not user_input:
            return self.async_show_form(step_id="manual", data_schema=data_schema)

        errors = {}
        try:
            await self._async_set_api_key(user_input[CONF_API_KEY])
            await self._async_get_name()
            return await self.async_step_finish()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )

    async def async_step_finish(self, user_input=None):
        """Handle the final step."""
        data_schema = vol.Schema(
            {vol.Required(CONF_NAME, default=self._name or vol.UNDEFINED): str}
        )
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

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf step."""
        _LOGGER.debug("Zeroconf discovery info: %s", discovery_info)

        hostname = discovery_info["hostname"][:-1]
        proto = "https" if discovery_info["port"] == 443 else "http"
        port = discovery_info["port"]
        host = (
            hostname
            if (proto == "https" and port == 443) or (proto == "http" and port == 80)
            else f"{hostname}:{port}"
        )
        path = discovery_info["properties"].get("path", "/")
        self._url = _normalize_url(f"{proto}://{host}{path}")

        await self.async_set_unique_id(self._url)
        self._abort_if_unique_id_configured()

        _LOGGER.debug("Zeroconf form: %s", self._url)
        return await self.async_step_user()

    async def async_step_ssdp(self, discovery_info: DiscoveryInfoType):
        """Handle ssdp step."""
        _LOGGER.debug("SSDP discovery info: %s", discovery_info)

        hostname = discovery_info["hostname"][:-1]
        proto = "https" if discovery_info["port"] == 443 else "http"
        port = discovery_info["port"]
        host = (
            hostname
            if (proto == "https" and port == 443) or (proto == "http" and port == 80)
            else f"{hostname}:{port}"
        )
        path = discovery_info["properties"].get("path", "/")
        self._url = _normalize_url(f"{proto}://{host}{path}")

        await self.async_set_unique_id(self._url)
        self._abort_if_unique_id_configured()

        _LOGGER.debug("SSDP form: %s", self._url)
        return await self.async_step_user()
