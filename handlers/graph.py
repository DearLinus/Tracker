import asyncio
import functools
import logging
import sqlite3
from zoneinfo import ZoneInfoNotFoundError

from telegram import InputFile, Update
from telegram.ext import ContextTypes

from graph import create_graph
from handlers.constants import (
    GRAPH_TIMELINE,
    GRAPH_TIMELINES,
)
from handlers.utils import (
    clear_user_state,
    enforce_rate_limit,
    get_graph_theme,
    get_user_id,
    get_user_today,
    reset_state,
    set_user_state,
)
from keyboards import (
    GRAPH_KEYBOARD,
    MAIN_KEYBOARD,
)
from services.tracker_service import get_tracker_from_context as get_tracker

logger = logging.getLogger(__name__)

async def show_graph_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    reset_state(context)
    set_user_state(update, context, GRAPH_TIMELINE)

    await update.message.reply_text(
        "📈 Masturbation Trend\n\n"
        "This graph shows the recorded "
        "frequency over time.\n\n"
        "Choose the time range:",
        reply_markup=GRAPH_KEYBOARD,
    )


async def send_graph(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timeline_name: str,
):

    if timeline_name not in GRAPH_TIMELINES:

        await update.message.reply_text(
            "⚠️ Please choose one of the available "
            "time ranges.",
            reply_markup=GRAPH_KEYBOARD,
        )

        return

    try:
        if not await enforce_rate_limit(
            update,
            context,
            "graph_generation",
            message="⏳ Graph generation is rate-limited. Please wait a minute and try again.",
        ):
            return

        theme = get_graph_theme(update, context)

        # Offload graph generation to a thread to avoid blocking the event loop.
        graph_image = await asyncio.to_thread(
            functools.partial(
                create_graph,
                get_tracker(context),
                user_id=get_user_id(update),
                timeline=timeline_name,
                theme=theme,
                today=get_user_today(update, context),
            )
        )

        if graph_image is None:

            reset_state(context)
            clear_user_state(update, context)

            await update.message.reply_text(
                "📈 No records available yet.",
                reply_markup=MAIN_KEYBOARD,
            )

            return

        # Special sentinel: user has records, but none in the requested range
        if graph_image == "empty_range":
            reset_state(context)
            clear_user_state(update, context)

            await update.message.reply_text(
                "📈 You have records, but none in the selected time range.",
                reply_markup=MAIN_KEYBOARD,
            )

            return

        graph_image.seek(0)

        await update.message.reply_photo(
            photo=InputFile(
                graph_image,
                filename="masturbation_trend.png",
            ),
            caption=(
                "📈 Masturbation Trend\n\n"
                f"Time range: {timeline_name}\n"
                f"Theme: {theme.capitalize()}"
            ),
        )

        reset_state(context)
        clear_user_state(update, context)

        await update.message.reply_text(
            "Choose another option:",
            reply_markup=MAIN_KEYBOARD,
        )

    # Expected exceptions: timezone resolution, DB access, graph generation, or missing tracker.
    # Handle these to provide a friendly reply; unexpected exceptions should propagate for debugging.
    except (ZoneInfoNotFoundError, sqlite3.Error, ValueError, OSError, RuntimeError):
        logger.exception("Failed to generate graph")

        reset_state(context)
        clear_user_state(update, context)

        await update.message.reply_text(
            "⚠️ I couldn't generate the graph.",
            reply_markup=MAIN_KEYBOARD,
        )