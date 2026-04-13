"""
Turkish financial market holiday calendar.

Sources:
  - `holidays` package (official public holidays)
  - Optional: TCMB tatil takvimi for banking-specific half-days

Caches to JSON on disk so subsequent runs are instant.
"""

import json
import datetime as dt
from pathlib import Path
from typing import Set, Optional

import holidays

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "tr_holidays.json"
DEFAULT_YEAR_RANGE = range(2020, 2036)


def _fetch_holidays(year_range=DEFAULT_YEAR_RANGE) -> dict[str, str]:
    """Fetch Turkish public holidays via the `holidays` library."""
    tr = holidays.Turkey(years=year_range)
    return {d.isoformat(): name for d, name in sorted(tr.items())}


def _load_cache() -> Optional[dict]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_holidays(force_refresh: bool = False) -> Set[dt.date]:
    """
    Return a set of dt.date objects for all Turkish holidays.
    Uses cached JSON if available, otherwise fetches and caches.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return {dt.date.fromisoformat(d) for d in cached.keys()}

    raw = _fetch_holidays()
    _save_cache(raw)
    print(f"[calendar] Cached {len(raw)} holidays to {CACHE_FILE}")
    return {dt.date.fromisoformat(d) for d in raw.keys()}


# ── Business day utilities ────────────────────────────────────────────

def is_business_day(d: dt.date, hols: Set[dt.date]) -> bool:
    return d.weekday() < 5 and d not in hols


def next_business_day(d: dt.date, hols: Set[dt.date]) -> dt.date:
    """Modified following: move forward to next BD."""
    d = d + dt.timedelta(days=1) if not is_business_day(d, hols) else d
    while not is_business_day(d, hols):
        d += dt.timedelta(days=1)
    return d


def add_business_days(d: dt.date, n: int, hols: Set[dt.date]) -> dt.date:
    """Add n business days to date d."""
    count = 0
    current = d
    while count < n:
        current += dt.timedelta(days=1)
        if is_business_day(current, hols):
            count += 1
    return current


def modified_following(d: dt.date, hols: Set[dt.date]) -> dt.date:
    """
    Modified following convention:
    If d is not a BD, roll forward. If rolled into next month, roll backward instead.
    """
    original_month = d.month
    adjusted = d
    while not is_business_day(adjusted, hols):
        adjusted += dt.timedelta(days=1)
    if adjusted.month != original_month:
        adjusted = d
        while not is_business_day(adjusted, hols):
            adjusted -= dt.timedelta(days=1)
    return adjusted


def count_business_days(d1: dt.date, d2: dt.date, hols: Set[dt.date]) -> int:
    """Count business days between d1 (excl) and d2 (incl)."""
    count = 0
    current = d1 + dt.timedelta(days=1)
    while current <= d2:
        if is_business_day(current, hols):
            count += 1
        current += dt.timedelta(days=1)
    return count
