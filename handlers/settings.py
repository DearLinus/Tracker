import asyncio
import functools

from telegram import Update
from telegram.ext import ContextTypes

from handlers.constants import (
    CONFIRM_DELETE,
    DARK_THEME,
    LIGHT_THEME,
    SETTINGS,
)
from handlers.utils import (
    clear_user_state,
    get_graph_theme,
    get_user_id,
    reset_state,
    set_user_state,
)
from keyboards import CONFIRM_DELETE_KEYBOARD, MAIN_KEYBOARD, SETTINGS_KEYBOARD
from services.tracker_service import get_tracker_from_context as get_tracker


async def show_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)
    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

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
    await asyncio.to_thread(
        functools.partial(
            get_tracker(context).set_setting,
            user_id,
            "graph_theme",
            theme,
        )
    )

    await update.message.reply_text(
        message,
        reply_markup=MAIN_KEYBOARD,
    )


async def request_delete_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Start a confirmation flow for deleting the user's data.

    This sets a persisted state so the confirmation survives restarts.
    """
    reset_state(context)
    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    set_user_state(update, context, CONFIRM_DELETE)

    await update.message.reply_text(
        "🗑️ Delete My Data\n\n"
        "This will permanently delete all your records and settings.\n"
        "Are you sure you want to continue?",
        reply_markup=CONFIRM_DELETE_KEYBOARD,
    )


async def confirm_delete_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    confirm: bool,
):
    user_id = get_user_id(update)

    # Clear transient state first
    reset_state(context)
    clear_user_state(update, context)

    tracker = get_tracker(context)

    if confirm:
        # delete_user will cascade to records/settings/user_states via FK
        # TrackerLogic.delete_user raises ValueError when the user does not
        # exist; treat that as "no data found" so the handler presents a
        # friendly message instead of bubbling an exception.
        try:
            deleted = await asyncio.to_thread(functools.partial(tracker.delete_user, user_id))
        except ValueError:
            deleted = False

        if deleted:
            await update.message.reply_text(
                "✅ Your data has been deleted.",
                reply_markup=MAIN_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "ℹ️ No data found for your account.",
                reply_markup=MAIN_KEYBOARD,
            )
        return

    # Cancelled
    await update.message.reply_text(
        "❌ Deletion cancelled.",
        reply_markup=MAIN_KEYBOARD,
    )