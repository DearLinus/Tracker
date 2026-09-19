from telegram import Update, InputFile
from telegram.ext import ContextTypes

from handlers.utils import (
    get_user_id,
    reset_state,
    get_graph_theme,
    get_user_today,
)
import logging

from keyboards import (
    MAIN_KEYBOARD,
    GRAPH_KEYBOARD,
)

from services.tracker_service import tracker
from graph import create_graph

from handlers.constants import (
    GRAPH_TIMELINE,
    GRAPH_TIMELINES,
)

logger = logging.getLogger(__name__)

async def show_graph_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    reset_state(context)

    context.user_data["awaiting"] = GRAPH_TIMELINE

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

        theme = get_graph_theme(update)

        graph_image = create_graph(
        tracker,
        user_id=get_user_id(update),
        timeline=timeline_name,
        theme=theme,
        today=get_user_today(update),
    )

        if graph_image is None:

            reset_state(context)

            await update.message.reply_text(
                "📈 No records available yet.",
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

        await update.message.reply_text(
            "Choose another option:",
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception:
        logger.exception("Failed to generate graph")

        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't generate the graph.",
            reply_markup=MAIN_KEYBOARD,
        )