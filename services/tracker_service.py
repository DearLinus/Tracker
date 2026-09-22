import os
import tempfile

from logic import TrackerLogic

_TESTING_DB_PATH = None


def setup_application(app, db_path=None):
    """Create a TrackerLogic instance and attach it to the Application.

    The tracker is stored on ``app.bot_data["tracker"]`` so each Telegram
    Application owns its own service instance instead of sharing a process-wide
    singleton.
    """
    global _TESTING_DB_PATH

    # During tests, prefer a temporary SQLite file instead of :memory:.
    # SQLite in-memory databases are isolated per connection, which breaks
    # tests that create multiple tracker instances or connections against the
    # same logical database.
    if db_path is None and os.getenv("TESTING"):
        if _TESTING_DB_PATH is None:
            fd, _TESTING_DB_PATH = tempfile.mkstemp(prefix="tracker_test_", suffix=".db")
            os.close(fd)
        db_path = _TESTING_DB_PATH

    tracker_instance = TrackerLogic(db_path)

    if getattr(app, "bot_data", None) is None:
        try:
            app.bot_data = {}
        except Exception as exc:
            raise RuntimeError(
                "Application object must allow setting .bot_data attribute"
            ) from exc

    app.bot_data["tracker"] = tracker_instance
    return tracker_instance


def get_tracker_from_context(context):
    """Return the TrackerLogic instance stored on the Telegram context.

    Looks up ``context.bot_data["tracker"]``, then
    ``context.application.bot_data["tracker"]``. Raises RuntimeError if the
    application was not initialized with ``setup_application()``.
    """
    if context is None:
        raise RuntimeError("No context provided to get_tracker_from_context")

    tracker = _tracker_from_bot_data(getattr(context, "bot_data", None))
    if tracker is None:
        application = getattr(context, "application", None)
        tracker = _tracker_from_bot_data(
            getattr(application, "bot_data", None) if application is not None else None
        )

    if tracker is None:
        raise RuntimeError(
            "TrackerLogic instance not found in application. "
            "Call services.tracker_service.setup_application(app) in bot.main()."
        )

    return tracker


def _tracker_from_bot_data(bot_data):
    if bot_data is None:
        return None

    try:
        return bot_data.get("tracker")
    except (AttributeError, TypeError):
        return None
