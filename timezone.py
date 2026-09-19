# timezone.py

from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Tehran"


def get_today(timezone_name: str = DEFAULT_TIMEZONE):
    return datetime.now(
        ZoneInfo(timezone_name)
    ).date()