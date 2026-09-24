import logging
import os
from pathlib import Path
from typing import ClassVar

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import register_handlers
from handlers.router import handle_text
from handlers.utils import validate_allowed_user_ids


class ColoredFormatter(logging.Formatter):

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\033[90m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }

    RESET: ClassVar[str] = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def configure_logging(log_dir: Path | str = "logs"):
    """Configure logging. Call from main() to avoid import-side effects."""
    log_path = Path(log_dir)
    # In tests we may want to avoid creating files or changing global
    # logging state. Honor `NO_FILE_LOGS` environment variable to skip
    # creating file handlers, and avoid forcing global handler replacement
    # unless explicitly requested.
    no_file = os.getenv("NO_FILE_LOGS") is not None

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    handlers = [stream_handler]

    if not no_file:
        log_path.mkdir(exist_ok=True)
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            log_path / "tracker.log",
            encoding="utf-8",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        handlers.append(file_handler)

    # Do not use force=True by default to avoid stomping on other tests' logging.
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logging.getLogger("tracker.bot")


logger = logging.getLogger("tracker.bot")


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context
):
    logger.error(
        "Exception while handling update",

        exc_info=context.error,
    )

    if update and getattr(
        update,
        "effective_message",
        None,
    ):
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again."
            )
        except Exception:
            logger.exception(
                "Failed to send error message"
            )


# =========================================================
# MAIN
# =========================================================

def main():

    # configure logging now (no import-time side effects)
    global logger
    logger = configure_logging()

    token = TELEGRAM_BOT_TOKEN

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    validate_allowed_user_ids()

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    # Initialize application-scoped services
    from services import tracker_service
    tracker_service.setup_application(app)

    from services.cleanup_service import schedule_cleanup_jobs
    schedule_cleanup_jobs(app)

    register_handlers(app)

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "Daily Tracker bot is running..."
    )

    app.run_polling(allowed_updates=[Update.MESSAGE])


if __name__ == "__main__":
    main()