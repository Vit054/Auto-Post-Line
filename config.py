"""Shared config: timezone + Thai lucky-color theme per day of week."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Bangkok")

# Thai lucky color of the day. weekday(): Monday=0 ... Sunday=6
THEMES = {
    0: {"day": "Monday",    "color": "#F6C700", "accent": "#FFE680",
        "flowers": "bright yellow daisies and chrysanthemums"},
    1: {"day": "Tuesday",   "color": "#FF6FA5", "accent": "#FFB6D2",
        "flowers": "soft pink roses and pink cosmos"},
    2: {"day": "Wednesday", "color": "#34B233", "accent": "#9FE08D",
        "flowers": "fresh green foliage with small white blossoms"},
    3: {"day": "Thursday",  "color": "#FF8C1A", "accent": "#FFC487",
        "flowers": "warm orange marigolds"},
    4: {"day": "Friday",    "color": "#1FA7E0", "accent": "#9BD8F5",
        "flowers": "sky-blue hydrangeas and forget-me-nots"},
    5: {"day": "Saturday",  "color": "#7E57C2", "accent": "#C3A6E8",
        "flowers": "purple lavender and violets"},
    6: {"day": "Sunday",    "color": "#E53935", "accent": "#F5A3A1",
        "flowers": "deep red roses"},
}


def today():
    """Return (now_in_bangkok, theme_for_today)."""
    now = datetime.now(TZ)
    return now, THEMES[now.weekday()]
