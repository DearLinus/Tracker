from datetime import datetime


from telegram import Update
from telegram.ext import ContextTypes
import logging

from keyboards import MAIN_KEYBOARD, BACK_KEYBOARD
from config import SUCCESS_STICKER_ID, ERROR_STICKER_ID
from services.tracker_service import tracker
from handlers.utils import (
    get_user_id,
    reset_state,
    send_sticker_if_available,
    get_user_today,
)

logger = logging.getLogger(__name__)
# =========================================================
# HELPERS
# =========================================================
# =========================================================
# TODAY RECORD
# =========================================================

async def start_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    context.user_data["awaiting"] = "today_count"

    today_date = get_user_today(update)
    user_id = get_user_id(update)

    existing = tracker.get_record(
        user_id,
        today_date
    )

    if existing is None:
        message = (
            "📝 Today Record\n\n"
            f"Today is {today_date.strftime('%B %d, %Y')}.\n\n"
            "How many times did you do it today?\n\n"
            "Send the number only.\n"
            "Example: 8"
        )
    else:
        message = (
            "📝 Today Record\n\n"
            f"Today's current record is {existing}.\n\n"
            "Send the new count to update it.\n\n"
            "Example: 8"
        )

    await update.message.reply_text(
        message,
        reply_markup=BACK_KEYBOARD,
    )


async def save_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    user_id = get_user_id(update)

    try:
        count = int(text)

    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a whole number.\n\n"
            "Example: 8",
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            "⚠️ The count cannot be negative.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    today_date = get_user_today(update)

    try:
        # save_record is an upsert: it creates the record
        # or overwrites the existing one for that date.
        tracker.save_record(
            user_id,
            today_date,
            count
        )

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {today_date.strftime('%B %d, %Y')}\n"
            f"Count: {count}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except Exception:
        logger.exception("Failed to save today's record")

        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID,
        )

        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't save today's record.\n\n"
            "Please try again later.",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# NEW RECORD
# =========================================================

async def start_new_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    context.user_data["awaiting"] = "new_record"

    await update.message.reply_text(
        "➕ New Record\n\n"
        "Send the date and count in this format:\n\n"
        "YYYY-MM-DD count\n\n"
        "Example:\n"
        "2026-09-10 8\n\n"
        "⚠️ Future dates are not allowed.",
        reply_markup=BACK_KEYBOARD,
    )


async def save_new_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    parts = update.message.text.strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "⚠️ Invalid format.\n\n"
            "Use:\n"
            "YYYY-MM-DD count\n\n"
            "Example:\n"
            "2026-09-10 8",
            reply_markup=BACK_KEYBOARD,
        )
        return

    date_text = parts[0]
    count_text = parts[1]

    try:
        record_date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid date.\n\n"
            "Please use YYYY-MM-DD.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    try:
        count = int(count_text)

    except ValueError:
        await update.message.reply_text(
            "⚠️ Count must be a whole number.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            "⚠️ The count cannot be negative.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    try:
        user_id = get_user_id(update)

        existing = tracker.get_record(
            user_id,
            record_date
        )

        # save_record is an upsert, so one call covers both cases.
        # `existing` is only used to pick the wording of the reply.
        tracker.save_record(
            user_id,
            record_date,
            count
        )

        action = "Added" if existing is None else "Updated"

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {record_date.strftime('%B %d, %Y')}\n"
            f"Count: {count}\n\n"
            f"Action: {action}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ {e}",
            reply_markup=BACK_KEYBOARD,
        )
        return

    except Exception:
        logger.exception("Failed to save new record")

        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID,
        )

        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't save the record.\n\n"
            "Please try again later.",
            reply_markup=MAIN_KEYBOARD,
        )