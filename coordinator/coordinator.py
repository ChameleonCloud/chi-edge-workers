import base64
import os
from pathlib import Path
import time

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
)
from keystoneauth1 import adapter, session
from keystoneauth1.identity.v3 import application_credential

WIREGUARD_CONF = "/etc/wireguard"
WIREGUARD_INTERFACE = "wg-calico"


def sleep_forever(message):
    while True:
        print(message)
        time.sleep(60.0)


def get_wireguard_keys():
    is_new = False
    private_keyfile = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.key")
    if private_keyfile.exists():
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            private_keyfile.read_bytes()
        )
    else:
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_keyfile.write_bytes(
            private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw)
        )
        private_keyfile.chmod(0o600)
        is_new = True

    private_key_s = base64.standard_b64encode(
        private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw)
    ).decode("utf-8")
    public_key_s = base64.standard_b64encode(
        private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("utf-8")

    return private_key_s, public_key_s, is_new


def get_user_channel(hardware):
    channel_workers = [w for w in hardware["workers"] if w["worker_type"] == "tunelo"]
    if not channel_workers:
        raise RuntimeError("Missing information for tunnel configuration")

    return channel_workers[0]["state_details"].get("channels", {}).get("user")


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
        config_lines.extend(
            [
                "[Peer]",
                f"PublicKey = {peer['public_key']}",
                # TODO: this is hacky; this should be on the peer somehow
                f"AllowedIPs = {peer['ip']}/24",
                f"Endpoint = {peer['endpoint']}",
                "PersistentKeepalive = 15",
                "",
            ]
        )

    wg_conf = Path(WIREGUARD_CONF, f"{WIREGUARD_INTERFACE}.conf")
    wg_conf.write_text("\n".join(config_lines))
    wg_conf.chmod(0o600)


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
            [device_uuid[:12], device_uuid[12:16], device_uuid[16:20], device_uuid[20:]]
        )
        doni = get_doni_client()
        hardware = doni.get(f"/v1/hardware/{device_uuid}/")
        user_channel = get_user_channel(hardware)

        wg_privkey, wg_pubkey, wg_is_new = get_wireguard_keys()
        if wg_is_new:
            doni.patch(
                f"/v1/hardware/{device_uuid}/",
                json=[
                    {
                        "op": "replace" if user_channel else "add",
                        "path": "/channels/user",
                        "value": {
                            "channel_type": "wireguard",
                            "public_key": wg_pubkey,
                        },
                    }
                ],
            )
            return True

        sync_wireguard_config(user_channel, wg_privkey)

    except Exception as exc:
        print(str(exc))
    else:
        return False


try_again = True
while try_again:
    try_again = main()
    time.sleep(10.0)

print("Finished coordination")
