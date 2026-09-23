import asyncio
import functools
import logging
import sqlite3
from zoneinfo import ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import ContextTypes

from config import ERROR_STICKER_ID, SUCCESS_STICKER_ID
from handlers.constants import (
    COUNT_MUST_BE_WHOLE_NUMBER_MESSAGE,
    GENERIC_RECORD_ERROR_MESSAGE,
    INVALID_DATE_MESSAGE,
    INVALID_FORMAT_MESSAGE,
    INVALID_NUMBER_MESSAGE,
    NEGATIVE_COUNT_MESSAGE,
    NEW_RECORD,
    RECORD_SAVED_TEMPLATE,
    TODAY_COUNT,
    TODAY_RECORD_PROMPT,
    TODAY_RECORD_UPDATE_PROMPT,
)
from handlers.utils import (
    clear_user_state,
    get_user_id,
    get_user_today,
    parse_date,
    parse_int,
    reset_state,
    send_sticker_if_available,
    set_user_state,
)
from keyboards import BACK_KEYBOARD, MAIN_KEYBOARD
from services.tracker_service import get_tracker_from_context as get_tracker

logger = logging.getLogger(__name__)
# =========================================================
# HELPERS
# =========================================================


async def _clear_record_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset ephemeral and persisted state after a record save attempt."""
    reset_state(context)
    try:
        await asyncio.to_thread(functools.partial(clear_user_state, update, context))
    except sqlite3.Error as db_err:
        logger.warning("Failed to clear user state from DB (continuing): %s", db_err)


# =========================================================
# TODAY RECORD
# =========================================================

async def start_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)
    # persist and mirror the new awaiting state
    set_user_state(update, context, TODAY_COUNT)

    today_date = get_user_today(update, context)
    user_id = get_user_id(update)

    # Offload DB read to thread
    existing = await asyncio.to_thread(
        functools.partial(get_tracker(context).get_record, user_id, today_date)
    )

    date_label = today_date.strftime("%B %d, %Y")
    if existing is None:
        message = TODAY_RECORD_PROMPT.format(date_label=date_label)
    else:
        message = TODAY_RECORD_UPDATE_PROMPT.format(count=existing)

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
        count = parse_int(text)

    except ValueError:
        await update.message.reply_text(
            INVALID_NUMBER_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            NEGATIVE_COUNT_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    today_date = get_user_today(update, context)

    try:
        # save_record is an upsert: it creates the record
        # or overwrites the existing one for that date.
        # Offload DB write to thread
        await asyncio.to_thread(
            functools.partial(
                get_tracker(context).save_record,
                user_id,
                today_date,
                count,
            )
        )

        # Clear state BEFORE sending sticker/reply to avoid leaving stale state
        # if Telegram I/O fails. Reset in-memory first, then clear persisted state.
        await _clear_record_state(update, context)

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID
        )

        await update.message.reply_text(
            RECORD_SAVED_TEMPLATE.format(
                date_label=today_date.strftime("%B %d, %Y"),
                count=count,
            ),
            reply_markup=MAIN_KEYBOARD,
        )

    except ValueError as exc:
        # Expected validation errors raised by TrackerLogic
        logger.warning("Rejected today's record: %s", exc)

        await _clear_record_state(update, context)

        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID,
        )

        await update.message.reply_text(
            f"⚠️ {exc}",
            reply_markup=MAIN_KEYBOARD,
        )

    # Expected exceptions: validation/type errors from TrackerLogic, DB errors, or missing tracker.
    # We handle these to give a user-facing message; unexpected exceptions should bubble up.
    except (TypeError, sqlite3.Error, RuntimeError):
        # TypeError: validation type issues from TrackerLogic
        # sqlite3.Error: DB errors bubbled from TrackerDatabase
        # RuntimeError: missing tracker or app initialization
        logger.exception("Failed to save today's record")

        await _clear_record_state(update, context)

        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID,
        )

        await update.message.reply_text(
            GENERIC_RECORD_ERROR_MESSAGE,
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

    set_user_state(update, context, NEW_RECORD)

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
            INVALID_FORMAT_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    date_text = parts[0]
    count_text = parts[1]

    try:
        record_date = parse_date(date_text)

    except ValueError:
        await update.message.reply_text(
            INVALID_DATE_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    try:
        count = parse_int(count_text)

    except ValueError:
        await update.message.reply_text(
            COUNT_MUST_BE_WHOLE_NUMBER_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            NEGATIVE_COUNT_MESSAGE,
            reply_markup=BACK_KEYBOARD,
        )
        return

    try:
        user_id = get_user_id(update)

        # Cache tracker to avoid repeated lookups in this scope
        tracker = get_tracker(context)
        # Offload get_record and save_record to threads
        existing = await asyncio.to_thread(
            functools.partial(tracker.get_record, user_id, record_date)
        )

        await asyncio.to_thread(
            functools.partial(tracker.save_record, user_id, record_date, count)
        )

        # Clear state BEFORE sending sticker/reply to avoid leaving stale state
        # if Telegram I/O fails. Reset in-memory first, then clear persisted state.
        await _clear_record_state(update, context)

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

    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ {e}",
            reply_markup=BACK_KEYBOARD,
        )
        return

    # Expected exceptions: validation/type errors, DB errors, missing tracker, or timezone resolution failures.
    # These are handled to present a friendly error to users; programmer errors should not be swallowed.
    except (TypeError, sqlite3.Error, RuntimeError, ZoneInfoNotFoundError):
        # TypeError: validation type issues from TrackerLogic
        # sqlite3.Error: DB errors bubbled from TrackerDatabase
        # RuntimeError: missing tracker or app initialization
        # ZoneInfoNotFoundError: invalid timezone names during date validation
        logger.exception("Failed to save new record")

        await _clear_record_state(update, context)

        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID,
        )

        await update.message.reply_text(
            "⚠️ I couldn't save the record.\n\n"
            "Please try again later.",
            reply_markup=MAIN_KEYBOARD,
        )