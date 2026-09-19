from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from zoneinfo import ZoneInfo

from services.tracker_service import tracker

from timezone import DEFAULT_TIMEZONE

def get_user_id(update: Update):
    return update.effective_user.id


def reset_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting", None)

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