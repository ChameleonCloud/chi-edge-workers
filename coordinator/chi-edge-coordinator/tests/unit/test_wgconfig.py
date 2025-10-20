import unittest
from unittest.mock import Mock, patch

from chi_edge_coordinator.clients import wgconfig

from tests.unit import fakes


class TestGetWireguardKeys(unittest.TestCase):
    @patch("chi_edge_coordinator.clients.wgconfig.Path")
    @patch("chi_edge_coordinator.clients.wgconfig.subprocess")
    def test_get_wireguard_keys_existing(self, mock_subprocess, mock_path):
        mock_private_keyfile = Mock()
        mock_private_keyfile.exists.return_value = True
        mock_private_keyfile.read_text.return_value = "private_key"
        mock_path.return_value = mock_private_keyfile

        private_key, public_key = wgconfig.get_wireguard_keys()

        self.assertEqual(private_key, "private_key")
        self.assertEqual(mock_subprocess.run.call_count, 1)

    @patch("chi_edge_coordinator.clients.wgconfig.Path")
    @patch("chi_edge_coordinator.clients.wgconfig.subprocess")
    def test_get_wireguard_keys_generate(self, mock_subprocess, mock_path):
        mock_private_keyfile = Mock()
        mock_private_keyfile.exists.return_value = False
        mock_path.return_value = mock_private_keyfile

        mock_subprocess.run.side_effect = [
            Mock(stdout="private_key\n"),
            Mock(stdout="public_key\n"),
        ]

        private_key, public_key = wgconfig.get_wireguard_keys()

        self.assertEqual(private_key, "private_key")
        self.assertEqual(public_key, "public_key")
        self.assertEqual(mock_subprocess.run.call_count, 2)
