from keystoneauth1.adapter import Adapter
from keystoneauth1.session import Session


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
