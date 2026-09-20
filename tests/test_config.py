import importlib

import pytest

import config
from config import get_env_value


def test_get_env_value_strips_whitespace(monkeypatch):
    monkeypatch.setenv("TEST_TOKEN", "  abc123\n")

    assert get_env_value("TEST_TOKEN") == "abc123"


def test_get_env_value_raises_for_missing_required_value(monkeypatch):
    monkeypatch.delenv("TEST_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TEST_TOKEN"):
        get_env_value("TEST_TOKEN", required=True)


def test_database_path_uses_env_value(monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", "data/custom.db")

    importlib.reload(config)

    assert config.DATABASE_PATH == "data/custom.db"

    monkeypatch.delenv("DATABASE_PATH", raising=False)
    importlib.reload(config)
