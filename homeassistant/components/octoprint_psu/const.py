"""Constants for the OctoPrint PSU integration."""

from homeassistant.const import TEMP_CELSIUS, TIME_SECONDS, UNIT_PERCENTAGE

DOMAIN = "octoprint_psu"

DEFAULT_NAME = "OctoPrint"

CONF_REVOKE_API_KEY = "revoke_api_key"
CONF_BED = "bed"
CONF_NUMBER_OF_TOOLS = "number_of_tools"

BINARY_SENSOR_TYPES = {
    # API Endpoint, Group, Key, unit
    "Printing": ["printer", "state", "printing", None],
    "Printing Error": ["printer", "state", "error", None],
}

SENSOR_TYPES = {
    # API Endpoint, Group, Key, unit, icon
    "Temperatures": ["printer", "temperature", "*", TEMP_CELSIUS],
    "Current State": ["printer", "state", "text", None, "mdi:printer-3d"],
    "Job Percentage": [
        "job",
        "progress",
        "completion",
        UNIT_PERCENTAGE,
        "mdi:file-percent",
    ],
    "Time Remaining": [
        "job",
        "progress",
        "printTimeLeft",
        TIME_SECONDS,
        "mdi:clock-end",
    ],
    "Time Elapsed": ["job", "progress", "printTime", TIME_SECONDS, "mdi:clock-start"],
}
