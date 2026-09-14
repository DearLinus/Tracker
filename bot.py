import os
import os
from dotenv import load_dotenv

load_dotenv()

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


WELCOME_STICKER_ID = os.environ.get(
    "WELCOME_STICKER_ID"
)

SUCCESS_STICKER_ID = os.environ.get(
    "SUCCESS_STICKER_ID"
)

ERROR_STICKER_ID = os.environ.get(
    "ERROR_STICKER_ID"
)


# =========================================================
# TIMELINES
# =========================================================

TIMELINES = (
    "Weekly",
    "Monthly",
    "3 Months",
    "6 Months",
    "1 Year",
)


# =========================================================
# KEYBOARDS
# =========================================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📈 Graph", "📝 Today Record"],
        ["➕ New Record", "📊 Statistics"],
        ["📜 History", "⚙️ Settings"],
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


SETTINGS_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌙 Dark Graph", "☀️ Light Graph"],
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

def get_user_id(update: Update):
    return update.effective_user.id


def get_graph_theme(update: Update):
    user_id = get_user_id(update)

    return logic.get_setting(
        user_id,
        "graph_theme",
        default="dark",
    )


def reset_state(
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data.pop(
        "awaiting",
        None
    )


async def send_sticker_if_available(
    update: Update,
    sticker_id: str | None,
):
    if not sticker_id:
        return

    try:
        await update.message.reply_sticker(
            sticker_id
        )
    except Exception:
        pass


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    await send_sticker_if_available(
        update,
        WELCOME_STICKER_ID
    )

    await update.message.reply_text(
        "👋 Welcome to Daily Tracker!\n\n"
        "Daily Tracker is a personal tracker for "
        "recording and viewing the trend of masturbation "
        "frequency over time.\n\n"
        "You can record your daily count, review your "
        "history and statistics, and visualize your "
        "progress with a graph.\n\n"
        "Choose an option below:",
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================================
# GRAPH
# =========================================================

async def show_graph_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    context.user_data["awaiting"] = (
        "graph_timeline"
    )

    await update.message.reply_text(
        "📈 Masturbation Trend\n\n"
        "This graph shows the recorded masturbation "
        "frequency over time.\n\n"
        "Choose the time range:",
        reply_markup=GRAPH_KEYBOARD,
    )


async def send_graph(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timeline_name: str,
):
    if timeline_name not in TIMELINES:
        await update.message.reply_text(
            "⚠️ Please choose one of the available "
            "time ranges.",
            reply_markup=GRAPH_KEYBOARD,
        )
        return

    try:
        theme = get_graph_theme(update)

        graph_image = create_graph(
            logic,
            timeline=timeline_name,
            theme=theme,
        )

        if graph_image is None:
            reset_state(context)

            await update.message.reply_text(
                "📈 No records available yet.\n\n"
                "Add some records first, then come "
                "back here.",
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

    except Exception as error:
        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't generate the graph.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# SETTINGS
# =========================================================

async def show_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    current_theme = get_graph_theme(
        update
    )

    theme_text = (
        "🌙 Dark"
        if current_theme == "dark"
        else "☀️ Light"
    )

    context.user_data["awaiting"] = (
        "settings"
    )

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
    if theme not in ("dark", "light"):
        return

    user_id = get_user_id(update)

    logic.set_setting(
        user_id,
        "graph_theme",
        theme,
    )

    reset_state(context)

    if theme == "dark":
        message = (
            "🌙 Dark graph enabled.\n\n"
            "Your graph will now use the dark theme."
        )
    else:
        message = (
            "☀️ Light graph enabled.\n\n"
            "Your graph will now use the light theme."
        )

    await update.message.reply_text(
        message,
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================================
# TODAY RECORD
# =========================================================

async def start_today_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    context.user_data["awaiting"] = (
        "today_count"
    )

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
    context: ContextTypes.DEFAULT_TYPE
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
            logic.add_record(
                today,
                count
            )
        else:
            logic.update_record(
                today,
                today,
                count
            )

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {today.strftime('%B %d, %Y')}\n"
            f"Count: {count}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except Exception as error:
        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID
        )

        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't save today's record.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# NEW RECORD
# =========================================================

async def start_new_record(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    reset_state(context)

    context.user_data["awaiting"] = (
        "new_record"
    )

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
    context: ContextTypes.DEFAULT_TYPE
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

    try:
        record_date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid date.\n\n"
            "Please use YYYY-MM-DD.",
            reply_markup=BACK_KEYBOARD,
        )
        return

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

    try:
        existing = logic.get_record(
            record_date
        )

        if existing is None:
            logic.add_record(
                record_date,
                count
            )
            action = "Added"
        else:
            logic.update_record(
                record_date,
                record_date,
                count
            )
            action = "Updated"

        await send_sticker_if_available(
            update,
            SUCCESS_STICKER_ID
        )

        await update.message.reply_text(
            "✅ Record saved successfully.\n\n"
            f"Date: {record_date.strftime('%B %d, %Y')}\n"
            f"Count: {count}\n\n"
            f"Action: {action}",
            reply_markup=MAIN_KEYBOARD,
        )

        reset_state(context)

    except Exception as error:
        await send_sticker_if_available(
            update,
            ERROR_STICKER_ID
        )

        reset_state(context)

        await update.message.reply_text(
            "⚠️ I couldn't save the record.\n\n"
            f"Error: {error}",
            reply_markup=MAIN_KEYBOARD,
        )


# =========================================================
# STATISTICS
# =========================================================

async def show_statistics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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
                "No records yet.",
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
    context: ContextTypes.DEFAULT_TYPE
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

        for record_date in sorted(
            records.keys(),
            reverse=True
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
    context: ContextTypes.DEFAULT_TYPE
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
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    awaiting = context.user_data.get(
        "awaiting"
    )

    # -----------------------------------------------------
    # Graph
    # -----------------------------------------------------

    if awaiting == "graph_timeline":

        if text == "⬅️ Back":
            await go_back(
                update,
                context
            )
            return

        await send_graph(
            update,
            context,
            text
        )
        return

    # -----------------------------------------------------
    # Settings
    # -----------------------------------------------------

    if awaiting == "settings":

        if text == "⬅️ Back":
            await go_back(
                update,
                context
            )
            return

        if text == "🌙 Dark Graph":
            await change_graph_theme(
                update,
                context,
                "dark"
            )
            return

        if text == "☀️ Light Graph":
            await change_graph_theme(
                update,
                context,
                "light"
            )
            return

        await update.message.reply_text(
            "⚠️ Please choose one of the "
            "available settings.",
            reply_markup=SETTINGS_KEYBOARD,
        )
        return

    # -----------------------------------------------------
    # Today
    # -----------------------------------------------------

    if awaiting == "today_count":

        if text == "⬅️ Back":
            await go_back(
                update,
                context
            )
            return

        await save_today_record(
            update,
            context
        )
        return

    # -----------------------------------------------------
    # New Record
    # -----------------------------------------------------

    if awaiting == "new_record":

        if text == "⬅️ Back":
            await go_back(
                update,
                context
            )
            return

        await save_new_record(
            update,
            context
        )
        return

    # -----------------------------------------------------
    # Main menu
    # -----------------------------------------------------

    if text == "📈 Graph":
        await show_graph_menu(
            update,
            context
        )
        return

    if text == "📝 Today Record":
        await start_today_record(
            update,
            context
        )
        return

    if text == "➕ New Record":
        await start_new_record(
            update,
            context
        )
        return

    if text == "📊 Statistics":
        await show_statistics(
            update,
            context
        )
        return

    if text == "📜 History":
        await show_history(
            update,
            context
        )
        return

    if text == "⚙️ Settings":
        await show_settings(
            update,
            context
        )
        return

    if text == "⬅️ Back":
        await go_back(
            update,
            context
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
    context: ContextTypes.DEFAULT_TYPE
):
    print(
        "Telegram bot error:",
        context.error
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
            "TELEGRAM_BOT_TOKEN environment variable "
            "is not set."
        )

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    # Only /start remains a command.
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "Daily Tracker bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()