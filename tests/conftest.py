import logging
import os

from cryptography.fernet import Fernet
import pytest

# Set env before importing config so required startup variables are present in tests.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_PATH", "test_tracker.db")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

import config

logger = logging.getLogger(__name__)


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
    # Override both the process env and the imported config module so any
    # import-time configuration already loaded in-process sees the same value.
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config, "DATABASE_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "ENCRYPTION_KEY", os.environ["ENCRYPTION_KEY"], raising=False)
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
    def set_setting(user_id, key, value):
        return None

    @staticmethod
    def delete_record(user_id, record_date):
        return None

    @staticmethod
    def delete_user(user_id):
        return None

    @staticmethod
    def get_statistics(user_id):
        return {
            "days": 0,
            "total": 0,
            "average": 0,
            "highest": 0,
        }

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
        
        autospec = overrides.pop("autospec", False)

        for method_name, method_impl in overrides.items():
            setattr(ConfiguredFakeTracker, method_name, staticmethod(method_impl))

        instance = ConfiguredFakeTracker()

        if autospec:
            # Create an autospeced object matching TrackerLogic to catch API drift
            from unittest.mock import create_autospec

            from logic import TrackerLogic

            spec = create_autospec(TrackerLogic, instance=True)
            # copy over any overrides from the configured instance into the spec
            for name in dir(instance):
                if not name.startswith("_") and hasattr(spec, name):
                    try:
                        setattr(spec, name, getattr(instance, name))
                    except AttributeError:
                        logger.debug("Skipping autospec attribute %s", name, exc_info=True)

            return spec

        return instance
    
    return _create
