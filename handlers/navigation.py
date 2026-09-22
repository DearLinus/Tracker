import asyncio
import functools

from telegram import Update
from telegram.ext import ContextTypes

from handlers.utils import clear_user_state, reset_state
from keyboards import MAIN_KEYBOARD


async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    await update.message.reply_text(
        "🏠 Main Menu",
        reply_markup=MAIN_KEYBOARD,
    )