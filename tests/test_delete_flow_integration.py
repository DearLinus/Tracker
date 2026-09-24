from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from handlers.settings import (
    confirm_delete_data,
    request_delete_data,
    restore_delete_data,
)
from logic import TrackerLogic
from services.tracker_service import setup_application


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, user_id):
        self.effective_user = SimpleNamespace(id=user_id, username="u")
        self.message = FakeMessage()


class FakeContext:
    def __init__(self, app):
        self.bot_data = app.bot_data
        self.application = app
        self.user_data = {}


@pytest.mark.asyncio
async def test_delete_button_creates_pending_deletion_instead_of_immediate_delete(tmp_path):
    db_path = str(tmp_path / "test_tracker.db")
    app = SimpleNamespace()
    tracker = setup_application(app, db_path=db_path)
    user_id = 42
    tracker.create_user(user_id, "u")

    update = FakeUpdate(user_id)
    context = FakeContext(app)

    await request_delete_data(update, context)
    assert context.user_data.get("awaiting") == "confirm_delete"

    await confirm_delete_data(update, context, True)

    assert tracker.user_exists(user_id) is True
    assert tracker.get_pending_deletion(user_id) is not None
    assert "scheduled for deletion" in update.message.replies[-1].lower()
    assert "7 days" in update.message.replies[-1]


