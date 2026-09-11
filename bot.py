import os

from datetime import date, datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InputFile,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from logic import TrackerLogic
from graph import create_graph


# =========================================================
# CONFIG
# =========================================================

logic = TrackerLogic()

# Optional sticker IDs.
#
# You can set these as environment variables:
#
# WELCOME_STICKER_ID
# SUCCESS_STICKER_ID
# ERROR_STICKER_ID
#
# If they are not set, the bot simply uses emojis instead.

WELCOME_STICKER_ID = os.environ.get("WELCOME_STICKER_ID")
SUCCESS_STICKER_ID = os.environ.get("SUCCESS_STICKER_ID")
ERROR_STICKER_ID = os.environ.get("ERROR_STICKER_ID")


# =========================================================
# TIMELINES
# =========================================================

TIMELINE_DAYS = {
    "Weekly": 7,
    "Monthly": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
}


# =========================================================
# KEYBOARDS
# =========================================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📈 Graph", "📝 Today Record"],
        ["➕ New Record", "📊 Statistics"],
        ["📜 History"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


GRAPH_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Weekly", "Monthly"],
        ["3 Months", "6 Months"],
        ["1 Year"],
        ["⬅️ Back"],
    ],
    resize_keyboard=True,
)


BACK_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["⬅️ Back"],
    ],
    resize_keyboard=True,
)


# =========================================================
# HELPERS
# =========================================================

async def send_sticker_if_available(
    update: Update,
    sticker_id: str | None,
):
    """
    Send a sticker if a valid Telegram sticker file_id
    has been configured.
    """

    if not sticker_id:
        return

    try:
        await update.message.reply_sticker(sticker_id)
    except Exception:
        # A bad/expired sticker ID should never break the bot.
        pass


