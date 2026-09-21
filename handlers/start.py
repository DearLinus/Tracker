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
from handlers.utils import is_user_allowed
import asyncio
import functools


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)
    user = update.effective_user

    # Access control: prevent unauthorized users from creating accounts
    from handlers.constants import ACCESS_DENIED_MESSAGE, PRIVATE_CHAT_REQUIRED_MESSAGE
    from handlers.utils import is_private_chat

    # Private chat enforcement: reject group messages early
    if not is_private_chat(update):
        await update.message.reply_text(
            PRIVATE_CHAT_REQUIRED_MESSAGE,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    if not is_user_allowed(user.id):
        await update.message.reply_text(
            ACCESS_DENIED_MESSAGE,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    await asyncio.to_thread(functools.partial(get_tracker(context).create_user, user.id, user.username))

    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID,
    )

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=MAIN_KEYBOARD,
    )