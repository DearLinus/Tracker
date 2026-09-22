import sqlite3

import pytest

from handlers.constants import (
    BACK_BUTTON,
    CONFIRM_NO_BUTTON,
    CONFIRM_YES_BUTTON,
    DARK_THEME,
    DARK_THEME_BUTTON,
    DELETE_DATA_BUTTON,
    EXPORT_BUTTON,
    HISTORY_BUTTON,
    LIGHT_THEME,
    LIGHT_THEME_BUTTON,
    NEW_RECORD_BUTTON,
    SETTINGS_BUTTON,
    STATISTICS_BUTTON,
    TODAY_RECORD_BUTTON,
)
from handlers.router import handle_text


class FakeUser:
    def __init__(self):
        self.id = 123
        self.username = "test_user"


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



# =========================================================
# user validation
# =========================================================


@pytest.mark.asyncio
async def test_router_rejects_unknown_user(monkeypatch):

    update = FakeUpdate("anything")
    context = FakeContext()

    class FakeTrackerA:
        @staticmethod
        def user_exists(user_id):
            return False
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

    context.bot_data = {"tracker": FakeTrackerA()}


    await handle_text(
        update,
        context
    )


    assert (
        "Please start the bot first"
        in update.message.replies[0]
    )



# =========================================================
# today record button
# =========================================================


@pytest.mark.asyncio
async def test_router_rejects_access_denied_user(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "999")
    update = FakeUpdate("anything")
    context = FakeContext()

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

    context.bot_data = {"tracker": FakeTracker()}

    await handle_text(update, context)

    assert "not authorized" in update.message.replies[0].lower()


@pytest.mark.asyncio
async def test_router_rejects_non_private_chat(monkeypatch):
    update = FakeUpdate("anything")
    update.message.chat = type("Chat", (), {"type": "group"})()
    context = FakeContext()

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

    context.bot_data = {"tracker": FakeTracker()}

    await handle_text(update, context)

    assert "private" in update.message.replies[0].lower()


@pytest.mark.asyncio
async def test_router_handles_clear_user_state_failure_gracefully(monkeypatch):
    update = FakeUpdate("I am lost")
    context = FakeContext()
    context.user_data["awaiting"] = "today_count"

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
            raise sqlite3.Error("database is locked")

    context.bot_data = {"tracker": FakeTracker()}

    await handle_text(update, context)

    assert "I didn't understand that" in update.message.replies[0]


@pytest.mark.asyncio
async def test_router_calls_today_record(monkeypatch):

    update = FakeUpdate(
        TODAY_RECORD_BUTTON
    )
    context = FakeContext()


    class FakeTrackerB:
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

    context.bot_data = {"tracker": FakeTrackerB()}


    called = []


    async def fake_start_today(update, context):
        called.append(True)


    monkeypatch.setattr(
        "handlers.router.start_today_record",
        fake_start_today
    )


    await handle_text(
        update,
        context
    )


    assert called == [True]



# =========================================================
# today count state
# =========================================================


@pytest.mark.asyncio
async def test_router_saves_today_record_when_waiting(monkeypatch):

    update = FakeUpdate(
        "8"
    )

    context = FakeContext()

    context.user_data["awaiting"] = "today_count"


    class FakeTrackerC:
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

    context.bot_data = {"tracker": FakeTrackerC()}


    called = []


    async def fake_save_today(update, context):
        called.append(True)


    monkeypatch.setattr(
        "handlers.router.save_today_record",
        fake_save_today
    )


    await handle_text(
        update,
        context
    )


    assert called == [True]


@pytest.mark.asyncio
async def test_router_allows_menu_action_while_waiting(monkeypatch):

    update = FakeUpdate("📈 Graph")
    context = FakeContext()
    context.user_data["awaiting"] = "today_count"

    class FakeTrackerD:
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

    context.bot_data = {"tracker": FakeTrackerD()}

    called = []

    async def fake_show_graph_menu(update, context):
        called.append(True)

    monkeypatch.setattr(
        "handlers.router.show_graph_menu",
        fake_show_graph_menu
    )

    await handle_text(update, context)

    assert called == [True]


@pytest.mark.asyncio
async def test_handle_text_ignores_empty_message():
    # No message -> nothing happens (no exception)
    update = type("U", (), {"message": None, "effective_user": type("User", (), {"id": 1})()})()
    context = FakeContext()

    # Should return gracefully
    await handle_text(update, context)


