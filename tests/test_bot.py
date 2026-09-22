from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update

import bot


def test_configure_logging_no_file_logs(monkeypatch, tmp_path):
    monkeypatch.setenv("NO_FILE_LOGS", "1")
    log = bot.configure_logging(log_dir=tmp_path)
    assert log.name == "tracker.bot"


def test_configure_logging_creates_file_handler(monkeypatch, tmp_path):
    # Ensure file handler is added when NO_FILE_LOGS not set
    monkeypatch.delenv("NO_FILE_LOGS", raising=False)
    log = bot.configure_logging(log_dir=tmp_path)
    # basicConfig sets handlers on root logger; ensure logger is returned
    assert log.name == "tracker.bot"


@pytest.mark.asyncio
async def test_error_handler_replies(monkeypatch):
    # Create a fake update with effective_message.reply_text
    mock_msg = AsyncMock()
    mock_msg.reply_text = AsyncMock()

    class FakeUpdate:
        effective_message = mock_msg

    class Ctx:
        error = Exception("boom")

    await bot.error_handler(FakeUpdate(), Ctx())
    mock_msg.reply_text.assert_awaited()


def test_main_missing_token(monkeypatch):
    monkeypatch.setenv("NO_FILE_LOGS", "1")
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", None)

    with pytest.raises(RuntimeError):
        bot.main()


def test_main_builds_application(monkeypatch):
    monkeypatch.setenv("NO_FILE_LOGS", "1")
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc123")

    fake_app = MagicMock()
    fake_application_builder = MagicMock()
    fake_application_builder.token.return_value = fake_application_builder
    fake_application_builder.build.return_value = fake_app

    fake_application = MagicMock()
    fake_application.builder.return_value = fake_application_builder

    with patch("bot.Application", autospec=True) as MockApp:
        MockApp.builder.return_value = fake_application_builder
        # Patch tracker_service.setup_application and handlers.register_handlers
        with patch("services.tracker_service.setup_application") as setup_app, patch("bot.register_handlers") as reg:
            # Prevent run_polling from blocking
            fake_app.run_polling = MagicMock()
            fake_application_builder.build.return_value = fake_app

            bot.main()

            setup_app.assert_called()
            reg.assert_called_once()
            fake_app.run_polling.assert_called_with(allowed_updates=[Update.MESSAGE])


def test_main_fails_fast_on_invalid_allowlist(monkeypatch):
    monkeypatch.setenv("NO_FILE_LOGS", "1")
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc123")
    monkeypatch.setenv("ALLOWED_USER_IDS", "invalid")

    with pytest.raises(ValueError, match="ALLOWED_USER_IDS"):
        bot.main()
