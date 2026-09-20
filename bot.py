import logging
from pathlib import Path

from handlers import register_handlers
from handlers.router import handle_text
from config import TELEGRAM_BOT_TOKEN
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):

    COLORS = {
        logging.DEBUG: "\033[90m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }

    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
)

file_handler = logging.FileHandler(LOG_DIR / "tracker.log", encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler],
    force=True,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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

    token = TELEGRAM_BOT_TOKEN

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

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

    logging.info(
        "Daily Tracker bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()