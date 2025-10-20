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


class TuneloClient(OpenstackClient):
    def __init__(self, auth) -> None:
        super().__init__(auth, service_type="channel")
