import os
from types import SimpleNamespace

import pytest

from logic import TrackerLogic
from services.tracker_service import get_tracker_from_context, setup_application


class FakeApp:
    def __init__(self, bot_data=None):
        if bot_data is not None:
            self.bot_data = bot_data


def test_setup_application_attaches_tracker():
    app = FakeApp()
    tracker = setup_application(app, db_path=":memory:")

    assert tracker is not None
    assert getattr(app, "bot_data", None) is not None
    assert app.bot_data["tracker"] is tracker


def test_setup_application_stores_tracker_on_bot_data(tmp_path):
    app = FakeApp()

    tracker = setup_application(app, db_path=str(tmp_path / "test.db"))

    assert isinstance(tracker, TrackerLogic)
    assert app.bot_data["tracker"] is tracker


def test_setup_application_testing_uses_shared_temp_file_db(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    app1 = FakeApp()
    app2 = FakeApp()

    tracker1 = setup_application(app1)
    tracker2 = setup_application(app2)

    assert tracker1.database.db_path != ":memory:"
    assert os.path.exists(tracker1.database.db_path)
    assert tracker1.database.db_path == tracker2.database.db_path

    tracker1.create_user(42, "alice")
    assert tracker2.user_exists(42)


def test_setup_application_reuses_existing_bot_data(tmp_path):
    app = FakeApp(bot_data={"other": 1})

    tracker = setup_application(app, db_path=str(tmp_path / "test.db"))

    assert app.bot_data["other"] == 1
    assert app.bot_data["tracker"] is tracker


def test_get_tracker_from_context_prefers_context_bot_data():
    class Ctx:
        def __init__(self):
            self.bot_data = {"tracker": "A"}

    ctx = Ctx()
    assert get_tracker_from_context(ctx) == "A"


def test_get_tracker_from_context_looks_in_application():
    class Application:
        def __init__(self):
            self.bot_data = {"tracker": "B"}

    class Ctx:
        def __init__(self):
            self.bot_data = None
            self.application = Application()

    ctx = Ctx()
    assert get_tracker_from_context(ctx) == "B"


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


def test_setup_application_raises_when_bot_data_is_unusable():
    class BrokenApp:
        def __setattr__(self, name, value):
            raise TypeError("no bot_data for you")

    with pytest.raises(RuntimeError, match="allow setting .bot_data"):
        setup_application(BrokenApp())


def test_tracker_service_raises_for_non_mapping_bot_data():
    with pytest.raises(RuntimeError, match="TrackerLogic instance not found"):
        get_tracker_from_context(SimpleNamespace(bot_data=[]))


def test_get_tracker_from_context_raises_on_missing():
    class Ctx:
        def __init__(self):
            self.bot_data = None
            self.application = None

    ctx = Ctx()
    with pytest.raises(RuntimeError):
        get_tracker_from_context(ctx)
