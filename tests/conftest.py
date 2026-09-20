import os

import pytest


# Provide a sensible default so importing modules that read config at
# import-time don't fail in a clean CI environment.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
# Keep a default but tests will normally override this with a temp file.
os.environ.setdefault("DATABASE_PATH", "test_tracker.db")


@pytest.fixture
def mock_sticker(monkeypatch):
    async def fake_send_sticker(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "handlers.start.send_sticker_if_available",
        fake_send_sticker,
        raising=False,
    )

    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker,
        raising=False,
    )


@pytest.fixture(autouse=True)
def use_temp_database(tmp_path, monkeypatch):
    """
    Ensure each test runs with an isolated temporary database file.

    This avoids shared state between tests and gives a clean CI run.
    The fixture is autouse so no test changes are required.
    """
    db_path = str(tmp_path / "test_tracker.db")
    # Override the env var for the duration of the test run
    monkeypatch.setenv("DATABASE_PATH", db_path)
    return db_path
