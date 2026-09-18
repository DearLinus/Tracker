import pytest

from handlers.start import start


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
        self.user_data = {
            "awaiting": "something"
        }


@pytest.mark.asyncio
async def test_start_creates_user(monkeypatch, mock_sticker):

    update = FakeUpdate()
    context = FakeContext()

    created_users = []

    def fake_create_user(user_id, username):
        created_users.append(
            (user_id, username)
        )

    monkeypatch.setattr(
        "handlers.start.tracker.create_user",
        fake_create_user
    )


    await start(
        update,
        context
    )


    assert created_users == [
        (123, "test_user")
    ]


@pytest.mark.asyncio
async def test_start_sends_welcome_message(monkeypatch, mock_sticker):

    update = FakeUpdate()
    context = FakeContext()

    monkeypatch.setattr(
        "handlers.start.tracker.create_user",
        lambda *args: None
    )


    await start(
        update,
        context
    )


    assert len(
        update.message.replies
    ) == 1

    assert (
        "Welcome to Daily Tracker"
        in update.message.replies[0]
    )


@pytest.mark.asyncio
async def test_start_resets_state(monkeypatch, mock_sticker):

    update = FakeUpdate()
    context = FakeContext()

    monkeypatch.setattr(
        "handlers.start.tracker.create_user",
        lambda *args: None
    )


    await start(
        update,
        context
    )


    assert (
        "awaiting"
        not in context.user_data
    )