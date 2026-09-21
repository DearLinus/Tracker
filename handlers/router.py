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
from handlers.settings import request_delete_data, confirm_delete_data
from handlers.statistics import show_statistics
from handlers.history import show_history
from handlers.navigation import go_back
from handlers.export import export_records

from keyboards import MAIN_KEYBOARD

from services.tracker_service import get_tracker_from_context as get_tracker

from handlers.utils import get_user_id, get_user_state, reset_state, clear_user_state

from handlers.constants import (
    GRAPH_TIMELINE,
    SETTINGS,
    TODAY_COUNT,
    NEW_RECORD,
    GRAPH_TIMELINES,

    GRAPH_BUTTON,
    TODAY_RECORD_BUTTON,
    STATISTICS_BUTTON,
    SETTINGS_BUTTON,
    BACK_BUTTON,
    EXPORT_BUTTON,
    NEW_RECORD_BUTTON,
    HISTORY_BUTTON,
    DARK_THEME_BUTTON,
    LIGHT_THEME_BUTTON,
    DARK_THEME,
    LIGHT_THEME,
    DELETE_DATA_BUTTON,
    CONFIRM_DELETE,
    CONFIRM_YES_BUTTON,
    CONFIRM_NO_BUTTON,
)


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # Ignore empty messages
    if not update.message or not update.message.text:
        return

    user_id = get_user_id(update)

    if not get_tracker(context).user_exists(user_id):
        await update.message.reply_text(
            "👋 Please start the bot first using /start"
        )
        return


    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")

    # If there's no in-memory state, try to read persisted state (after restart)
    if awaiting is None:
        # get_user_state is synchronous; it may mirror persisted state into context
        awaiting = get_user_state(update, context)


    # =====================================================
    # BACK
    # =====================================================

    if text == BACK_BUTTON:
        await go_back(update, context)
        return


    # =====================================================
    # MAIN MENU
    # =====================================================

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

    if text == EXPORT_BUTTON:
        await export_records(update, context)
        return


    # =====================================================
    # STATES
    # =====================================================

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
        if text == DELETE_DATA_BUTTON:
            await request_delete_data(update, context)
            return

    elif awaiting == CONFIRM_DELETE:
        if text == CONFIRM_YES_BUTTON:
            await confirm_delete_data(update, context, True)
            return
        if text == CONFIRM_NO_BUTTON:
            await confirm_delete_data(update, context, False)
            return

    elif awaiting == TODAY_COUNT:
        # Only forward to the handler if the message looks like a number.
        # Otherwise treat as unknown input to avoid accidental execution
        # when users send unrelated messages while a state is active.
        if text.lstrip("-").isdigit():
            await save_today_record(update, context)
            return
        # fall through to unknown handling below

    elif awaiting == NEW_RECORD:
        # Expect format: YYYY-MM-DD count. If it doesn't match, treat as unknown
        parts = text.split()
        if len(parts) == 2:
            date_part, count_part = parts
            if date_part.count("-") == 2 and (count_part.lstrip("-").isdigit()):
                await save_new_record(update, context)
                return
        # fall through to unknown handling below


    # =====================================================
    # UNKNOWN MESSAGE
    # =====================================================

    # Clear any transient or persisted awaiting state to avoid accidental
    # execution of previously-selected actions after an unrelated message.
    reset_state(context)
    try:
        clear_user_state(update, context)
    except Exception:
        # Be conservative: do not fail on clear_user_state issues
        pass

    await update.message.reply_text(
        "⚠️ I didn't understand that.\n\n"
        "Please choose an option from the menu.",
        reply_markup=MAIN_KEYBOARD,
    )