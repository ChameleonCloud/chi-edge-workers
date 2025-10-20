import unittest
from unittest.mock import Mock, patch
import os

from tests.unit import fakes
from chi_edge_coordinator.clients import balena


@patch.dict(
    os.environ, {"BALENA_SUPERVISOR_ADDRESS": fakes.FAKE_BALENA_SUPERVISOR_ADDRESS}
)
@patch.dict(
    os.environ, {"BALENA_SUPERVISOR_API_KEY": fakes.FAKE_BALENA_SUPERVISOR_API_KEY}
)
class TestBalena(unittest.TestCase):
    fake_response = {"result": [{"foo": "bar", "baz": True}]}

    @patch("chi_edge_coordinator.clients.balena.requests.request")
    def test_call_supervisor_empty_response(self, mock_request):
        # mock the response from request to supervisor
        # in this case, we don't throw a status code, but still have empty response
        mock_response = Mock(status_code=200)
        mock_response.json.side_effect = ValueError()
        mock_request.return_value = mock_response

        response = balena.call_supervisor(fakes.FAKE_SUPERVISOR_PATH)
        self.assertIsNone(response)
        self.assertRaises(ValueError)

    @patch("chi_edge_coordinator.clients.balena.requests.request")
    def test_call_supervisor_valid_response(self, mock_request):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = self.fake_response
        mock_request.return_value = mock_response

        response = balena.call_supervisor(fakes.FAKE_SUPERVISOR_PATH)
        self.assertEqual(response, self.fake_response)

    @patch.object(
        balena,
        "call_supervisor",
        side_effect=[fakes.FAKE_BALENA_STATE_STATUS, None],
    )
    def test_restart_service_running(self, patched_call_supervisor):
        balena.restart_service(fakes.FAKE_BALENA_SERVICE_NAME)
        self.assertEqual(patched_call_supervisor.call_count, 2)

    @patch.object(
        balena,
        "call_supervisor",
        side_effect=[fakes.FAKE_BALENA_STATE_STATUS, None],
    )
    def test_restart_service_not_running(self, patched_call_supervisor):
        balena.restart_service(fakes.FAKE_BALENA_SERVICE_MISSING)
        self.assertEqual(patched_call_supervisor.call_count, 1)
