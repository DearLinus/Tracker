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
    def __init__(self, tracker=None):
        self.user_data = {
            "awaiting": "something"
        }
        self.bot_data = {}
        if tracker is not None:
            self.bot_data["tracker"] = tracker


@pytest.mark.asyncio
async def test_start_creates_user(mock_sticker):

    created_users = []

    def fake_create_user(user_id, username):
        created_users.append(
            (user_id, username)
        )

    class FakeTracker1:
        def create_user(self, user_id, username):
            return fake_create_user(user_id, username)
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    update = FakeUpdate()
    context = FakeContext(tracker=FakeTracker1())


    await start(
        update,
        context
    )


    assert created_users == [
        (123, "test_user")
    ]


@pytest.mark.asyncio
async def test_start_sends_welcome_message(mock_sticker):

    class FakeTracker2:
        def create_user(self, *args):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    update = FakeUpdate()
    context = FakeContext(tracker=FakeTracker2())


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
async def test_start_resets_state(mock_sticker):

    class FakeTracker3:
        def create_user(self, *args):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    update = FakeUpdate()
    context = FakeContext(tracker=FakeTracker3())


    await start(
        update,
        context
    )


    assert (
        "awaiting"
        not in context.user_data
    )