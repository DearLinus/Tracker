from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from services.tracker_service import get_tracker_from_context as get_tracker

from handlers.utils import get_user_id, reset_state, clear_user_state


async def show_statistics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)
    clear_user_state(update, context)

    user_id = get_user_id(update)

    stats = get_tracker(context).get_statistics(user_id)

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