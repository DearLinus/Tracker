from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from handlers.utils import reset_state

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)

    await update.message.reply_text(
        "🏠 Main Menu",
        reply_markup=MAIN_KEYBOARD,
    )