@pytest.mark.asyncio
async def test_back_button_calls_go_back(monkeypatch):
    update = FakeUpdate(BACK_BUTTON)
    context = FakeContext()

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

    called = []

    async def fake_go_back(update, context):
        called.append(True)

    monkeypatch.setattr("handlers.router.go_back", fake_go_back)

    await handle_text(update, context)

    assert called == [True]


@pytest.mark.asyncio
async def test_main_menu_calls_various_handlers(monkeypatch):
    update = FakeUpdate(NEW_RECORD_BUTTON)
    context = FakeContext()

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

    called = {}

    async def fake_new(update, context):
        called['new'] = True

    async def fake_stats(update, context):
        called['stats'] = True

    async def fake_history(update, context):
        called['history'] = True

    async def fake_settings(update, context):
        called['settings'] = True

    async def fake_export(update, context):
        called['export'] = True

    monkeypatch.setattr("handlers.router.start_new_record", fake_new)
    monkeypatch.setattr("handlers.router.show_statistics", fake_stats)
    monkeypatch.setattr("handlers.router.show_history", fake_history)
    monkeypatch.setattr("handlers.router.show_settings", fake_settings)
    monkeypatch.setattr("handlers.router.export_records", fake_export)

    # NEW_RECORD
    await handle_text(update, context)
    assert called.get('new')

    # STATISTICS
    update = FakeUpdate(STATISTICS_BUTTON)
    await handle_text(update, context)
    assert called.get('stats')

    # HISTORY
    update = FakeUpdate(HISTORY_BUTTON)
    await handle_text(update, context)
    assert called.get('history')

    # SETTINGS
    update = FakeUpdate(SETTINGS_BUTTON)
    await handle_text(update, context)
    assert called.get('settings')

    # EXPORT
    update = FakeUpdate(EXPORT_BUTTON)
    await handle_text(update, context)
    assert called.get('export')


@pytest.mark.asyncio
async def test_state_fallback_uses_persisted_state(monkeypatch):
    update = FakeUpdate("8")
    context = FakeContext()

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

    # Simulate persisted state being read when in-memory is absent
    monkeypatch.setattr("handlers.router.get_user_state", lambda u, c: "today_count")

    called = []

    async def fake_save_today(update, context):
        called.append(True)

    monkeypatch.setattr("handlers.router.save_today_record", fake_save_today)

    await handle_text(update, context)

    assert called == [True]


@pytest.mark.asyncio
async def test_settings_state_actions(monkeypatch):
    update = FakeUpdate(DARK_THEME_BUTTON)
    context = FakeContext()
    context.user_data['awaiting'] = 'settings'

    class FakeTracker:
        @staticmethod
        def user_exists(user_id):
            return True
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    called = {}

    async def fake_change_theme(update, context, theme):
        called['theme'] = theme

    async def fake_request_delete(update, context):
        called['delete'] = True

    monkeypatch.setattr("handlers.router.change_graph_theme", fake_change_theme)
    monkeypatch.setattr("handlers.router.request_delete_data", fake_request_delete)

    # DARK_THEME_BUTTON
    await handle_text(update, context)
    assert called.get('theme') == DARK_THEME

    # LIGHT_THEME_BUTTON
    update = FakeUpdate(LIGHT_THEME_BUTTON)
    await handle_text(update, context)
    assert called.get('theme') == LIGHT_THEME

    # DELETE_DATA_BUTTON
    update = FakeUpdate(DELETE_DATA_BUTTON)
    await handle_text(update, context)
    assert called.get('delete')


@pytest.mark.asyncio
async def test_confirm_delete_buttons_call_confirm(monkeypatch):
    update = FakeUpdate(CONFIRM_YES_BUTTON)
    context = FakeContext()
    context.user_data['awaiting'] = 'confirm_delete'

    class FakeTracker:
        @staticmethod
        def user_exists(user_id):
            return True
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    calls = []

    async def fake_confirm(update, context, val):
        calls.append(val)

    monkeypatch.setattr("handlers.router.confirm_delete_data", fake_confirm)

    await handle_text(update, context)
    assert calls == [True]

    update = FakeUpdate(CONFIRM_NO_BUTTON)
    context.user_data['awaiting'] = 'confirm_delete'
    await handle_text(update, context)
    assert calls == [True, False]


@pytest.mark.asyncio
async def test_unknown_message_shows_main_keyboard(monkeypatch):
    update = FakeUpdate("I don't know this")
    context = FakeContext()

    class FakeTracker:
        @staticmethod
        def user_exists(user_id):
            return True
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    # ensure in-memory key exists so get_user_state() is not invoked
    context.user_data['awaiting'] = None

    await handle_text(update, context)

    assert "I didn't understand" in update.message.replies[-1]