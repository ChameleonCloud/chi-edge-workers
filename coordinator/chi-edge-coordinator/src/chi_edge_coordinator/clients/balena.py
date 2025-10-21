import logging
import os
from urllib.parse import urljoin

import requests

LOG = logging.getLogger(__name__)


class BalenaSupervisorClient(object):
    """Implements REST API communication with balena supervisor.

    See https://docs.balena.io/reference/supervisor/supervisor-api/
    """

    supervisor_address = ""
    supervisor_api_key = ""

    def __init__(self, supervisor_api_address, supervisor_api_key):
        """Initialize URL and api key for supervisor"""

        self.supervisor_address = supervisor_api_address
        self.supervisor_api_key = supervisor_api_key

        if not (self.supervisor_address and self.supervisor_api_key):
            raise RuntimeError("Missing Balena supervisor configuration")

    def ping(self) -> bool:
        """Checks if we can contact supervisor."""

        path = urljoin(self.supervisor_address, "ping")  # type: ignore
        response = requests.get(url=path)
        return response.ok

    def call_supervisor(self, path, method="get", json=None) -> dict:
        """Send authenticated http request to the supervisor."""

        request_path = urljoin(self.supervisor_address, path)  # type: ignore

        headers = {"Content-Type": "application/json"}
        params = {"apikey": self.supervisor_api_key}

        response = requests.request(
            method=method,
            url=request_path,
            params=params,
            headers=headers,
            json=json,
        )

        response.raise_for_status()

        # handle case where sometimes supervisor returns 200, but no data
        try:
            data = response.json()
        except ValueError:
            LOG.warning("No JSON data returned from supervisor for %s", path)
            data = {}

        return data

    def _restart_service(self, app_id, service_name):
        path = "/v2/applications/{}/restart-service".format(app_id)

        self.call_supervisor(
            path=path, method="post", json={"serviceName": service_name}
        )

    def restart_service(self, service_name):
        """Ask supervisor to restart a service by name."""

        status = self.call_supervisor("/v2/state/status")
        container_state_list = [
            s
            for s in status.get("containers", [])
            if s.get("serviceName") == service_name
        ]

        for container in container_state_list:
            containerStatus = container.get("status")
            if containerStatus == "Running":
                LOG.info("applying requested restart for service %s", service_name)
                self._restart_service(
                    app_id=container["appId"],
                    service_name=service_name,
                )
            else:
                LOG.warning(
                    "skipping restart, container %s in state %s",
                    service_name,
                    containerStatus,
                )

    def _set_device_hostname(self, name):
        """Call supervisor to update balena device's hostname."""
        LOG.info("Updating device hostname to %s", name)

        self.call_supervisor(
            path="/v1/device/host-config",
            method="patch",
            json={"network": {"hostname": name}},
        )

    def sync_device_hostname(self, name):
        """Call supervisor to update balena device's hostname."""

        balena_device_name = os.getenv("BALENA_DEVICE_NAME_AT_INIT")
        if name == balena_device_name:
            return

        if os.getenv("BALENA_SUPERVISOR_OVERRIDE_LOCK") != "1":
            raise Exception("Skipping hostname change, update lock is set!")

        self.call_supervisor(
            path="/v1/device/host-config",
            method="patch",
            json={"network": {"hostname": name}},
        )

    def find_k3s_service_name(self) -> str:
        """Return name of k3s service on this device."""

        status: dict = self.call_supervisor("/v2/state/status")

        k3s_service_names = [
            c.get("serviceName")
            for c in status.get("containers", [])
            if c.get("serviceName", "").startswith("k3s")
        ]

        LOG.debug("found %s names for k3s", k3s_service_names)

        if len(k3s_service_names) == 1:
            return k3s_service_names[0]
        else:
            LOG.warning("Found 0 or >1 k3s services: %s", k3s_service_names)
            raise RuntimeError("K3s service not found, retry next iteration!")
