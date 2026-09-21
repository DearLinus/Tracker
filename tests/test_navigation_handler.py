import pytest

from handlers.navigation import go_back


class FakeUser:
    def __init__(self):
        self.id = 123


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
async def test_go_back_resets_state():
    update = FakeUpdate()
    context = FakeContext()

    # populate some state
    context.user_data['awaiting'] = 'today_count'

    class FakeTracker:
        @staticmethod
        def delete_user_state(user_id, key):
            return None
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": FakeTracker()}

    await go_back(update, context)

    assert 'awaiting' not in context.user_data
    assert 'Main Menu' in update.message.replies[0]
