from chi_edge_coordinator.clients.wgconfig import WireguardManager

import unittest
from unittest.mock import Mock, patch

from tests.unit import fakes


FAKE_CONFIG_PATH = "/var/lib/foo"
FAKE_INTERACE_NAME = "wg-baz"
FAKE_SUBNET_MASK = 29

FAKE_PRIVKEY = "foo-bar-baz-nope"
FAKE_PUBKEY = "this_is_a_pubkey"


class TestWireguardManager(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = WireguardManager(
            wg_config_dir=FAKE_CONFIG_PATH,
            wg_interface_name=FAKE_INTERACE_NAME,
            wg_subnet_mask=FAKE_SUBNET_MASK,
        )

        self.mock_gen_privkey = patch.object(
            WireguardManager, "_generate_private_key"
        ).start()
        self.mock_gen_pubkey = patch.object(
            WireguardManager, "_generate_public_key"
        ).start()
        self.mock_write_privkey = patch.object(
            WireguardManager, "_write_key_to_file"
        ).start()
        self.mock_privkey_path = patch(
            "chi_edge_coordinator.clients.wgconfig.Path"
        ).start()

    def test_get_wireguard_keys(self):
        """Case where private key file is already populated"""

        self.mock_privkey_path.return_value.read_text.return_value = FAKE_PRIVKEY
        self.mock_gen_pubkey.return_value = FAKE_PUBKEY

        privkey, pubkey = self.client.get_wireguard_keys()

        # ensure we don't try to override privkey when it already exists!
        self.mock_gen_privkey.assert_not_called()
        self.mock_write_privkey.assert_not_called()

        # we always generate the publickey from privkey
        self.mock_gen_pubkey.assert_called_once()

        self.assertEqual(privkey, FAKE_PRIVKEY)
        self.assertEqual(pubkey, FAKE_PUBKEY)

    def test_gen_wg_privkey(self):
        self.mock_privkey_path.return_value.read_text.return_value = None
        self.mock_gen_privkey.return_value = FAKE_PRIVKEY
        self.mock_gen_pubkey.return_value = FAKE_PUBKEY

        privkey, pubkey = self.client.get_wireguard_keys()

        # ensure we generate and write privkey
        self.mock_gen_privkey.assert_called_once()
        self.mock_write_privkey.assert_called_once()

        # we always generate the publickey from privkey
        self.mock_gen_pubkey.assert_called_once()

        self.assertEqual(privkey, FAKE_PRIVKEY)
        self.assertEqual(pubkey, FAKE_PUBKEY)
