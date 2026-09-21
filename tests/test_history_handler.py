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
        self.bot_data = {}


@pytest.mark.asyncio
async def test_history_without_records(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    class FakeTracker:
        @staticmethod
        def get_records(user_id):
            return {}
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


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

    from timezone import DEFAULT_TIMEZONE

    today = datetime.now(
        ZoneInfo(DEFAULT_TIMEZONE)
    ).date()


    class FakeTracker:
        @staticmethod
        def get_records(user_id):
            return {today: 8}
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


    await show_history(
        update,
        context
    )


    assert (
        "8"
        in update.message.replies[0]
    )


@pytest.mark.asyncio
async def test_history_marks_missing_days_as_no_record(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from timezone import DEFAULT_TIMEZONE

    today = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date()
    recent_day = today - __import__("datetime").timedelta(days=1)

    class FakeTracker:
        @staticmethod
        def get_records(user_id):
            return {recent_day: 8}
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}

    await show_history(update, context)

    text = update.message.replies[0]
    assert "No record" in text
    assert f"{recent_day.strftime('%Y-%m-%d')} → 8" in text


@pytest.mark.asyncio
async def test_history_uses_correct_user_id(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    called = []


    def fake_get_records(user_id):

        called.append(user_id)

        return {}


    class FakeTracker:
        def get_records(self, user_id):
            return fake_get_records(user_id)
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


    await show_history(
        update,
        context
    )


    assert called == [
        123
    ]