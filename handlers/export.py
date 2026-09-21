import csv
import os
import tempfile
import asyncio
import functools

from telegram import Update
from telegram.ext import ContextTypes

from services.tracker_service import get_tracker_from_context as get_tracker

from handlers.utils import get_user_id


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

    user_id = get_user_id(update)

    # Offload fetching records and file creation to a thread
    filename = await asyncio.to_thread(
        functools.partial(_build_export_file, get_tracker(context), user_id)
    )

    if not filename:
        await update.message.reply_text("📤 No records available to export.")
        return

    try:
        with open(filename, "rb") as file:
            await update.message.reply_document(document=file, filename="tracker_history.csv")
    finally:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception:
            pass