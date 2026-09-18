from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD, SETTINGS_KEYBOARD
from services.tracker_service import tracker

from handlers.utils import (
    get_user_id,
    reset_state,
    get_graph_theme,
)

from handlers.constants import (
    SETTINGS,
    DARK_THEME,
    LIGHT_THEME,
)


async def show_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)

    current_theme = get_graph_theme(update)

    theme_text = (
        "🌙 Dark"
        if current_theme == DARK_THEME
        else "☀️ Light"
    )

    context.user_data["awaiting"] = SETTINGS

    await update.message.reply_text(
        "⚙️ Settings\n\n"
        "Graph appearance\n\n"
        f"Current theme: {theme_text}\n\n"
        "Choose how your graph should look:",
        reply_markup=SETTINGS_KEYBOARD,
    )


async def change_graph_theme(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    theme: str,
):

    user_id = get_user_id(update)

    tracker.set_setting(
        user_id,
        "graph_theme",
        theme,
    )

    reset_state(context)

    if theme == DARK_THEME:
        message = (
            "🌙 Dark graph enabled.\n\n"
            "Your graph will now use the dark theme."
        )

    elif theme == LIGHT_THEME:
        message = (
            "☀️ Light graph enabled.\n\n"
            "Your graph will now use the light theme."
        )

    else:
        message = "⚠️ Invalid theme."

    await update.message.reply_text(
        message,
        reply_markup=MAIN_KEYBOARD,
    )