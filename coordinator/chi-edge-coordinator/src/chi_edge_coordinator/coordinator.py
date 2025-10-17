import logging

import os
import time
import traceback

import utils
from keystoneauth1.identity.v3 import application_credential

from chi_edge_coordinator.clients.balena import BalenaSupervisorClient
from chi_edge_coordinator.clients.openstack import DoniClient, TuneloClient
from chi_edge_coordinator.clients.wgconfig import WireguardManager

LOG = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)

    # initialize supervisor client from env vars
    supervisor = BalenaSupervisorClient(
        supervisor_api_address=os.getenv("BALENA_SUPERVISOR_ADDRESS"),
        supervisor_api_key=os.getenv("BALENA_SUPERVISOR_API_KEY"),
    )

    # initialize openstack clients from env vars
    keystone_auth = application_credential.ApplicationCredential(
        auth_url=os.getenv("OS_AUTH_URL"),
        application_credential_id=os.getenv("OS_APPLICATION_CREDENTIAL_ID"),
        application_credential_secret=os.getenv("OS_APPLICATION_CREDENTIAL_SECRET"),
    )
    doni = DoniClient(auth=keystone_auth)
    tunelo = TuneloClient(auth=keystone_auth)

    # ensure that balena hostname matches doni "name"
    device_uuid = utils.uuid_hex_to_dashed(os.getenv("BALENA_DEVICE_UUID", ""))
    hardware = doni.get_hardware(device_uuid)
    supervisor.sync_device_hostname(name=hardware["name"])

    # ensure that wireguard private key is present, generating it if necessary
    wg_manager = WireguardManager()
    wg_private_key, wg_public_key = wg_manager.get_wireguard_keys()

    # if we have a new private key, tell Doni to update the hub port
    # on the first run, this might change the assigned IP address for our spoke port
    user_channel_patch = utils.get_channel_patch(hardware, "user", wg_public_key)
    if user_channel_patch:
        LOG.info(f"Updating channel public key to {wg_public_key}")
        result = doni.patch_hardware(uuid=device_uuid, jsonpatch=user_channel_patch)

    # ensure that we synchronize our end to the spoke port config.
    # Fetch this from tunelo, as it has more up to date information than Doni

    channel_uuid = utils.get_channel(hardware, "user").get("uuid")
    tunelo_channel = tunelo.get_channel(channel_uuid)

    # update local side of configuration to match any updated peers or IP changes
    wg_changed = wg_manager.sync_config(tunelo_channel, wg_private_key)

    # restart services to pick up new config
    if wg_changed:
        print("restarting wg service")
        supervisor.restart_service("wireguard")

        k3s_name = supervisor.find_k3s_service_name()
        print(f"restarting k3s service {k3s_name}")
        supervisor.restart_service(k3s_name)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            traceback.print_exc()

        # poll for changes every 60 seconds
        time.sleep(60.0)
