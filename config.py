import os

from dotenv import load_dotenv

load_dotenv()


def get_env_value(name: str, *, required: bool = False, default: str | None = None):
    """Return a trimmed environment value.

    When `required=True`, raise immediately instead of silently falling back.
    This keeps startup failures explicit and prevents the bot from running
    without required secrets such as the Telegram token.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        if required:
            raise ValueError(f"Missing required environment variable: {name}")
        return default

    return value.strip()


DATABASE_PATH = get_env_value("DATABASE_PATH", default="tracker.db")
# Required at startup: running the bot without a token should fail immediately.
TELEGRAM_BOT_TOKEN = get_env_value("TELEGRAM_BOT_TOKEN", required=True)
WELCOME_STICKER_ID = get_env_value("WELCOME_STICKER_ID")
SUCCESS_STICKER_ID = get_env_value("SUCCESS_STICKER_ID")
ERROR_STICKER_ID = get_env_value("ERROR_STICKER_ID")