def reset_state(
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Clear any active input state.
    """

    context.user_data.pop("awaiting", None)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID,
    )

    await update.message.reply_text(
        "👋 Welcome to Daily Tracker!\n\n"
        "Track your daily progress, review your history, "
        "check your statistics, and visualize your activity "
        "with a graph.\n\n"
        "Choose an option below:",
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================================
# GRAPH
# =========================================================

async def show_graph_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    context.user_data["awaiting"] = "graph_timeline"

    await update.message.reply_text(
        "📈 Graph\n\n"
        "Choose the time range you want to see:",
        reply_markup=GRAPH_KEYBOARD,
    )


async def send_graph(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timeline_name: str,
):
    if timeline_name not in TIMELINE_DAYS:
        await update.message.reply_text(
            "⚠️ Please choose one of the available time ranges.",
            reply_markup=GRAPH_KEYBOARD,
        )
        return

    try:
        # create_graph() returns a BytesIO image.
        graph_image = create_graph(
            logic,
            timeline=timeline_name,
            theme="dark",
        )

        if graph_image is None:
            await update.message.reply_text(
                "📈 No records available yet.\n\n"
                "Add some records first, then come back here.",
                reply_markup=MAIN_KEYBOARD,
            )

            reset_state(context)
            return

        graph_image.seek(0)

        await update.message.reply_photo(
            photo=InputFile(
                graph_image,
                filename="daily_tracker.png",
            ),
            caption=(
                f"📈 Daily Tracker\n\n"
                f"Time range: {timeline_name}"
            ),
        )

        reset_state(context)

        await update.message.reply_text(
            "Choose another option:",
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception as error:
        await update.message.reply_text(
            "⚠️ I couldn't generate the graph.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)


# =========================================================
# TODAY RECORD
# =========================================================

async def start_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    context.user_data["awaiting"] = "today_count"

    today = date.today()
    existing = logic.get_record(today)

    if existing is None:
        message = (
            "📝 Today Record\n\n"
            f"Today is {today.strftime('%B %d, %Y')}.\n\n"
            "How many times did you do it today?\n\n"
            "Send the number only.\n"
            "Example: 8"
        )
    else:
        message = (
            "📝 Today Record\n\n"
            f"Today's current record is {existing}.\n\n"
            "Send the new count to update it.\n\n"
            "Example: 8"
        )

    await update.message.reply_text(
        message,
        reply_markup=BACK_KEYBOARD,
    )


async def save_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    try:
        count = int(text)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a whole number.\n\n"
            "Example: 8",
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            "⚠️ The count cannot be negative.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    today = date.today()

    try:
        existing = logic.get_record(today)

        if existing is None:
            logic.add_record(today, count)
        else:
            logic.update_record(
                today,
                today,
                count,
            )

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID,
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {today.strftime('%B %d, %Y')}\n"
            f"Count: {count}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except Exception as error:
        await update.message.reply_text(
            "⚠️ I couldn't save today's record.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)


# =========================================================
# NEW RECORD
# =========================================================

async def start_new_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    context.user_data["awaiting"] = "new_record"

    await update.message.reply_text(
        "➕ New Record\n\n"
        "Send the date and count in this format:\n\n"
        "YYYY-MM-DD count\n\n"
        "Example:\n"
        "2026-09-10 8",
        reply_markup=BACK_KEYBOARD,
    )


async def save_new_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    parts = update.message.text.strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "⚠️ Invalid format.\n\n"
            "Use:\n"
            "YYYY-MM-DD count\n\n"
            "Example:\n"
            "2026-09-10 8",
            reply_markup=BACK_KEYBOARD,
        )
        return

    date_text = parts[0]
    count_text = parts[1]

    # -----------------------------
    # Date
    # -----------------------------

    try:
        record_date = datetime.strptime(
            date_text,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid date.\n\n"
            "Please use YYYY-MM-DD.\n\n"
            "Example:\n"
            "2026-09-10 8",
            reply_markup=BACK_KEYBOARD,
        )
        return

    # -----------------------------
    # Count
    # -----------------------------

    try:
        count = int(count_text)

    except ValueError:
        await update.message.reply_text(
            "⚠️ Count must be a whole number.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    if count < 0:
        await update.message.reply_text(
            "⚠️ The count cannot be negative.",
            reply_markup=BACK_KEYBOARD,
        )
        return

    # -----------------------------
    # Save / Update
    # -----------------------------

    try:
        existing = logic.get_record(record_date)

        if existing is None:
            logic.add_record(
                record_date,
                count,
            )
            action = "added"

        else:
            logic.update_record(
                record_date,
                record_date,
                count,
            )
            action = "updated"

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID,
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {record_date.strftime('%B %d, %Y')}\n"
            f"Count: {count}\n\n"
            f"Action: {action.capitalize()}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except Exception as error:
        await update.message.reply_text(
            "⚠️ I couldn't save the record.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)


# =========================================================
# STATISTICS
# =========================================================

async def show_statistics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    try:
        total = logic.get_total()
        average = logic.get_average()
        highest = logic.get_highest()
        records = logic.get_records()

        if not records:
            await update.message.reply_text(
                "📊 Statistics\n\n"
                "No records yet.\n\n"
                "Add your first record to start tracking.",
                reply_markup=MAIN_KEYBOARD,
            )
            return

        await update.message.reply_text(
            "📊 Statistics\n\n"
            f"Total: {total}\n"
            f"Daily Average: {average:.2f}\n"
            f"Highest: {highest}\n"
            f"Recorded Days: {len(records)}",
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception as error:
        await update.message.reply_text(
            "⚠️ I couldn't load the statistics.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# HISTORY
# =========================================================

async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    try:
        records = logic.get_records()

        if not records:
            await update.message.reply_text(
                "📜 History\n\n"
                "No records yet.",
                reply_markup=MAIN_KEYBOARD,
            )
            return

        lines = [
            "📜 History",
            "",
        ]

        # Newest first
        for record_date in sorted(
            records.keys(),
            reverse=True,
        ):
            count = records[record_date]

            lines.append(
                f"{record_date.strftime('%b %d, %Y')} — {count}"
            )

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception as error:
        await update.message.reply_text(
            "⚠️ I couldn't load the history.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# BACK
# =========================================================

async def go_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reset_state(context)

    await update.message.reply_text(
        "🏠 Main Menu\n\n"
        "Choose an option:",
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    # -----------------------------------------------------
    # Active input states
    # -----------------------------------------------------

    awaiting = context.user_data.get("awaiting")

    if awaiting == "graph_timeline":

        if text == "⬅️ Back":
            await go_back(update, context)
            return

        await send_graph(
            update,
            context,
            text,
        )
        return

    if awaiting == "today_count":

        if text == "⬅️ Back":
            await go_back(update, context)
            return

        await save_today_record(
            update,
            context,
        )
        return

    if awaiting == "new_record":

        if text == "⬅️ Back":
            await go_back(update, context)
            return

        await save_new_record(
            update,
            context,
        )
        return

    # -----------------------------------------------------
    # Main menu
    # -----------------------------------------------------

    if text == "📈 Graph":
        await show_graph_menu(
            update,
            context,
        )
        return

    if text == "📝 Today Record":
        await start_today_record(
            update,
            context,
        )
        return

    if text == "➕ New Record":
        await start_new_record(
            update,
            context,
        )
        return

    if text == "📊 Statistics":
        await show_statistics(
            update,
            context,
        )
        return

    if text == "📜 History":
        await show_history(
            update,
            context,
        )
        return

    if text == "⬅️ Back":
        await go_back(
            update,
            context,
        )
        return

    # -----------------------------------------------------
    # Unknown text
    # -----------------------------------------------------

    await update.message.reply_text(
        "🤔 I didn't recognize that option.\n\n"
        "Please choose something from the menu below.",
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(
        "Telegram bot error:",
        context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set."
        )

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    # -----------------------------
    # Commands
    # -----------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # -----------------------------
    # Text / button handling
    # -----------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    # -----------------------------
    # Errors
    # -----------------------------

    app.add_error_handler(
        error_handler
    )

    print("Daily Tracker bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()