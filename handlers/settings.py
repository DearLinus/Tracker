import asyncio
import functools

from telegram import Update
from telegram.ext import ContextTypes

from handlers.constants import (
    CONFIRM_DELETE,
    DARK_THEME,
    LIGHT_THEME,
    PENDING_DELETION_RESTORE_MESSAGE,
    SETTINGS,
)
from handlers.utils import (
    clear_user_state,
    get_graph_theme,
    get_user_id,
    reset_state,
    set_user_state,
)
from keyboards import (
    CONFIRM_DELETE_KEYBOARD,
    MAIN_KEYBOARD,
    PENDING_DELETE_KEYBOARD,
    SETTINGS_KEYBOARD,
)
from services.tracker_service import get_tracker_from_context as get_tracker


async def show_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    reset_state(context)
    # clear persisted state off the event loop
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    user_id = get_user_id(update)
    tracker = get_tracker(context)
    current_theme = await asyncio.to_thread(functools.partial(get_graph_theme, update, context))
    pending = await asyncio.to_thread(functools.partial(tracker.get_pending_deletion, user_id))

    theme_text = (
        "🌙 Dark"
        if current_theme == DARK_THEME
        else "☀️ Light"
    )

    keyboard = PENDING_DELETE_KEYBOARD if pending else SETTINGS_KEYBOARD
    await asyncio.to_thread(functools.partial(set_user_state, update, context, SETTINGS))

    await update.message.reply_text(
        "⚙️ Settings\n\n"
        "Graph appearance\n\n"
        f"Current theme: {theme_text}\n\n"
        "Choose how your graph should look:",
        reply_markup=keyboard,
    )


async def change_graph_theme(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    theme: str,
):

    user_id = get_user_id(update)
    reset_state(context)
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

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

    await asyncio.to_thread(functools.partial(set_user_state, update, context, CONFIRM_DELETE))

    await update.message.reply_text(
        "🗑️ Delete My Data\n\n"
        "This starts a 7-day recovery window.\n"
        "Your data remains available for restoration during that time.\n"
        "After 7 days, the active database entries are permanently removed.\n"
        "External recovery snapshots are deleted at that point.\n"
        "Historical database backups follow the configured BACKUP_RETENTION policy and are not scrubbed per user.\n\n"
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
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    tracker = get_tracker(context)

    if confirm:
        request_method = getattr(tracker, "request_pending_deletion", None)
        pending = None
        if callable(request_method):
            try:
                pending = await asyncio.to_thread(functools.partial(request_method, user_id))
            except ValueError:
                pending = None
        else:
            delete_method = getattr(tracker, "delete_user", None)
            if callable(delete_method):
                deleted = await asyncio.to_thread(functools.partial(delete_method, user_id))
                pending = {"status": "pending"} if deleted else None

        if not isinstance(pending, dict):
            pending = None

        if pending:
            if pending.get("status") == "deleted":
                await update.message.reply_text(
                    "✅ Your data has been deleted.",
                    reply_markup=MAIN_KEYBOARD,
                )
            else:
                await update.message.reply_text(
                    "🗑️ Your data has been scheduled for deletion.\n\n"
                    "You have 7 days to restore it.\n"
                    "After that, your data is permanently removed from the active database and the recovery snapshot is deleted.\n"
                    "Backups follow the configured retention policy and are not scrubbed immediately.",
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


async def restore_delete_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = get_user_id(update)
    tracker = get_tracker(context)

    reset_state(context)
    await asyncio.to_thread(functools.partial(clear_user_state, update, context))

    restore_method = getattr(tracker, "restore_pending_deletion", None)
    restored = False
    if callable(restore_method):
        restored = await asyncio.to_thread(functools.partial(restore_method, user_id))
    if not isinstance(restored, bool):
        restored = False
    if restored:
        await update.message.reply_text(
            PENDING_DELETION_RESTORE_MESSAGE,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    await update.message.reply_text(
        "⚠️ Your deletion window has expired or no pending deletion was found.",
        reply_markup=MAIN_KEYBOARD,
    )