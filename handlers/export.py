import asyncio
import csv
import functools
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from handlers.utils import enforce_rate_limit, get_user_id
from services.tracker_service import get_tracker_from_context as get_tracker


def _build_export_file(tracker, user_id):
    """Blocking helper run in thread: fetch records and write CSV file.

    Returns path to temporary file, or None if no records.
    """
    records = tracker.get_records(user_id)

    if not records:
        return None

    with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        suffix=".csv",
        delete=False
    ) as file:

        filename = file.name

        writer = csv.writer(file)

        writer.writerow(["date", "count"])

        for record_date, count in sorted(records.items()):
            writer.writerow([record_date, count])

    return filename


async def export_records(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await enforce_rate_limit(
        update,
        context,
        "export_generation",
        message="⏳ Export generation is rate-limited. Please wait a minute and try again.",
    ):
        return

    user_id = get_user_id(update)

    # Offload fetching records and file creation to a thread
    filename = await asyncio.to_thread(
        functools.partial(_build_export_file, get_tracker(context), user_id)
    )

    if not filename:
        await update.message.reply_text("📤 No records available to export.")
        return

    try:
        file_bytes = await asyncio.to_thread(_read_export_bytes, filename)
        await update.message.reply_document(document=file_bytes, filename="tracker_history.csv")
    finally:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except OSError:
            pass


def _read_export_bytes(filename):
    with open(filename, "rb") as file:
        return file.read()