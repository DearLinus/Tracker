import pytest

from handlers.history import show_history


class FakeUser:
    def __init__(self):
        self.id = 123
        self.username = "test_user"


class FakeMessage:

    def __init__(self):
        self.replies = []


    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:

    def __init__(self):
        self.effective_user = FakeUser()
        self.message = FakeMessage()


class FakeContext:

    def __init__(self):
        self.user_data = {}


@pytest.mark.asyncio
async def test_history_without_records(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    monkeypatch.setattr(
        "handlers.history.tracker.get_records",
        lambda *args: {}
    )


    await show_history(
        update,
        context
    )


    assert (
        "You don't have any records"
        in update.message.replies[0]
    )


@pytest.mark.asyncio
async def test_history_shows_records(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    from datetime import datetime
    from zoneinfo import ZoneInfo

    today = datetime.now(
        ZoneInfo("Europe/London")
    ).date()


    monkeypatch.setattr(
        "handlers.history.tracker.get_records",
        lambda *args: {
            today: 8
        }
    )


    await show_history(
        update,
        context
    )


    assert (
        "8"
        in update.message.replies[0]
    )


@pytest.mark.asyncio
async def test_history_uses_correct_user_id(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    called = []


    def fake_get_records(user_id):

        called.append(user_id)

        return {}


    monkeypatch.setattr(
        "handlers.history.tracker.get_records",
        fake_get_records
    )


    await show_history(
        update,
        context
    )


    assert called == [
        123
    ]