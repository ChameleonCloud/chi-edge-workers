import unittest
from unittest.mock import Mock, patch

from chi_edge_coordinator.clients.balena import BalenaSupervisorClient

from tests.unit import fakes

FAKE_SUPERVISOR_PATH = "/v2/foo"
FAKE_BALENA_SUPERVISOR_ADDRESS = "http://127.0.0.1"
FAKE_BALENA_SUPERVISOR_API_KEY = "asdf123"


class TestBalena(unittest.TestCase):
    fake_response = {"result": [{"foo": "bar", "baz": True}]}

    def setUp(self) -> None:
        super().setUp()
        self.client = BalenaSupervisorClient(
            FAKE_BALENA_SUPERVISOR_ADDRESS,
            FAKE_BALENA_SUPERVISOR_API_KEY,
        )

    @patch("chi_edge_coordinator.clients.balena.requests.request")
    def test_call_supervisor_empty_response(self, mock_request):
        # mock the response from request to supervisor
        # in this case, we don't throw a status code, but still have empty response
        mock_response = Mock(status_code=200)
        mock_response.json.side_effect = ValueError()
        mock_request.return_value = mock_response

        response = self.client.call_supervisor(FAKE_SUPERVISOR_PATH)
        self.assertEqual(response, {})
        self.assertRaises(ValueError)

    @patch("chi_edge_coordinator.clients.balena.requests.request")
    def test_call_supervisor_valid_response(self, mock_request):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = self.fake_response
        mock_request.return_value = mock_response

        response = self.client.call_supervisor(FAKE_SUPERVISOR_PATH)
        self.assertEqual(response, self.fake_response)

    @patch.object(BalenaSupervisorClient, "call_supervisor")
    def test_restart_service_running(self, mock_call_supervisor: Mock):
        mock_call_supervisor.side_effect = [fakes.FAKE_BALENA_STATE_STATUS, None]

        self.client.restart_service(fakes.FAKE_BALENA_SERVICE_NAME)
        mock_call_supervisor.assert_any_call("/v2/state/status")
        self.assertEqual(mock_call_supervisor.call_count, 2)

    @patch.object(BalenaSupervisorClient, "call_supervisor")
    def test_restart_service_not_running(self, mock_call_supervisor):
        mock_call_supervisor.side_effect = [fakes.FAKE_BALENA_STATE_STATUS, None]

        self.client.restart_service(fakes.FAKE_BALENA_SERVICE_MISSING)

        # Should only call once (get status), not restart since service not running
        self.assertEqual(mock_call_supervisor.call_count, 1)
        mock_call_supervisor.assert_called_once_with("/v2/state/status")

    @patch.object(BalenaSupervisorClient, "call_supervisor")
    def test_find_k3s_service(self, mock_call_supervisor: Mock):
        mock_status = {
            "containers": [
                {"serviceName": "coordinator"},
                {"serviceName": "wireguard"},
                {"serviceName": "k3s-fake-01"},
            ]
        }

        mock_call_supervisor.return_value = mock_status
        result = self.client.find_k3s_service_name()
        self.assertEqual(result, "k3s-fake-01")

    @patch.object(BalenaSupervisorClient, "call_supervisor")
    def test_find_k3s_service_multiple(self, mock_call_supervisor: Mock):
        mock_status = {
            "containers": [
                {"serviceName": "coordinator"},
                {"serviceName": "wireguard"},
                {"serviceName": "k3s-fake-01"},
                {"serviceName": "k3s-fake-02"},
            ]
        }

        mock_call_supervisor.return_value = mock_status
        with self.assertRaises(RuntimeError):
            self.client.find_k3s_service_name()
