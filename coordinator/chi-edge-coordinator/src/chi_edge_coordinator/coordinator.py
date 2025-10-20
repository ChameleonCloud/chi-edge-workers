import os
import time
import traceback

from keystoneauth1.identity.v3 import application_credential

from chi_edge_coordinator import utils
from chi_edge_coordinator.clients import balena, wgconfig
from chi_edge_coordinator.clients.openstack import DoniClient, TuneloClient


def mainLoop():
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

    device_name = os.getenv("BALENA_DEVICE_NAME_AT_INIT", "")
    balena.sync_device_name(hardware, device_name)

    wg_privkey, wg_pubkey = wgconfig.get_wireguard_keys()
    user_channel_patch = utils.get_channel_patch(hardware, "user", wg_pubkey)

    if user_channel_patch:
        print(f"Updating channel public key to {wg_pubkey}")
        result = doni.patch_hardware(uuid=device_uuid, jsonpatch=user_channel_patch)

    channel_uuid = utils.get_channel(hardware, "user").get("uuid")
    # for our end, fetch directly from tunelo, not doni
    tunelo_channel = tunelo.get_channel(channel_uuid)

    wg_changed = wgconfig.sync_wireguard_config(tunelo_channel, wg_privkey)

    if wg_changed:
        balena.restart_service("wireguard")

        # look up name of k3s service. Could be different depending on device
        k3s_services = balena.find_k3s_services()
        if len(k3s_services) == 0:
            print("No services starting with 'k3s' found!")
        elif len(k3s_services) > 1:
            print("More than one service starting with 'k3s' found!")
        else:
            k3s_service_name = k3s_services[0]
            balena.restart_service(k3s_service_name)


if __name__ == "__main__":
    while True:
        try:
            mainLoop()
        except Exception:
            traceback.print_exc()

        # poll for changes every 60 seconds
        time.sleep(60.0)
