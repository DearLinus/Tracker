import pytest


@pytest.fixture
def mock_sticker(monkeypatch):
    async def fake_send_sticker(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "handlers.start.send_sticker_if_available",
        fake_send_sticker,
        raising=False
    )

    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker,
        raising=False
    )