import os
import subprocess
import time
import traceback
from ipaddress import IPv4Network
from pathlib import Path

from chi_edge_coordinator.clients import balena
from chi_edge_coordinator.clients.openstack import DoniClient, TuneloClient
from chi_edge_coordinator import utils

from keystoneauth1.identity.v3 import application_credential

WIREGUARD_CONF = "/etc/wireguard"
WIREGUARD_INTERFACE = "wg-calico"
SUBNET_SIZE = 24


def get_wireguard_keys():
    private_keyfile = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.key")
    if private_keyfile.exists():
        private_key = private_keyfile.read_text()
    else:
        print("Generating new tunnel private key")
        proc = subprocess.run(
            ["wg", "genkey"], capture_output=True, check=True, text=True
        )
        private_key = proc.stdout.strip()
        private_keyfile.write_text(private_key)
        private_keyfile.chmod(0o600)

    proc = subprocess.run(
        ["wg", "pubkey"], input=private_key, capture_output=True, check=True, text=True
    )
    public_key = proc.stdout.strip()

    return private_key, public_key


def sync_wireguard_config(channel, private_key_s) -> bool:
    if not channel:
        raise RuntimeError("User channel not configured!")

    config_lines = [
        "[Interface]",
        f"PrivateKey = {private_key_s}",
        "",
    ]

    peers = channel.get("peers")
    if not peers:
        raise RuntimeError("Missing peer configuration")

    for peer in peers:
        # tunelo peer has structure
        # uuid
        # status
        # properties
        #   public_key
        #   endpoint
        #   ip

        properties = peer.get("properties", {})
        pubkey = properties.get("public_key")
        endpoint = properties.get("endpoint")
        ip_address = properties.get("ip")

        if not pubkey or not endpoint:
            print("WARNING: Peer missing pubkey or endpoint: %s", peer)
            continue

        # TODO: this is hacky; netmask should be on the peer somehow
        allowed_ips = str(IPv4Network(f"{ip_address}/{SUBNET_SIZE}", strict=False))

        config_lines.extend(
            [
                "[Peer]",
                f"PublicKey = {pubkey}",
                f"AllowedIPs = {allowed_ips}",
                f"Endpoint = {endpoint}",
                "PersistentKeepalive = 15",
                "",
            ]
        )

    wg_conf = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.conf")
    wg_ipv4 = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.ipv4")
    wg_restart = False

    config_text = "\n".join(config_lines)

    channel_properties = channel.get("properties", {})
    channel_bind_ip = channel_properties.get("ip")
    ipv4_text = f"{channel_bind_ip}/{SUBNET_SIZE}"

    if not wg_conf.exists() or wg_conf.read_text() != config_text:
        print("Writing tunnel configuration")
        wg_conf.write_text(config_text)
        wg_conf.chmod(0o600)
        wg_restart = True

    if not wg_ipv4.exists() or wg_ipv4.read_text() != ipv4_text:
        print("Writing new IPv4 configuration")
        wg_ipv4.write_text(ipv4_text)
        wg_restart = True

    return wg_restart


def main():
    try:
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

        wg_privkey, wg_pubkey = get_wireguard_keys()
        user_channel_patch = utils.get_channel_patch(hardware, "user", wg_pubkey)

        if user_channel_patch:
            print(f"Updating channel public key to {wg_pubkey}")
            result = doni.patch_hardware(uuid=device_uuid, jsonpatch=user_channel_patch)

        channel_uuid = utils.get_channel(hardware, "user").get("uuid")
        # for our end, fetch directly from tunelo, not doni
        tunelo_channel = tunelo.get_channel(channel_uuid)

        wg_changed = sync_wireguard_config(tunelo_channel, wg_privkey)

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

    except Exception as exc:
        traceback.print_exc()


if __name__ == "__main__":
    while True:
        sleep_interval = main() or 60.0
        time.sleep(60.0)
