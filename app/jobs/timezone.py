from __future__ import annotations

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8 compatibility
    from pytz import timezone as ZoneInfo


def get_timezone(timezone_name: str):
    return ZoneInfo(timezone_name)
