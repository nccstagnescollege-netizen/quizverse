from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from collections import defaultdict


def generate_date_buckets(period: str = "daily") -> List[str]:
    """
    Generates ordered bucket keys:
    - 'daily': last 14 days (YYYY-MM-DD)
    - 'weekly': last 8 weeks (YYYY-MM-DD of Monday)
    - 'monthly': last 6 months (YYYY-MM)
    """
    now = datetime.now(timezone.utc)
    buckets = []

    if period == "monthly":
        for i in range(5, -1, -1):
            # calculate year and month
            month = (now.month - i - 1) % 12 + 1
            year = now.year + ((now.month - i - 1) // 12)
            buckets.append(f"{year:04d}-{month:02d}")
    elif period == "weekly":
        for i in range(7, -1, -1):
            dt = now - timedelta(weeks=i)
            monday = dt - timedelta(days=dt.weekday())
            buckets.append(monday.strftime("%Y-%m-%d"))
    else:  # daily
        for i in range(13, -1, -1):
            dt = now - timedelta(days=i)
            buckets.append(dt.strftime("%Y-%m-%d"))

    return buckets


def get_start_date_for_period(period: str = "daily") -> datetime:
    """
    Calculates cut-off datetime for the period.
    """
    now = datetime.now(timezone.utc)
    if period == "monthly":
        return now - timedelta(days=185)
    elif period == "weekly":
        return now - timedelta(weeks=9)
    else:  # daily
        return now - timedelta(days=15)


def format_dt_to_bucket(dt: datetime, period: str = "daily") -> str:
    """
    Converts a datetime to a matching bucket string.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if period == "monthly":
        return dt.strftime("%Y-%m")
    elif period == "weekly":
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")
    else:
        return dt.strftime("%Y-%m-%d")
