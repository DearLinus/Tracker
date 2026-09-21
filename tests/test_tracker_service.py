from types import SimpleNamespace

import pytest

from logic import TrackerLogic
from services.tracker_service import get_tracker_from_context, setup_application


class FakeApp:
    def __init__(self, bot_data=None):
        if bot_data is not None:
            self.bot_data = bot_data


def test_setup_application_stores_tracker_on_bot_data(tmp_path):
    app = FakeApp()

    tracker = setup_application(app, db_path=str(tmp_path / "test.db"))

    assert isinstance(tracker, TrackerLogic)
    assert app.bot_data["tracker"] is tracker


def test_setup_application_reuses_existing_bot_data(tmp_path):
    app = FakeApp(bot_data={"other": 1})

    tracker = setup_application(app, db_path=str(tmp_path / "test.db"))

    assert app.bot_data["other"] == 1
    assert app.bot_data["tracker"] is tracker


def test_get_tracker_from_context_reads_bot_data():
    tracker = object()
    context = SimpleNamespace(bot_data={"tracker": tracker})

    assert get_tracker_from_context(context) is tracker


def test_get_tracker_from_context_falls_back_to_application():
    tracker = object()
    context = SimpleNamespace(
        bot_data={},
        application=SimpleNamespace(bot_data={"tracker": tracker}),
    )

    assert get_tracker_from_context(context) is tracker


def test_get_tracker_from_context_requires_context():
    with pytest.raises(RuntimeError, match="No context provided"):
        get_tracker_from_context(None)


def test_get_tracker_from_context_requires_setup():
    context = SimpleNamespace(bot_data={})

    with pytest.raises(RuntimeError, match="setup_application"):
        get_tracker_from_context(context)
