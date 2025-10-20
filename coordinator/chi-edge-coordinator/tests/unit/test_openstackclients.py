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


class TestDoniClient(unittest.TestCase):
    """Tests for Doni hardware/inventory client implementation."""

    client: DoniClient

    def setUp(self) -> None:
        self.client = DoniClient(fakes.FAKE_APP_CREDENTIAL)
        super().setUp()
