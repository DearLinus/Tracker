import pytest

import bot


class FakeBuilder:
    def __init__(self, app):
        self.app = app
        self._token = None

    def token(self, value):
        self._token = value
        return self

    def build(self):
        self.app.token = self._token
        return self.app


class FakeApp:
    def __init__(self):
        self.token = None
        self.handlers = []
        self.error_handlers = []
        self.polling_called = False

    def add_handler(self, handler):
        self.handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)

    def run_polling(self):
        self.polling_called = True


def test_main_raises_when_token_missing(monkeypatch):
    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", None)

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        bot.main()


def test_main_builds_application_with_token(monkeypatch):
    app = FakeApp()
    builder = FakeBuilder(app)

    monkeypatch.setattr(bot, "TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setattr(bot, "Application", type("AppFactory", (), {"builder": staticmethod(lambda: builder)}))
    monkeypatch.setattr(bot, "register_handlers", lambda app_obj: app_obj.handlers.append("registered"))
    monkeypatch.setattr(bot, "MessageHandler", lambda *args, **kwargs: {"handler": args, "kwargs": kwargs})

    bot.main()

    assert app.token == "token-123"
    assert app.polling_called is True
    assert "registered" in app.handlers
