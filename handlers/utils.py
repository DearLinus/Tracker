from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from services.tracker_service import get_tracker_from_context as get_tracker


from timezone import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

def get_user_id(update: Update):
    return update.effective_user.id


def reset_state(context: ContextTypes.DEFAULT_TYPE):
    """Clear ephemeral in-memory state only (keeps tests backwards-compatible)."""
    context.user_data.pop("awaiting", None)


def set_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: str):
    """Set both in-memory and persistent state for the user."""
    context.user_data["awaiting"] = state
    user_id = get_user_id(update)
    get_tracker(context).set_user_state(user_id, "awaiting", state)


def get_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read state: prefer in-memory (current request), fall back to persisted."""
    if "awaiting" in context.user_data:
        return context.user_data["awaiting"]
    user_id = get_user_id(update)
    state = get_tracker(context).get_user_state(user_id, "awaiting")
    if state is not None:
        # mirror into context for faster subsequent access
        context.user_data["awaiting"] = state
    return state


def clear_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear both in-memory and persisted state when update is available."""
    context.user_data.pop("awaiting", None)
    user_id = get_user_id(update)
    get_tracker(context).delete_user_state(user_id, "awaiting")


async def send_sticker_if_available(update: Update, sticker_id: str | None):
    """Send a sticker if available. Telegram errors are logged and not propagated.
    
    Sticker failures must never break the main handler flow (e.g., blocking a record save).
    """
    if not sticker_id:
        return
    try:
        await update.message.reply_sticker(sticker_id)
    except TelegramError as exc:
        logger.warning("Failed to send sticker: %s", exc)


def get_graph_theme(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)

    return get_tracker(context).get_setting(
        user_id,
        "graph_theme",
        default="dark",
    )



def get_user_timezone(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)

    return get_tracker(context).get_setting(
        user_id,
        "timezone",
        DEFAULT_TIMEZONE,
    )



def get_user_today(update, context: ContextTypes.DEFAULT_TYPE):
    timezone = get_user_timezone(update, context)

    return datetime.now(
        ZoneInfo(timezone)
    ).date()