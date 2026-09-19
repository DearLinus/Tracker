from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Tehran"


def today(timezone=DEFAULT_TIMEZONE):
    return datetime.now(
        ZoneInfo(timezone)
    ).date()