from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from config import WELCOME_STICKER_ID

from logic import TrackerLogic


logic = TrackerLogic()


async def send_sticker_if_available(
    update: Update,
    sticker_id: str | None,
):
    if not sticker_id:
        return

    try:
        await update.message.reply_sticker(
            sticker_id
        )

    except Exception:
        pass


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.pop(
        "awaiting",
        None
    )

    user = update.effective_user


    logic.create_user(
        user.id,
        user.username
    )


    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID
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