@pytest.mark.asyncio
async def test_recovery_snapshot_is_created_outside_sqlite_and_encrypted(tmp_path):
    db_path = str(tmp_path / "tracker.db")
    tracker = TrackerLogic(db_path=db_path)
    user_id = 77
    tracker.create_user(user_id, "u")
    record_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    tracker.save_record(user_id, record_date, 5)

    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    recovery_dir = tmp_path / "recovery"
    assert recovery_dir.exists()
    files = list(recovery_dir.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".enc"
    raw = files[0].read_bytes()
    assert b"records" not in raw
    assert b"enc:" not in raw
    assert tracker.recovery_storage.exists(user_id) is True


@pytest.mark.asyncio
async def test_restore_after_database_reopen_uses_external_recovery_snapshot(tmp_path):
    db_path = str(tmp_path / "tracker.db")
    tracker = TrackerLogic(db_path=db_path)
    user_id = 88
    tracker.create_user(user_id, "u")
    record_date = datetime.now(timezone.utc).date() - timedelta(days=2)
    tracker.save_record(user_id, record_date, 9)
    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    reopened = TrackerLogic(db_path=db_path)
    assert reopened.restore_pending_deletion(user_id, now=now + timedelta(days=3)) is True
    assert reopened.get_pending_deletion(user_id) is None
    assert reopened.get_record(user_id, record_date) == 9
    assert reopened.recovery_storage.exists(user_id) is False


@pytest.mark.asyncio
async def test_restore_after_bot_restart_uses_external_recovery_snapshot(tmp_path):
    db_path = str(tmp_path / "tracker.db")
    app = SimpleNamespace()
    tracker = setup_application(app, db_path=db_path)
    user_id = 99
    tracker.create_user(user_id, "u")
    record_date = datetime.now(timezone.utc).date() - timedelta(days=3)
    tracker.save_record(user_id, record_date, 3)
    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    restarted = setup_application(SimpleNamespace(), db_path=db_path)
    assert restarted.restore_pending_deletion(user_id, now=now + timedelta(days=2)) is True
    assert restarted.get_record(user_id, record_date) == 3


@pytest.mark.asyncio
async def test_recovery_storage_is_user_isolated(tmp_path):
    db_path = str(tmp_path / "tracker.db")
    tracker = TrackerLogic(db_path=db_path)
    user_a = 101
    user_b = 202
    tracker.create_user(user_a, "a")
    tracker.create_user(user_b, "b")
    record_date = datetime.now(timezone.utc).date() - timedelta(days=4)
    tracker.save_record(user_a, record_date, 4)
    tracker.save_record(user_b, record_date, 7)

    tracker.request_pending_deletion(user_a, now=datetime.now(timezone.utc))

    assert tracker.recovery_storage.exists(user_a) is True
    assert tracker.recovery_storage.exists(user_b) is False


@pytest.mark.asyncio
async def test_cleanup_expired_deletions_removes_active_data_and_recovery_file(tmp_path):
    db_path = str(tmp_path / "tracker.db")
    tracker = TrackerLogic(db_path=db_path)
    user_id = 303
    tracker.create_user(user_id, "u")
    record_date = datetime.now(timezone.utc).date() - timedelta(days=5)
    tracker.save_record(user_id, record_date, 6)
    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    assert tracker.recovery_storage.exists(user_id) is True

    deleted = tracker.cleanup_expired_deletions(now=now + timedelta(days=8))
    assert deleted == [user_id]
    assert tracker.recovery_storage.exists(user_id) is False
    assert tracker.get_pending_deletion(user_id) is None
    assert tracker.user_exists(user_id) is False

    with pytest.raises(ValueError, match="User does not exist|does not exist"):
        tracker.get_record(user_id, record_date)


@pytest.mark.asyncio
async def test_user_cannot_create_records_while_pending(tmp_path):
    tracker = TrackerLogic(db_path=str(tmp_path / "pending.db"))
    user_id = 7
    tracker.create_user(user_id, "u")

    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    with pytest.raises(ValueError, match="pending deletion|pending"):
        tracker.save_record(user_id, date(2026, 9, 24), 3)


@pytest.mark.asyncio
async def test_restore_works_before_deadline(tmp_path):
    tracker = TrackerLogic(db_path=str(tmp_path / "restore_before.db"))
    user_id = 8
    tracker.create_user(user_id, "u")
    tracker.set_setting(user_id, "graph_theme", "light")
    tracker.save_record(user_id, date(2026, 9, 24), 5)

    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    restored = tracker.restore_pending_deletion(user_id, now=now + timedelta(days=3))
    assert restored is True
    assert tracker.get_pending_deletion(user_id) is None
    assert tracker.get_setting(user_id, "graph_theme") == "light"
    assert tracker.get_record(user_id, date(2026, 9, 24)) == 5


@pytest.mark.asyncio
async def test_restore_fails_after_deadline(tmp_path):
    tracker = TrackerLogic(db_path=str(tmp_path / "restore_after.db"))
    user_id = 9
    tracker.create_user(user_id, "u")

    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    assert tracker.restore_pending_deletion(user_id, now=now + timedelta(days=7, seconds=1)) is False
    assert tracker.get_pending_deletion(user_id) is not None


@pytest.mark.asyncio
async def test_restart_keeps_pending_deletion_state(tmp_path):
    db_path = str(tmp_path / "restart_pending.db")
    tracker = TrackerLogic(db_path=db_path)
    user_id = 10
    tracker.create_user(user_id, "u")
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    restarted = TrackerLogic(db_path=db_path)
    assert restarted.get_pending_deletion(user_id) is not None
    assert restarted.user_exists(user_id) is True


@pytest.mark.asyncio
async def test_restore_button_restores_pending_user(tmp_path):
    db_path = str(tmp_path / "restore_button.db")
    app = SimpleNamespace()
    tracker = setup_application(app, db_path=db_path)
    user_id = 11
    tracker.create_user(user_id, "u")
    tracker.save_record(user_id, date(2026, 9, 24), 7)
    now = datetime.now(timezone.utc)
    tracker.request_pending_deletion(user_id, now=now)

    update = FakeUpdate(user_id)
    context = FakeContext(app)
    await restore_delete_data(update, context)

    assert tracker.get_pending_deletion(user_id) is None
    assert tracker.get_record(user_id, date(2026, 9, 24)) == 7
    assert "restored" in update.message.replies[-1].lower()
