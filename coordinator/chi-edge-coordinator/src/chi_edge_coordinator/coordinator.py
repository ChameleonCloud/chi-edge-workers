import logging
import os
import time
import traceback

from keystoneauth1.identity.v3 import application_credential

from chi_edge_coordinator import utils
from chi_edge_coordinator.clients import wgconfig
from chi_edge_coordinator.clients.balena import BalenaSupervisorClient
from chi_edge_coordinator.clients.openstack import DoniClient, TuneloClient

LOG = logging.getLogger(__name__)


def mainLoop():
    # initialize supervisor client from env vars
    supervisor = BalenaSupervisorClient(
        supervisor_api_address=os.getenv("BALENA_SUPERVISOR_ADDRESS"),
        supervisor_api_key=os.getenv("BALENA_SUPERVISOR_API_KEY"),
    )

    # initialize openstack clients from env vars
    keystone_auth = application_credential.ApplicationCredential(
        auth_url=os.getenv("OS_AUTH_URL"),  # type: ignore
        application_credential_id=os.getenv("OS_APPLICATION_CREDENTIAL_ID"),  # type: ignore
        application_credential_secret=os.getenv("OS_APPLICATION_CREDENTIAL_SECRET"),  # type: ignore
    )
    doni = DoniClient(auth=keystone_auth)
    tunelo = TuneloClient(auth=keystone_auth)

    # ensure that balena hostname matches doni "name"
    device_uuid = utils.uuid_hex_to_dashed(os.getenv("BALENA_DEVICE_UUID", ""))
    hardware = doni.get_hardware(device_uuid)
    supervisor.sync_device_hostname(name=hardware["name"])

    # ensure that wireguard private key is present, generating it if necessary
    wg_privkey, wg_pubkey = wgconfig.get_wireguard_keys()

    # if we have a new private key, tell Doni to update the hub port
    # on the first run, this might change the assigned IP address for our spoke port
    user_channel_patch = utils.get_channel_patch(hardware, "user", wg_pubkey)
    if user_channel_patch:
        LOG.info(f"Updating channel public key to {wg_pubkey}")
        doni.patch_hardware(uuid=device_uuid, jsonpatch=user_channel_patch)

    # ensure that we synchronize our end to the spoke port config.
    # Fetch this from tunelo, as it has more up to date information than Doni

    channel_uuid = utils.get_channel(hardware, "user").get("uuid")
    tunelo_channel = tunelo.get_channel(channel_uuid)

    # update local side of configuration to match any updated peers or IP changes
    wg_changed = wgconfig.sync_wireguard_config(tunelo_channel, wg_privkey)

    # restart services to pick up new config
    if wg_changed:
        LOG.info("restarting wg service")
        supervisor.restart_service("wireguard")

        # look up name of k3s service. Could be different depending on device
        k3s_name = supervisor.find_k3s_service_name()
        LOG.info(f"restarting k3s service {k3s_name}")
        supervisor.restart_service(k3s_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    while True:
        try:
            mainLoop()
        except Exception:
            traceback.print_exc()

        # poll for changes every 60 seconds
        time.sleep(60.0)
