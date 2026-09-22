import pytest

from handlers.start import start
from handlers.utils import _parse_allowed_user_ids, is_user_allowed


class FakeUser:
    def __init__(self, id=123, username="user"):
        self.id = id
        self.username = username


class FakeMessage:
    def __init__(self, text=None):
        self.replies = []
        self.text = text

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)

    async def reply_document(self, *args, **kwargs):
        pass


class FakeUpdate:
    def __init__(self, user_id=123, text=None):
        self.effective_user = FakeUser(user_id)
        self.message = FakeMessage(text)


class FakeContext:
    def __init__(self):
        self.user_data = {}
        self.bot_data = {}


@pytest.mark.parametrize("env,expected", [
    (None, set()),
    ("123, 456", {123, 456}),
    ("  7 ,8,9  ", {7, 8, 9}),
    ("bad,10", {10}),
])
def test_parse_allowed_user_ids(env, expected, monkeypatch):
    if env is None:
        monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    else:
        monkeypatch.setenv("ALLOWED_USER_IDS", env)

    assert _parse_allowed_user_ids() == expected


@pytest.mark.parametrize("env", ["", "bad", "bad,not-a-number", " , "])
def test_parse_allowed_user_ids_rejects_invalid_configured_value(env, monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", env)

    with pytest.raises(ValueError, match="ALLOWED_USER_IDS"):
        _parse_allowed_user_ids()


@pytest.mark.asyncio
async def test_is_user_allowed_raises_for_invalid_allowlist_configuration(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "invalid")

    with pytest.raises(ValueError, match="ALLOWED_USER_IDS"):
        is_user_allowed(1)


@pytest.mark.asyncio
async def test_is_user_allowed_when_not_configured(monkeypatch):
    monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    assert is_user_allowed(1) is True


@pytest.mark.asyncio
async def test_is_user_allowed_when_in_list(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "10,20,30")
    assert is_user_allowed(20) is True
    assert is_user_allowed(999) is False


@pytest.mark.asyncio
async def test_blocked_user_cannot_create_user(monkeypatch):
    # configure allowed list with a different id
    monkeypatch.setenv("ALLOWED_USER_IDS", "999")

    update = FakeUpdate(user_id=123)
    context = FakeContext()

    # Provide a tracker so start() would attempt to create user if allowed
    class FakeTracker:
        def create_user(self, user_id, username):
            raise RuntimeError("should not be called")

        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": FakeTracker()}

    await start(update, context)

    assert any("not authorized" in r.lower() for r in update.message.replies)
    