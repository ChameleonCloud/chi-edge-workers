import logging
from datetime import datetime, timedelta, timezone

from lockfile import LockFile

LOG = logging.getLogger(__name__)

LOCKFILE_PATH = "/tmp/balena/updates"
DEFAULT_GUARD_MINUTES = 15


def device_should_lock(allocations, guard_minutes=DEFAULT_GUARD_MINUTES, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    guard = timedelta(minutes=guard_minutes)

    for res in allocations:
        start = datetime.fromisoformat(res["start_date"]).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(res["end_date"]).replace(tzinfo=timezone.utc)

        # Active reservation, or one starting within guard window
        if end > now and (start - guard) <= now:
            return True

    return False


class UpdateLock:
    def __init__(self):
        self._lock = LockFile(LOCKFILE_PATH)
        # Clean up stale lock from a previous crash
        if self._lock.is_locked():
            LOG.info("Breaking stale update lock from previous run")
            self._lock.break_lock()

    @property
    def held(self):
        return self._lock.is_locked()

    def acquire(self):
        if self._lock.is_locked():
            return
        self._lock.acquire()
        LOG.info("Update lock acquired")

    def release(self):
        if not self._lock.is_locked():
            return
        self._lock.release()
        LOG.info("Update lock released")
