import pytest

from handlers.utils import is_private_chat
from handlers.start import start


class FakeChat:
    def __init__(self, type):
        self.type = type


class FakeMessage:
    def __init__(self, chat_type="private"):
        self.chat = FakeChat(chat_type)
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUser:
    def __init__(self, id=123, username="user"):
        self.id = id
        self.username = username


class FakeUpdate:
    def __init__(self, chat_type="private", user_id=123):
        self.message = FakeMessage(chat_type)
        self.effective_user = FakeUser(user_id)


class FakeContext:
    def __init__(self, tracker=None):
        self.user_data = {}
        self.bot_data = {}
        if tracker is not None:
            self.bot_data["tracker"] = tracker


def test_is_private_chat():
    assert is_private_chat(FakeUpdate(chat_type="private")) is True
    assert is_private_chat(FakeUpdate(chat_type="group")) is False


@pytest.mark.asyncio
async def test_group_chat_rejected(monkeypatch):

    update = FakeUpdate(chat_type="group")
    context = FakeContext()

    class FakeTracker:
        def create_user(self, *args, **kwargs):
            raise RuntimeError("should not be called")

    context.bot_data = {"tracker": FakeTracker()}

    await start(update, context)

    assert any("only works in private" in r.lower() for r in update.message.replies)


@pytest.mark.asyncio
async def test_private_chat_allowed(monkeypatch):
    update = FakeUpdate(chat_type="private")
    context = FakeContext()

    created = []
    class FakeTracker2:
        def create_user(self, user_id, username):
            created.append((user_id, username))
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": FakeTracker2()}

    await start(update, context)

    assert created == [(123, "user")]
 