from telegram import Update
from telegram.ext import ContextTypes

from keyboards import MAIN_KEYBOARD, SETTINGS_KEYBOARD
from services.tracker_service import get_tracker_from_context as get_tracker


from handlers.utils import (
    get_user_id,
    reset_state,
    get_graph_theme,
    set_user_state,
    clear_user_state,
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
    clear_user_state(update, context)

    current_theme = get_graph_theme(update, context)

    theme_text = (
        "🌙 Dark"
        if current_theme == DARK_THEME
        else "☀️ Light"
    )

    set_user_state(update, context, SETTINGS)

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
    reset_state(context)
    clear_user_state(update, context)

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
        await update.message.reply_text(
            "⚠️ Invalid theme.",
            reply_markup=MAIN_KEYBOARD,
        )

        # Do not persist invalid theme
        return

    # Persist only after validation
    get_tracker(context).set_setting(
        user_id,
        "graph_theme",
        theme,
    )

    await update.message.reply_text(
        message,
        reply_markup=MAIN_KEYBOARD,
    )