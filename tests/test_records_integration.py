"""
Integration tests: handlers -> real TrackerLogic -> real SQLite.

The unit tests in test_records_handler.py mock the tracker, so they could
not catch a mismatch between what the handler calls and what logic.py
actually accepts. These tests use a real temporary database instead.
"""

import pytest

from logic import TrackerLogic
from timezone import get_today

from handlers.records import save_today_record, save_new_record


class FakeUser:
    id = 123
    username = "test_user"


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, text):
        self.effective_user = FakeUser()
        self.message = FakeMessage(text)


class FakeContext:
    def __init__(self):
        self.user_data = {}


@pytest.fixture
def real_tracker(tmp_path, monkeypatch, mock_sticker):
    logic = TrackerLogic(str(tmp_path / "test.db"))
    logic.create_user(FakeUser.id, FakeUser.username)

    monkeypatch.setattr("handlers.records.get_tracker", lambda ctx: logic, raising=True)
    return logic


@pytest.mark.asyncio
async def test_today_record_can_be_overwritten(real_tracker):
    day = get_today()

    await save_today_record(FakeUpdate("3"), FakeContext())
    assert real_tracker.get_record(FakeUser.id, day) == 3

    update = FakeUpdate("5")
    await save_today_record(update, FakeContext())

    assert real_tracker.get_record(FakeUser.id, day) == 5
    assert "saved successfully" in update.message.replies[-1]


@pytest.mark.asyncio
async def test_new_record_reports_added_then_updated(real_tracker):
    first = FakeUpdate("2026-01-10 4")
    await save_new_record(first, FakeContext())
    assert "Action: Added" in first.message.replies[-1]

    second = FakeUpdate("2026-01-10 9")
    await save_new_record(second, FakeContext())
    assert "Action: Updated" in second.message.replies[-1]

    from datetime import date
    assert real_tracker.get_record(FakeUser.id, date(2026, 1, 10)) == 9