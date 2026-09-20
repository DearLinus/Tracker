from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from zoneinfo import ZoneInfo

from services.tracker_service import tracker

from timezone import DEFAULT_TIMEZONE

def get_user_id(update: Update):
    return update.effective_user.id


def reset_state(context: ContextTypes.DEFAULT_TYPE):
    """Clear ephemeral in-memory state only (keeps tests backwards-compatible)."""
    context.user_data.pop("awaiting", None)


def set_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: str):
    """Set both in-memory and persistent state for the user."""
    context.user_data["awaiting"] = state
    try:
        user_id = get_user_id(update)
        tracker.set_user_state(user_id, "awaiting", state)
    except Exception:
        # persistence is best-effort; do not fail the handler flow
        pass


def get_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read state: prefer in-memory (current request), fall back to persisted."""
    if "awaiting" in context.user_data:
        return context.user_data["awaiting"]

    try:
        user_id = get_user_id(update)
        state = tracker.get_user_state(user_id, "awaiting")
        if state is not None:
            # mirror into context for faster subsequent access
            context.user_data["awaiting"] = state
        return state
    except Exception:
        return None


def clear_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear both in-memory and persisted state when update is available."""
    context.user_data.pop("awaiting", None)
    try:
        user_id = get_user_id(update)
        tracker.delete_user_state(user_id, "awaiting")
    except Exception:
        pass


async def send_sticker_if_available(update: Update, sticker_id: str | None):
    if not sticker_id:
        return

    try:
        await update.message.reply_sticker(sticker_id)
    except Exception:
        pass


def get_graph_theme(update):
    user_id = get_user_id(update)

    return tracker.get_setting(
        user_id,
        "graph_theme",
        default="dark",
    )



def get_user_timezone(update):

    user_id = get_user_id(update)

    timezone = tracker.get_setting(
        user_id,
        "timezone",
        DEFAULT_TIMEZONE
    )

    return timezone



def get_user_today(update):

    timezone = get_user_timezone(update)

    return datetime.now(
        ZoneInfo(timezone)
    ).date()