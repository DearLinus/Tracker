from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/London"


def today():
    return datetime.now(ZoneInfo(TIMEZONE)).date()