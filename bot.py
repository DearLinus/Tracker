import os
import logging

from handlers import register_handlers
from handlers.router import handle_text
from config import TELEGRAM_BOT_TOKEN
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


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