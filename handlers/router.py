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

from handlers.constants import (
    GRAPH_TIMELINE,
    SETTINGS,
    TODAY_COUNT,
    NEW_RECORD,
    GRAPH_TIMELINES,
)

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")

    # =====================================================
    # ACTIVE STATES
    # =====================================================

    if awaiting == "graph_timeline":
        if text in GRAPH_TIMELINES:
            await send_graph(update, context, text)
            return

    elif awaiting == "settings":
        if text == "🌙 Dark Graph":
            await change_graph_theme(update, context, "dark")
            return

        if text == "☀️ Light Graph":
            await change_graph_theme(update, context, "light")
            return

    elif awaiting == "today_count":
        await save_today_record(update, context)
        return

    elif awaiting == "new_record":
        await save_new_record(update, context)
        return

    # =====================================================
    # MAIN MENU
    # =====================================================

    if text == "📈 Graph":
        await show_graph_menu(update, context)
        return

    if text == "📝 Today Record":
        await start_today_record(update, context)
        return

    if text == "➕ New Record":
        await start_new_record(update, context)
        return

    if text == "📊 Statistics":
        await show_statistics(update, context)
        return

    if text == "📜 History":
        await show_history(update, context)
        return

    if text == "⚙️ Settings":
        await show_settings(update, context)
        return

    if text == "⬅️ Back":
        await go_back(update, context)
        return