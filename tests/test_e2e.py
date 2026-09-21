import os
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.error import TelegramError

from services.tracker_service import setup_application, get_tracker_from_context
from handlers.records import save_today_record, start_today_record
from handlers.start import start


class FakeUser:
    def __init__(self, user_id=123):
        self.id = user_id
        self.username = "e2e_user"


class FakeMessage:
    def __init__(self, text=None):
        self.text = text
        self.replies = []
        self.stickers_sent = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)

    async def reply_sticker(self, sticker_id):
        self.stickers_sent.append(sticker_id)


class FakeUpdate:
    def __init__(self, user_id=123, text=None):
        self.effective_user = FakeUser(user_id)
        self.message = FakeMessage(text)


def test_application_botdata_context_tracker_persistence(tmp_path):
    """Verify tracker persists across Application restarts (basic E2E)."""
    db_path = str(tmp_path / "e2e.db")

    # Create a real Application and attach a TrackerLogic instance
    app = Application.builder().token("TEST").build()
    tracker = setup_application(app, db_path=db_path)

    # Access via a context-like object
    context = SimpleNamespace(bot_data=app.bot_data, application=app)

    svc = get_tracker_from_context(context)
    assert svc is tracker

    # Create a user and verify it's persisted
    svc.create_user(12345, username="e2e_user")
    assert svc.user_exists(12345)

    # Simulate application restart by creating a new Application and setup
    app2 = Application.builder().token("TEST").build()
    tracker2 = setup_application(app2, db_path=db_path)

    context2 = SimpleNamespace(bot_data=app2.bot_data, application=app2)
    svc2 = get_tracker_from_context(context2)

    # The new tracker backed by the same DB must observe the user created earlier
    assert svc2.user_exists(12345)


@pytest.mark.asyncio
async def test_e2e_start_handler_flow(tmp_path):
    """E2E test: /start handler with real Application, context, and tracker.
    
    Flow: Application → Update/handler → context → TrackerLogic → SQLite
    Verify: User created, welcome message sent, state reset.
    """
    db_path = str(tmp_path / "e2e_start.db")
    
    # Create real Application and tracker
    app = Application.builder().token("TEST").build()
    setup_application(app, db_path=db_path)
    
    # Create fake Update and mock context
    update = FakeUpdate(user_id=999)
    context = MagicMock()
    context.user_data = {}
    context.bot_data = app.bot_data
    
    # Call real /start handler
    await start(update, context)
    
    # Verify user was created in DB
    tracker = app.bot_data["tracker"]
    assert tracker.user_exists(999)
    
    # Verify welcome message was sent
    assert len(update.message.replies) == 1
    assert "Welcome to Daily Tracker" in update.message.replies[0]
    
    # Verify state was cleared
    assert "awaiting" not in context.user_data


@pytest.mark.asyncio
async def test_e2e_record_save_with_state_persistence(tmp_path):
    """E2E test: Record saving with state persistence across restart.
    
    Flow:
    1. User starts /start (creates user)
    2. User initiates record (sets awaiting=today_count in DB)
    3. App restarts → state lost from memory
    4. User sends record → state retrieved from DB
    5. Record saved, state cleared from DB
    """
    db_path = str(tmp_path / "e2e_record.db")
    
    # === Phase 1: Initial /start ===
    app1 = Application.builder().token("TEST").build()
    setup_application(app1, db_path=db_path)
    
    update1 = FakeUpdate(user_id=777)
    context1 = MagicMock()
    context1.user_data = {}
    context1.bot_data = app1.bot_data
    
    await start(update1, context1)
    assert app1.bot_data["tracker"].user_exists(777)
    
    # === Phase 2: Start today record (sets state in DB) ===
    update2 = FakeUpdate(user_id=777)
    context2 = MagicMock()
    context2.user_data = {}
    context2.bot_data = app1.bot_data
    
    await start_today_record(update2, context2)
    
    # Verify state was persisted to DB
    tracker1 = app1.bot_data["tracker"]
    persisted_state = tracker1.get_user_state(777, "awaiting")
    assert persisted_state == "today_count"
    
    # === Phase 3: Simulate app restart (new Application instance) ===
    app2 = Application.builder().token("TEST").build()
    setup_application(app2, db_path=db_path)
    tracker2 = app2.bot_data["tracker"]
    
    # Verify state is NOT in memory but IS in DB
    assert tracker2.user_exists(777)
    persisted_state = tracker2.get_user_state(777, "awaiting")
    assert persisted_state == "today_count", "State should be restored from DB"
    
    # === Phase 4: Save record (with fresh context after restart) ===
    update3 = FakeUpdate(user_id=777, text="5")
    context3 = MagicMock()
    context3.user_data = {}  # Empty: state lost from memory
    context3.bot_data = app2.bot_data
    
    await save_today_record(update3, context3)
    
    # Verify record was saved
    records = tracker2.get_records(777)
    today = datetime.now().date()
    assert today in records
    assert records[today] == 5
    
    # Verify state was cleared from DB
    cleared_state = tracker2.get_user_state(777, "awaiting")
    assert cleared_state is None, "State should be cleared after save"


@pytest.mark.asyncio
async def test_e2e_sticker_failure_doesnt_break_flow(tmp_path, monkeypatch):
    """E2E test: Sticker send failure should not break record save flow.
    
    Verify: TelegramError during sticker send is logged but does not prevent
    record save or state cleanup.
    """
    db_path = str(tmp_path / "e2e_sticker.db")
    
    app = Application.builder().token("TEST").build()
    setup_application(app, db_path=db_path)
    
    # Setup: create user and set state
    update_init = FakeUpdate(user_id=555)
    context_init = MagicMock()
    context_init.user_data = {}
    context_init.bot_data = app.bot_data
    
    await start(update_init, context_init)
    
    # === Now test record save with sticker failure ===
    update = FakeUpdate(user_id=555, text="3")
    context = MagicMock()
    context.user_data = {}
    context.bot_data = app.bot_data
    
    # Mock sticker send to fail with TelegramError
    original_send_sticker = update.message.reply_sticker
    async def failing_sticker(*args, **kwargs):
        raise TelegramError("Sticker send failed")
    update.message.reply_sticker = failing_sticker
    
    # Should not raise; handler should complete despite sticker failure
    await save_today_record(update, context)
    
    # Verify record WAS saved despite sticker failure
    tracker = app.bot_data["tracker"]
    records = tracker.get_records(555)
    today = datetime.now().date()
    assert today in records, "Record should be saved despite sticker failure"
    assert records[today] == 3
    
    # Verify state WAS cleared despite sticker failure
    cleared_state = tracker.get_user_state(555, "awaiting")
    assert cleared_state is None, "State should be cleared despite sticker failure"
    
    # Verify reply was still sent
    assert len(update.message.replies) > 0, "Reply should still be sent"
