from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD
from services.tracker_service import tracker
from handlers.utils import get_user_id, reset_state

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)

    user_id = get_user_id(update)
    records = tracker.get_records(user_id)

    if not records:
        await update.message.reply_text(
            "📜 History\n\n"
            "You don't have any records yet.",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    lines = ["📜 History\n"]

    for record_date, count in sorted(records.items(), reverse=True):
        lines.append(
            f"{record_date.strftime('%Y-%m-%d')}  →  {count}"
        )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=MAIN_KEYBOARD,
    )