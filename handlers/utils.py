from telegram import Update
from telegram.ext import ContextTypes
from services.tracker_service import tracker

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