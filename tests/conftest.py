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


class MinimalFakeTracker:
    """Minimal tracker that returns None/empty for all methods.
    
    Tests can subclass this and override only the methods they need.
    This reduces boilerplate when creating test-specific FakeTrackers.
    """
    @staticmethod
    def get_record(user_id, record_date):
        return None

    @staticmethod
    def get_records(user_id):
        return {}

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

    @staticmethod
    def save_record(user_id, record_date, count):
        return None

    @staticmethod
    def save_setting(user_id, key, value):
        return None

    @staticmethod
    def user_exists(user_id):
        return True

    @staticmethod
    def create_user(user_id, username=None):
        return None


@pytest.fixture
def tracker_factory():
    """Factory to create configured FakeTracker instances for tests.
    
    Usage:
        # Create minimal tracker
        tracker = tracker_factory()
        
        # Or create with specific behavior
        tracker = tracker_factory(get_record=lambda *a: 5)
    """
    def _create(**overrides):
        class ConfiguredFakeTracker(MinimalFakeTracker):
            pass
        
        for method_name, method_impl in overrides.items():
            setattr(ConfiguredFakeTracker, method_name, staticmethod(method_impl))
        
        return ConfiguredFakeTracker()
    
    return _create
