import pytest

from handlers.constants import BACK_BUTTON
from handlers.router import handle_text


class FakeUser:
    def __init__(self):
        self.id = 123


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
        self.bot_data = {}


@pytest.mark.asyncio
async def test_unknown_message_clears_state(monkeypatch):
    update = FakeUpdate("I am lost")
    context = FakeContext()

    # Simulate persisted awaiting state
    context.user_data['awaiting'] = 'today_count'

    class FakeTracker:
        @staticmethod
        def user_exists(user_id):
            return True
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

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    await handle_text(update, context)

    # awaiting should be cleared
    assert context.user_data.get('awaiting') is None


@pytest.mark.asyncio
async def test_old_button_does_not_fire_after_unknown(monkeypatch):
    # After an unknown message, pressing a previous button shouldn't trigger its action
    update = FakeUpdate("I am lost")
    context = FakeContext()
    context.user_data['awaiting'] = 'today_count'

    class FakeTracker:
        @staticmethod
        def user_exists(user_id):
            return True
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

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    # user sends unknown message
    await handle_text(update, context)

    # now user presses back button; ensure only go_back is called, not save_today
    update2 = FakeUpdate(BACK_BUTTON)

    called = []

    async def fake_go_back(update, context):
        called.append('back')

    async def fake_save_today(update, context):
        called.append('save')

    monkeypatch.setattr('handlers.router.go_back', fake_go_back)
    monkeypatch.setattr('handlers.router.save_today_record', fake_save_today)

    await handle_text(update2, context)

    assert called == ['back']
