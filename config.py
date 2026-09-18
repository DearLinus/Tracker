import os
from dotenv import load_dotenv

load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)


WELCOME_STICKER_ID = os.getenv(
    "WELCOME_STICKER_ID"
)

SUCCESS_STICKER_ID = os.getenv(
    "SUCCESS_STICKER_ID"
)

ERROR_STICKER_ID = os.getenv(
    "ERROR_STICKER_ID"
)