import os
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = os.getenv("TIMEZONE", "America/Toronto")

_tz = ZoneInfo(TIMEZONE)


def now() -> datetime:
    return datetime.now(tz=_tz)
