from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import HISTORY_KEYBOARD
from services.tracker_service import tracker
from handlers.utils import get_user_id, reset_state


async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    user_id = get_user_id(update)

    records = tracker.get_records(user_id)

    lines = [
        "📜 Last 7 Days\n"
    ]

    today = datetime.now(
        ZoneInfo("Europe/London")
    ).date()

    has_record = False

    for i in range(7):
        current_date = today - timedelta(days=i)

        count = records.get(
            current_date,
            0
        )

        if current_date in records:
            has_record = True

        lines.append(
            f"{current_date.strftime('%Y-%m-%d')} → {count}"
        )

    if not has_record:
        lines = [
            "📜 Last 7 Days\n",
            "You don't have any records in the last 7 days."
        ]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=HISTORY_KEYBOARD,
    )