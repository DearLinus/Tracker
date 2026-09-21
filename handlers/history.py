from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes

import asyncio
import functools

from keyboards import HISTORY_KEYBOARD
from services.tracker_service import get_tracker_from_context as get_tracker


from handlers.utils import (
    get_user_id,
    reset_state,
    get_user_today,
    clear_user_state,
)


async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)
    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    user_id = get_user_id(update)

    # fetch records in a thread to avoid blocking the event loop
    records = await asyncio.to_thread(functools.partial(get_tracker(context).get_records, user_id))

    lines = [
        "📜 Last 7 Days\n"
    ]

    today = get_user_today(update, context)

    has_record = False

    for i in range(7):
        current_date = today - timedelta(days=i)

        if current_date in records:
            has_record = True
            count = records[current_date]
        else:
            count = "No record"

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