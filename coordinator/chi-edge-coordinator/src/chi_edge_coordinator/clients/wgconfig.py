import subprocess
from ipaddress import IPv4Network
from pathlib import Path

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
