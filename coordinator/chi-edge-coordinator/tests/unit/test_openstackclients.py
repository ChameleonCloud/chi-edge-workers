from chi_edge_coordinator.clients.openstack import (
    OpenstackClient,
    DoniClient,
    TuneloClient,
)
import unittest
from unittest.mock import Mock, patch

from tests.unit import fakes


class TestTuneloClient(unittest.TestCase):
    """Tests for Tunelo channel client implementation."""

    pass


class TestDoniClient(unittest.TestCase):
    """Tests for Doni hardware/inventory client implementation."""

    client: DoniClient

    def setUp(self) -> None:
        self.client = DoniClient(fakes.FAKE_APP_CREDENTIAL)
        return super().setUp()

    @patch("chi_edge_coordinator.clients.openstack.ksAdapter.get")
    def test_get_hardware(self, patched_request: Mock):
        result = self.client.get_hardware(fakes.FAKE_HARDWARE_UUID)

        patched_request.assert_called_once()
        patched_request.assert_called_with(url="/v1/hardware/22-33-44-55")


class TestKeystoneClient(unittest.TestCase):
    """Tests for keystone identity client implementation."""

    pass
