import pytest

from handlers.settings import (
    change_graph_theme,
    confirm_delete_data,
    request_delete_data,
    show_settings,
)


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
async def test_show_settings_sets_state(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    monkeypatch.setattr(
        "handlers.settings.get_graph_theme",
        lambda update, context: "dark"
    )

    # provide a minimal tracker for user state operations
    class _StateTracker:
        @staticmethod
        def delete_user_state(user_id, key):
            return None
        @staticmethod
        def set_user_state(user_id, key, value):
            return None

    from tests.helpers import autospec_tracker

    context.bot_data["tracker"] = autospec_tracker(_StateTracker())

    await show_settings(
        update,
        context
    )


    assert (
        context.user_data["awaiting"]
        ==
        "settings"
    )


    assert (
        "Dark"
        in update.message.replies[0]
    )



@pytest.mark.asyncio
async def test_change_graph_theme_saves_setting(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    saved = []


    class FakeTracker:
        def set_setting(self, user_id, key, value):
            saved.append((user_id, key, value))
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


    await change_graph_theme(
        update,
        context,
        "dark"
    )


    assert saved == [
        (
            123,
            "graph_theme",
            "dark"
        )
    ]


    assert (
        "awaiting"
        not in context.user_data
    )


    assert (
        "Dark graph enabled"
        in update.message.replies[0]
    )


@pytest.mark.asyncio
async def test_change_graph_theme_invalid_theme(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    class FakeTracker:
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    # Provide no-op persisted-state methods used by clear_user_state
    FakeTracker.delete_user_state = staticmethod(lambda user_id, key: None)
    FakeTracker.set_user_state = staticmethod(lambda user_id, key, value: None)
    FakeTracker.get_user_state = staticmethod(lambda user_id, key: None)

    await change_graph_theme(update, context, "not-a-theme")

    assert "Invalid theme" in update.message.replies[0]


@pytest.mark.asyncio
async def test_delete_data_flow(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    # Minimal tracker that reports deletion
    class FakeTracker:
        def __init__(self):
            self.deleted = False

        def delete_user(self, user_id):
            self.deleted = True
            return True

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

    # Request delete sets confirmation state and sends confirmation message
    await request_delete_data(update, context)
    assert context.user_data.get("awaiting") == "confirm_delete"
    assert "7 days" in update.message.replies[0]

    # Confirm deletion
    update2 = FakeUpdate()
    context2 = FakeContext()
    context2.bot_data = {"tracker": FakeTracker()}

    await confirm_delete_data(update2, context2, True)
    assert "scheduled for deletion" in update2.message.replies[0].lower()


@pytest.mark.asyncio
async def test_delete_data_cancel(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    class FakeTracker:
        @staticmethod
        def delete_user(user_id):
            return False

        @staticmethod
        def set_user_state(user_id, key, value):
            return None

        @staticmethod
        def get_user_state(user_id, key):
            return None

        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": FakeTracker()}

    await confirm_delete_data(update, context, False)
    assert "Deletion cancelled" in update.message.replies[0]