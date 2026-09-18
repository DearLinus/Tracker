from telegram import Update
from telegram.ext import ContextTypes

from handlers.graph import show_graph_menu, send_graph
from handlers.records import (
    start_today_record,
    save_today_record,
    start_new_record,
    save_new_record,
)
from handlers.settings import show_settings, change_graph_theme
from handlers.statistics import show_statistics
from handlers.history import show_history
from handlers.navigation import go_back

from keyboards import MAIN_KEYBOARD
from services.tracker_service import tracker
from handlers.utils import get_user_id

from handlers.constants import (
    GRAPH_TIMELINE,
    SETTINGS,
    TODAY_COUNT,
    NEW_RECORD,
    GRAPH_TIMELINES,
)

from handlers.constants import (
    GRAPH_BUTTON,
    TODAY_RECORD_BUTTON,
    STATISTICS_BUTTON,
    SETTINGS_BUTTON,
    BACK_BUTTON,
    NEW_RECORD_BUTTON,
    HISTORY_BUTTON,
    DARK_THEME_BUTTON,
    LIGHT_THEME_BUTTON,
    DARK_THEME,
    LIGHT_THEME,
)

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = get_user_id(update)

    if not tracker.user_exists(user_id):
        await update.message.reply_text(
            "👋 Please start the bot first using /start"
        )
        return

    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")

    # Back always has priority
    if text == BACK_BUTTON:
        await go_back(update, context)
        return

    if awaiting == GRAPH_TIMELINE:
        if text in GRAPH_TIMELINES:
            await send_graph(update, context, text)
            return

    elif awaiting == SETTINGS:
        if text == DARK_THEME_BUTTON:
            await change_graph_theme(update, context, DARK_THEME)
            return

        if text == LIGHT_THEME_BUTTON:
            await change_graph_theme(update, context, LIGHT_THEME)
            return

    elif awaiting == TODAY_COUNT:
        await save_today_record(update, context)
        return

    elif awaiting == NEW_RECORD:
        await save_new_record(update, context)
        return

    if text == GRAPH_BUTTON:
        await show_graph_menu(update, context)
        return

    if text == TODAY_RECORD_BUTTON:
        await start_today_record(update, context)
        return

    if text == NEW_RECORD_BUTTON:
        await start_new_record(update, context)
        return

    if text == STATISTICS_BUTTON:
        await show_statistics(update, context)
        return

    if text == HISTORY_BUTTON:
        await show_history(update, context)
        return

    if text == SETTINGS_BUTTON:
        await show_settings(update, context)
        return
    # =====================================================
    # UNKNOWN MESSAGE
    # =====================================================
    await update.message.reply_text(
        "⚠️ I didn't understand that.\n\n"
        "Please choose an option from the menu.",
            reply_markup=MAIN_KEYBOARD,
        )