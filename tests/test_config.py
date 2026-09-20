import pytest

from config import get_env_value


def test_get_env_value_strips_whitespace(monkeypatch):
    monkeypatch.setenv("TEST_TOKEN", "  abc123\n")

    assert get_env_value("TEST_TOKEN") == "abc123"


def test_get_env_value_raises_for_missing_required_value(monkeypatch):
    monkeypatch.delenv("TEST_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TEST_TOKEN"):
        get_env_value("TEST_TOKEN", required=True)
