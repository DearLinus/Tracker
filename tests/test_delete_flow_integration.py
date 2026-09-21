import pytest
from types import SimpleNamespace
from services.tracker_service import setup_application
from handlers import start as start_handler
from handlers.settings import request_delete_data, confirm_delete_data
import sqlite3


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, user_id):
        self.effective_user = SimpleNamespace(id=user_id, username="u")
        self.message = FakeMessage()


class FakeContext:
    def __init__(self, app):
        # context.bot_data should mirror application bot_data
        self.bot_data = app.bot_data
        self.application = app
        self.user_data = {}


@pytest.mark.asyncio
async def test_delete_flow_integration(tmp_path):
    db_path = str(tmp_path / "test_tracker.db")

    app = SimpleNamespace()
    tracker = setup_application(app, db_path=db_path)

    user_id = 42

    # create user via tracker API
    tracker.create_user(user_id, "u")
    assert tracker.user_exists(user_id)

    update = FakeUpdate(user_id)
    context = FakeContext(app)

    # Request delete -> awaiting state set
    await request_delete_data(update, context)
    assert context.user_data.get("awaiting") == "confirm_delete"

    # Confirm delete -> should delete and clear state
    await confirm_delete_data(update, context, True)
    assert "Your data has been deleted" in update.message.replies[-1]
    assert not tracker.user_exists(user_id)
    assert context.user_data.get("awaiting") is None

    # Confirm again -> no data found
    update2 = FakeUpdate(user_id)
    context2 = FakeContext(app)
    await confirm_delete_data(update2, context2, True)
    assert "No data found" in update2.message.replies[-1]

    # After deletion, calling start should recreate the user
    update3 = FakeUpdate(user_id)
    context3 = FakeContext(app)
    await start_handler.start(update3, context3)
    assert tracker.user_exists(user_id)
