import os
from datetime import date

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from logic import TrackerLogic
from graph import create_graph


logic = TrackerLogic()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Daily Tracker!\n\n"
        "Commands:\n"
        "/today - Today's record\n"
        "/stats - Statistics\n"
        "/history - Record history\n"
        "/graph - Current graph\n"
        "/graph weekly - Weekly graph\n"
        "/graph monthly - Monthly graph\n"
        "/graph 3m - 3 Months graph\n"
        "/graph 6m - 6 Months graph\n"
        "/graph 1y - 1 Year graph"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_date = date.today()
    count = logic.get_record(today_date)

    if count is None:
        await update.message.reply_text("No record for today.")
    else:
        await update.message.reply_text(
            f"Today ({today_date.isoformat()}): {count}"
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Total: {logic.get_total()}\n"
        f"Average: {logic.get_average():.2f}\n"
        f"Highest: {logic.get_highest()}"
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = logic.get_records()

    if not records:
        await update.message.reply_text("No records yet.")
        return

    lines = [
        f"{record_date.isoformat()}: {count}"
        for record_date, count in reversed(records.items())
    ]

    await update.message.reply_text("\n".join(lines))


def parse_timeline(context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return "Monthly"

    value = " ".join(context.args).strip().lower()

    aliases = {
        "week": "Weekly",
        "weekly": "Weekly",

        "month": "Monthly",
        "monthly": "Monthly",

        "3": "3 Months",
        "3m": "3 Months",
        "3 months": "3 Months",

        "6": "6 Months",
        "6m": "6 Months",
        "6 months": "6 Months",

        "year": "1 Year",
        "1y": "1 Year",
        "1 year": "1 Year",
    }

    return aliases.get(value, "Monthly")


async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    timeline = parse_timeline(context)

    image = create_graph(
        logic,
        timeline=timeline,
        theme="dark",
    )

    if image is None:
        await update.message.reply_text(
            "No records available yet."
        )
        return

    await update.message.reply_photo(
        photo=InputFile(
            image,
            filename="daily_tracker.png"
        ),
        caption=f"Daily Tracker — {timeline}",
    )


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("graph", graph))

    print("Telegram bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()