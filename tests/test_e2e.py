import os
from types import SimpleNamespace

from telegram.ext import Application

from services.tracker_service import setup_application, get_tracker_from_context


def test_application_botdata_context_tracker_persistence(tmp_path):
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
