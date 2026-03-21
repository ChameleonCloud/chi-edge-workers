import logging

from keystoneauth1.adapter import Adapter
from keystoneauth1.session import Session

LOG = logging.getLogger(__name__)


class OpenstackClient(Adapter):
    def __init__(self, auth, service_type) -> None:
        super().__init__(
            session=Session(auth),
            interface="public",
            service_type=service_type,
        )


class DoniClient(OpenstackClient):
    def __init__(self, auth) -> None:
        super().__init__(auth, service_type="inventory")

    def get_hardware(self, uuid):
        path = "/v1/hardware/{}".format(uuid)
        result = self.get(url=path)
        return result.json()

    def patch_hardware(self, uuid, jsonpatch):
        LOG.debug("sending patch: %s", jsonpatch)
        path = "/v1/hardware/{}".format(uuid)
        result = self.patch(url=path, json=jsonpatch)
        return result.json()


class TuneloClient(OpenstackClient):
    def __init__(self, auth) -> None:
        super().__init__(auth, service_type="channel")

    def get_channel(self, uuid):
        path = "/channels/{}".format(uuid)
        result = self.get(url=path)
        return result.json()


class BlazarClient(OpenstackClient):
    def __init__(self, auth) -> None:
        super().__init__(auth, service_type="reservation")

    def get_device_id(self, device_name):
        result = self.get(url="/devices")
        for device in result.json()["devices"]:
            if device.get("name") == device_name:
                return device["id"]
        return None

    def get_device_allocations(self, device_id):
        result = self.get(url="/devices/allocations")
        for device in result.json()["allocations"]:
            if device["resource_id"] == device_id:
                return device.get("reservations", [])
        return []
