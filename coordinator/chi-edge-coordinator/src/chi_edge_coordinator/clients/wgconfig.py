import logging
import subprocess
from ipaddress import IPv4Network
from pathlib import Path

LOG = logging.getLogger(__name__)

WIREGUARD_CONF = "/etc/wireguard"
WIREGUARD_INTERFACE = "wg-calico"
SUBNET_SIZE = 24


class WireguardManager(object):
    wg_config_dir: str
    wg_interface_name: str
    wg_subnet_mask: int
    wg_private_key_path: Path
    wg_public_key_path: Path

    def __init__(
        self,
        wg_config_dir=WIREGUARD_CONF,
        wg_interface_name=WIREGUARD_INTERFACE,
        wg_subnet_mask=SUBNET_SIZE,
    ) -> None:
        self.wg_config_dir = wg_config_dir
        self.wg_interface_name = wg_interface_name

    def _generate_private_key(self):
        proc = subprocess.run(
            ["wg", "genkey"], capture_output=True, check=True, text=True
        )
        return proc.stdout.strip()

    def _write_key_to_file(self, key_path: Path, key_value: str):
        LOG.info("New private key written to file!")
        key_path.write_text(key_value)
        key_path.chmod(0o600)

    def _generate_public_key(self, private_key):
        proc = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            check=True,
            text=True,
        )
        return proc.stdout.strip()

    def get_wireguard_keys(self):
        """Return wireguard private, public keypair, generating new if needed."""

        private_key_name = "{}.key".format(self.wg_interface_name)
        private_key_file = Path(self.wg_config_dir, private_key_name)

        # if private key file is missing or empty, overwrite it
        try:
            private_key = private_key_file.read_text()
        except FileNotFoundError:
            private_key = None

        if not private_key:
            private_key = self._generate_private_key()
            self._write_key_to_file(key_path=private_key_file, key_value=private_key)

        # always generate public key from private key, one less thing to sync
        public_key = self._generate_public_key(private_key=private_key)
        return private_key, public_key

    def sync_config(self, channel, private_key_s):
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
            properties = peer.get("properties", {})
            pubkey = properties.get("public_key")
            endpoint = properties.get("endpoint")
            ip_address = properties.get("ip")

            if not pubkey or not endpoint:
                LOG.info("WARNING: Peer missing pubkey or endpoint: %s", peer)
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
            LOG.info("Writing tunnel configuration")
            wg_conf.write_text(config_text)
            wg_conf.chmod(0o600)
            wg_restart = True

        if not wg_ipv4.exists() or wg_ipv4.read_text() != ipv4_text:
            LOG.info("Writing new IPv4 configuration")
            wg_ipv4.write_text(ipv4_text)
            wg_restart = True
        return wg_restart
