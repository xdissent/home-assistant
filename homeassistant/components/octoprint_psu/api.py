"""OctoPrint API Client."""

from octorest import OctoRest


class RestClient(OctoRest):
    """OctoPrint REST API Client."""

    def __init__(self, url):
        """Initialize the client."""
        super().__init__(url=url)
