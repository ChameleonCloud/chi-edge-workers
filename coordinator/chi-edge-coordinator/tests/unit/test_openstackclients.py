from chi_edge_coordinator.clients.openstack import (
    DoniClient,
    TuneloClient,
)
import unittest
from unittest.mock import Mock, patch

from tests.unit import fakes


class TestTuneloClient(unittest.TestCase):
    """Tests for Tunelo channel client implementation."""

    client: TuneloClient

    def setUp(self) -> None:
        self.client = TuneloClient(fakes.FAKE_APP_CREDENTIAL)
        super().setUp()

    def test_get_channel(self):
        with patch(
            "chi_edge_coordinator.clients.openstack.Adapter.get"
        ) as patched_request:
            result = self.client.get_channel(fakes.FAKE_CHANNEL_NAME)

            patched_request.assert_called_once()
            patched_request.assert_called_with(url="/channels/fake_channel")


class TestDoniClient(unittest.TestCase):
    """Tests for Doni hardware/inventory client implementation."""

    client: DoniClient

    def setUp(self) -> None:
        self.client = DoniClient(fakes.FAKE_APP_CREDENTIAL)
        super().setUp()

    @patch("chi_edge_coordinator.clients.openstack.Adapter.get")
    def test_get_hardware(self, patched_request: Mock):
        result = self.client.get_hardware(fakes.FAKE_HARDWARE_UUID)

        patched_request.assert_called_once()
        patched_request.assert_called_with(url="/v1/hardware/22-33-44-55")

    @patch("chi_edge_coordinator.clients.openstack.Adapter.patch")
    def test_patch_hardware(self, patched_request: Mock):
        result = self.client.patch_hardware(
            fakes.FAKE_HARDWARE_UUID, fakes.FAKE_HARDWARE_PATCH
        )

        patched_request.assert_called_once()
        patched_request.assert_called_with(
            url="/v1/hardware/22-33-44-55", json=fakes.FAKE_HARDWARE_PATCH
        )
