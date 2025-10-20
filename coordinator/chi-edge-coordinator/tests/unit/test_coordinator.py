import os
import unittest
from unittest.mock import Mock, patch

from tests.unit import fakes
import requests

from chi_edge_coordinator import coordinator


class TestChannels(unittest.TestCase):
    def test_get_channel(self):
        channel = coordinator.get_channel(fakes.FAKE_HARDWARE, fakes.FAKE_CHANNEL_NAME)
        self.assertIsNotNone(channel)

    # def test_get_channel_patch(self):
    #     raise NotImplemented

    # def test_sync_device_name(self):
    #     raise NotImplemented


# class TestWireguard(unittest.TestCase):
#     def test_wireguard_keys(self):
#         raise NotImplemented

#     def test_sync_wireguard_config(self):
#         raise NotImplemented


# class TestDoni(unittest.TestCase):
#     def test_get_doni_client(self):
#         raise NotImplemented


if __name__ == "__main__":
    unittest.main()
