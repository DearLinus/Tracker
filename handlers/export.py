import csv
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from services.tracker_service import get_tracker_from_context as get_tracker

from handlers.utils import get_user_id


async def export_records(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = get_user_id(update)

    records = get_tracker(context).get_records(user_id)

    if not records:
        await update.message.reply_text(
            "📤 No records available to export."
        )
        return


    with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        suffix=".csv",
        delete=False
    ) as file:

        filename = file.name

        writer = csv.writer(file)

        writer.writerow(
            [
                "date",
                "count"
            ]
        )

        for record_date, count in sorted(
            records.items()
        ):
            writer.writerow(
                [
                    record_date,
                    count
                ]
            )


    try:

        with open(
            filename,
            "rb"
        ) as file:

            await update.message.reply_document(
                document=file,
                filename="tracker_history.csv"
            )

    finally:

        if os.path.exists(filename):
            os.remove(filename)