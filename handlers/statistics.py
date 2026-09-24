import asyncio
import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from database import RecordDecryptionError
from handlers.utils import clear_user_state, get_user_id, reset_state
from keyboards import MAIN_KEYBOARD
from logic import RECORD_DECRYPTION_MESSAGE
from services.tracker_service import get_tracker_from_context as get_tracker

logger = logging.getLogger(__name__)


async def show_statistics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)
    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    user_id = get_user_id(update)

    try:
        # fetch statistics in a thread to avoid blocking the event loop
        stats = await asyncio.to_thread(functools.partial(get_tracker(context).get_statistics, user_id))
    except RecordDecryptionError:
        logger.exception("Decryption failed while fetching statistics")
        await update.message.reply_text(
            RECORD_DECRYPTION_MESSAGE,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    if stats["days"] == 0:
        await update.message.reply_text(
            "📊 Statistics\n\n"
            "You don't have any records yet.",
            reply_markup=MAIN_KEYBOARD,
        )
        return


    await update.message.reply_text(
        "📊 Statistics\n\n"
        f"📅 Recorded days: {stats['days']}\n"
        f"🔢 Total: {stats['total']}\n"
        f"📈 Average: {stats['average']:.2f}\n"
        f"🏆 Highest: {stats['highest']}",
        reply_markup=MAIN_KEYBOARD,
    )