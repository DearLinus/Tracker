from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from services.tracker_service import tracker
from handlers.utils import get_user_id, reset_state


async def show_statistics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)

    user_id = get_user_id(update)

    records = tracker.get_records(user_id)

    if not records:
        await update.message.reply_text(
            "📊 Statistics\n\n"
            "You don't have any records yet.",
            reply_markup=MAIN_KEYBOARD,
        )
        return


    values = records.values()

    total = sum(values)

    average = total / len(records)

    highest = max(values)


    await update.message.reply_text(
        "📊 Statistics\n\n"
        f"📅 Recorded days: {len(records)}\n"
        f"🔢 Total: {total}\n"
        f"📈 Average: {average:.2f}\n"
        f"🏆 Highest: {highest}",
        reply_markup=MAIN_KEYBOARD,
    )