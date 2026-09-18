from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from config import WELCOME_STICKER_ID

from services.tracker_service import tracker
from handlers.utils import (
    reset_state,
    send_sticker_if_available,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    user = update.effective_user

    tracker.create_user(
        user.id,
        user.username,
    )

    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID,
    )

    await update.message.reply_text(
        "👋 Welcome to Daily Tracker!\n\n"
        "Daily Tracker is a personal tracker for "
        "recording and viewing the trend of masturbation "
        "frequency over time.\n\n"
        "You can record your daily count, review your "
        "history and statistics, and visualize your "
        "progress with a graph.\n\n"
        "Choose an option below:",
        reply_markup=MAIN_KEYBOARD,
    )