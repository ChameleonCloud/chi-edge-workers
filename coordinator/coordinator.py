from ipaddress import IPv4Network
import os
from pathlib import Path
import subprocess
import time
import traceback

from keystoneauth1 import adapter, session
from keystoneauth1.identity.v3 import application_credential
import requests

WIREGUARD_CONF = "/etc/wireguard"
WIREGUARD_INTERFACE = "wg-calico"
SUBNET_SIZE = 24


def sleep_forever(message):
    while True:
        print(message)
        time.sleep(60.0)


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


def get_user_channel(hardware):
    channel_name = "user"
    channel = hardware["properties"].get("channels", {}).get(channel_name, {}).copy()

    channel_workers = [w for w in hardware["workers"] if w["worker_type"] == "tunelo"]
    if not channel_workers:
        raise RuntimeError("Missing information for tunnel configuration")
    channel.update(
        channel_workers[0]["state_details"].get("channels", {}).get(channel_name, {})
    )

    return channel


def sync_wireguard_config(channel, private_key_s):
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
        # TODO: this is hacky; netmask should be on the peer somehow
        allowed_ips = str(IPv4Network(f"{peer['ip']}/{SUBNET_SIZE}", strict=False))
        config_lines.extend(
            [
                "[Peer]",
                f"PublicKey = {peer['public_key']}",
                f"AllowedIPs = {allowed_ips}",
                f"Endpoint = {peer['endpoint']}",
                "PersistentKeepalive = 15",
                "",
            ]
        )

    print("Writing tunnel configuration")

    wg_conf = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.conf")
    wg_conf.write_text("\n".join(config_lines))
    wg_conf.chmod(0o600)

    wg_ipv4 = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.ipv4")
    wg_ipv4.write_text(f"{channel.get('ip')}/{SUBNET_SIZE}")


def sync_device_name(hardware, balena_device_name):
    # If the Balena device name does not match, update it from hardware via
    # calling the Balena supervisor.
    supervisor_api_url = os.getenv("BALENA_SUPERVISOR_ADDRESS")
    supervisor_api_key = os.getenv("BALENA_SUPERVISOR_API_KEY")
    if not (supervisor_api_url and supervisor_api_key):
        raise RuntimeError("Missing Balena supervisor configuration")

    if os.getenv("BALENA_SUPERVISOR_OVERRIDE_LOCK") != "1":
        print("Not updating hostname because update lock is in place")
        return

    hardware_name = hardware["name"]
    if hardware_name != balena_device_name:
        print(f"Updating device hostname to {hardware_name}")
        res = requests.patch(
            f"{supervisor_api_url}/v1/device/host-config",
            json={
                "network": {
                    "hostname": hardware["name"],
                },
            },
        )
        res.raise_for_status()


def get_doni_client():
    auth_url = os.getenv("OS_AUTH_URL")
    application_credential_id = os.getenv("OS_APPLICATION_CREDENTIAL_ID")
    application_credential_secret = os.getenv("OS_APPLICATION_CREDENTIAL_SECRET")

    if not (auth_url and application_credential_id and application_credential_secret):
        raise RuntimeError(
            "Missing authentication parameters for device enrollment API"
        )

    auth = application_credential.ApplicationCredential(
        auth_url,
        application_credential_id=application_credential_id,
        application_credential_secret=application_credential_secret,
    )
    client = session.Session(auth)
    return adapter.Adapter(client, interface="public", service_type="inventory")


def main():
    try:
        device_uuid = os.getenv("BALENA_DEVICE_UUID", "").lower()
        # Inventory service uses hyphenated UUIDs
        device_uuid = "-".join(
            [
                device_uuid[:8],
                device_uuid[8:12],
                device_uuid[12:16],
                device_uuid[16:20],
                device_uuid[20:],
            ]
        )
        doni = get_doni_client()
        print(f"Fetching {device_uuid} device description from inventory")
        hardware = doni.get(f"/v1/hardware/{device_uuid}/").json()

        device_name = os.getenv("BALENA_DEVICE_NAME_AT_INIT", "")
        sync_device_name(hardware, device_name)

        user_channel = get_user_channel(hardware)

        wg_privkey, wg_pubkey = get_wireguard_keys()
        if not user_channel or wg_pubkey != user_channel.get("public_key"):
            print(
                f"Updating public key to {wg_pubkey} (from {user_channel.get('public_key')})"
            )
            res = doni.patch(
                f"/v1/hardware/{device_uuid}/",
                json=[
                    {
                        "op": "replace" if user_channel else "add",
                        "path": "/properties/channels/user",
                        "value": {
                            "channel_type": "wireguard",
                            "public_key": wg_pubkey,
                        },
                    }
                ],
                raise_exc=False,
            )
            if res.status_code != 200:
                raise Exception(
                    f"Failed to update public key in inventory: {res.json()}"
                )
            # try a little quicker b/c Neutron should apply the change and generate
            # a new IP address for our end of the channel.
            return 10.0

        sync_wireguard_config(user_channel, wg_privkey)

    except Exception as exc:
        traceback.print_exc()
        sleep_forever(str(exc))


while True:
    sleep_interval = main() or 60.0
    time.sleep(60.0)
