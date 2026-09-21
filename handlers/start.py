from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from config import WELCOME_STICKER_ID
from handlers.constants import WELCOME_MESSAGE

from services.tracker_service import get_tracker_from_context as get_tracker

from handlers.utils import (
    reset_state,
    send_sticker_if_available,
    clear_user_state,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)
    clear_user_state(update, context)

    user = update.effective_user

    get_tracker(context).create_user(
        user.id,
        user.username,
    )

    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID,
    )

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=MAIN_KEYBOARD,
    )