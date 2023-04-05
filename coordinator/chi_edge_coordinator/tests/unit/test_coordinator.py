import os
import unittest
from unittest.mock import Mock, patch

import requests

from chi_edge_coordinator import coordinator

FAKE_CHANNEL_NAME = "fake_channel"
FAKE_CHANNEL = {}
FAKE_HARDWARE = {
    "workers": [
        {
            "worker_type": "tunelo",
            "state_details": {},
        },
    ],
    "properties": {
        "channels": {
            FAKE_CHANNEL_NAME: {},
        },
    },
}

FAKE_SUPERVISOR_PATH = "/v2/foo"
FAKE_BALENA_SUPERVISOR_ADDRESS = "http://127.0.0.1"
FAKE_BALENA_SUPERVISOR_API_KEY = "asdf123"


class TestChannels(unittest.TestCase):
    def test_get_channel(self):
        channel = coordinator.get_channel(FAKE_HARDWARE, FAKE_CHANNEL_NAME)
        self.assertIsNotNone(channel)

    # def test_get_channel_patch(self):
    #     raise NotImplemented


@patch.dict(os.environ, {"BALENA_SUPERVISOR_ADDRESS": FAKE_BALENA_SUPERVISOR_ADDRESS})
@patch.dict(os.environ, {"BALENA_SUPERVISOR_API_KEY": FAKE_BALENA_SUPERVISOR_API_KEY})
class TestBalena(unittest.TestCase):
    fake_response = {"result": [{"foo": "bar", "baz": True}]}

    @patch("chi_edge_coordinator.coordinator.requests.request")
    def test_call_supervisor_empty_response(self, mock_request):
        # mock the response from request to supervisor
        # in this case, we don't throw a status code, but still have empty response
        mock_response = Mock(status_code=200)
        mock_response.json.side_effect = ValueError()
        mock_request.return_value = mock_response

        response = coordinator.call_supervisor(FAKE_SUPERVISOR_PATH)
        self.assertIsNone(response)
        self.assertRaises(ValueError)

    @patch("chi_edge_coordinator.coordinator.requests.request")
    def test_call_supervisor_valid_response(self, mock_request):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = self.fake_response
        mock_request.return_value = mock_response

        response = coordinator.call_supervisor(FAKE_SUPERVISOR_PATH)
        self.assertEquals(response, self.fake_response)

    def test_restart_service(self):
        raise NotImplemented

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
