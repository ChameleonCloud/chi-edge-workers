from datetime import datetime, timezone

from chi_edge_coordinator.update_lock import device_should_lock

NOW = datetime(2026, 3, 20, 18, 0, 0, tzinfo=timezone.utc)


def _res(start, end):
    return {"start_date": start, "end_date": end}


def test_no_reservations():
    assert device_should_lock([], now=NOW) is False


def test_active_reservation():
    allocs = [_res("2026-03-20T17:00:00.000000", "2026-03-20T19:00:00.000000")]
    assert device_should_lock(allocs, now=NOW) is True


def test_past_reservation():
    allocs = [_res("2026-03-20T15:00:00.000000", "2026-03-20T17:00:00.000000")]
    assert device_should_lock(allocs, now=NOW) is False


def test_upcoming_within_guard():
    allocs = [_res("2026-03-20T18:10:00.000000", "2026-03-20T20:00:00.000000")]
    assert device_should_lock(allocs, guard_minutes=15, now=NOW) is True


def test_upcoming_outside_guard():
    allocs = [_res("2026-03-20T19:00:00.000000", "2026-03-20T20:00:00.000000")]
    assert device_should_lock(allocs, guard_minutes=15, now=NOW) is False
