import os
from datetime import date

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from logic import TrackerLogic


logic = TrackerLogic()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Daily Tracker!\n\n"
        "Commands:\n" 
        "/today - Today's record\n"
        "/stats - Statistics\n"
        "/history - Record history"
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

    print("Telegram bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()