import os
import subprocess
import time
import traceback
from ipaddress import IPv4Network
from pathlib import Path

import requests
from keystoneauth1 import adapter, session
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


def get_channel(hardware, channel_name):
    channel_workers = [w for w in hardware["workers"] if w["worker_type"] == "tunelo"]
    if not channel_workers:
        raise RuntimeError("Missing information for tunnel configuration")

    channels = hardware["properties"].get("channels", {})
    existing_channel = channels.get(channel_name, {}).copy()
    existing_channel.update(
        channel_workers[0]["state_details"].get("channels", {}).get(channel_name, {})
    )

    return existing_channel


def get_channel_patch(hardware, channel_name, pubkey):
    expected_channel = {"channel_type": "wireguard", "public_key": pubkey}

    channels = hardware["properties"].get("channels")
    if channels is None:
        # Corner case, no channels defined at all (Doni should really default this to
        # an empty obj better)
        return [
            {
                "op": "add",
                "path": "/properties/channels",
                "value": {channel_name: expected_channel},
            }
        ]

    existing_channel = channels.get(channel_name)
    if not existing_channel or existing_channel.get("public_key") != pubkey:
        return [
            {
                "op": "replace" if existing_channel else "add",
                "path": f"/properties/channels/{channel_name}",
                "value": expected_channel,
            }
        ]

    return []


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

    if wg_restart:
        restart_service("wireguard")


def sync_device_name(hardware, balena_device_name):
    hardware_name = hardware["name"]
    if hardware_name == balena_device_name:
        return

    if os.getenv("BALENA_SUPERVISOR_OVERRIDE_LOCK") != "1":
        print("Not updating hostname because update lock is in place")
        return
    print(f"Updating device hostname to {hardware_name}")
    call_supervisor(
        "/v1/device/host-config",
        method="patch",
        json={
            "network": {
                "hostname": hardware["name"],
            },
        },
    )


def restart_service(service_name):
    status = call_supervisor("/v2/state/status")
    running_service = next(
        iter(
            c
            for c in status["containers"]
            if c["status"] == "Running" and c["serviceName"] == service_name
        ),
        None,
    )
    # Only restart it if it was not explicitly stopped or is updating
    if running_service:
        print(f"Restarting {service_name} service")
        call_supervisor(
            f"/v2/applications/{running_service['appId']}/restart-service",
            method="post",
            json={
                "serviceName": service_name,
            },
        )


def call_supervisor(path, method="get", json=None):
    # If the Balena device name does not match, update it from hardware via
    # calling the Balena supervisor.
    supervisor_api_url = os.getenv("BALENA_SUPERVISOR_ADDRESS")
    supervisor_api_key = os.getenv("BALENA_SUPERVISOR_API_KEY")
    if not (supervisor_api_url and supervisor_api_key):
        raise RuntimeError("Missing Balena supervisor configuration")

    res = requests.request(
        method, f"{supervisor_api_url}{path}?apikey={supervisor_api_key}", json=json
    )
    res.raise_for_status()
    try:
        data = res.json()
    except ValueError:
        print("Supervisor Response content is not valid JSON")
    else:
        return data


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

def get_tunelo_client():
    auth_url = os.getenv("OS_AUTH_URL")
    application_credential_id = os.getenv("OS_APPLICATION_CREDENTIAL_ID")
    application_credential_secret = os.getenv("OS_APPLICATION_CREDENTIAL_SECRET")

    if not (auth_url and application_credential_id and application_credential_secret):
        raise RuntimeError(
            "Missing authentication parameters for channel API"
        )

    auth = application_credential.ApplicationCredential(
        auth_url,
        application_credential_id=application_credential_id,
        application_credential_secret=application_credential_secret,
    )
    client = session.Session(auth)
    return adapter.Adapter(client, interface="public", service_type="channel")


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
        hardware = doni.get(f"/v1/hardware/{device_uuid}/").json()

        device_name = os.getenv("BALENA_DEVICE_NAME_AT_INIT", "")
        sync_device_name(hardware, device_name)

        wg_privkey, wg_pubkey = get_wireguard_keys()
        user_channel_patch = get_channel_patch(hardware, "user", wg_pubkey)

        if user_channel_patch:
            print(f"Updating channel public key to {wg_pubkey}")
            res = doni.patch(
                f"/v1/hardware/{device_uuid}/",
                json=user_channel_patch,
                raise_exc=False,
            )
            if res.status_code != 200:
                raise Exception(
                    f"Failed to update public key in inventory: {res.json()}"
                )
            # try a little quicker b/c Neutron should apply the change and generate
            # a new IP address for our end of the channel.
            return 10.0



        channel_uuid = get_channel(hardware, "user").get("uuid")
        # for our end, fetch directly from tunelo, not doni
        tunelo = get_tunelo_client()
        tunelo_channel = tunelo.get(f"/channels/{channel_uuid}/").json()

        sync_wireguard_config(tunelo_channel, wg_privkey)

    except Exception as exc:
        traceback.print_exc()


if __name__ == "__main__":
    while True:
        sleep_interval = main() or 60.0
        time.sleep(60.0)
