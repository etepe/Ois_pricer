"""
Model OIS Rate Computation from User Rate Path
================================================
Given a user-specified TCMB rate path (spot + PPK deltas),
computes model OIS swap rates for standard tenors and compares
against market rates.

Method:
    1. Build daily TLREF fixings from rate path
    2. Compound daily to get discount factors
    3. Compute par swap rates for each standard tenor

Short end (≤95 days): Zero coupon → rate = (1/DF - 1) × 365/t × 100
Long end (>95 days):  Par swap   → rate = (1 - DF(T)) / Σ(dcf_i × DF_i) × 100
"""

import calendar as cal
import datetime as dt
from typing import List, Optional

from .calendar import is_business_day, modified_following, load_holidays


# Standard OIS tenors for comparison
STANDARD_TENORS = [
    ("1W",  0, 7),   ("1M",  1, 0),  ("2M",  2, 0),
    ("3M",  3, 0),   ("6M",  6, 0),  ("9M",  9, 0),
    ("1Y",  12, 0),  ("18M", 18, 0), ("2Y",  24, 0),
    ("3Y",  36, 0),  ("4Y",  48, 0), ("5Y",  60, 0),
]


def _add_months(start: dt.date, months: int) -> dt.date:
    m = start.month - 1 + months
    y = start.year + m // 12
    m = m % 12 + 1
    max_day = cal.monthrange(y, m)[1]
    return dt.date(y, m, min(start.day, max_day))


def _tlref_at(d: dt.date, spot_rate: float, meetings: List[dict]) -> float:
    """TLREF level at date d, given spot and meeting deltas."""
    level = spot_rate
    for m in meetings:
        md = m["date"] if isinstance(m["date"], dt.date) else dt.date.fromisoformat(m["date"])
        if md <= d:
            level += m["delta_bps"] / 100.0
        else:
            break
    return level


def _g_factor(d: dt.date, maturity: dt.date, hols: set) -> int:
    """
    Fixing weight: number of calendar days until next business day,
    capped at days to maturity.
    """
    nxt = d
    for _ in range(30):
        nxt += dt.timedelta(days=1)
        if is_business_day(nxt, hols):
            break
    return max(1, min((nxt - d).days, (maturity - d).days))


def _build_daily_df(
    start: dt.date,
    mat: dt.date,
    spot_rate: float,
    meetings: List[dict],
    hols: set,
) -> dict:
    """
    Build daily discount factor map from start to maturity.
    DF(T) = 1 / Π(1 + r_i · g_i / 365), compound on business days only.
    """
    df_map = {start: 1.0}
    compound = 1.0
    cursor = start
    while cursor < mat:
        if is_business_day(cursor, hols):
            r = _tlref_at(cursor, spot_rate, meetings) / 100.0
            g = _g_factor(cursor, mat, hols)
            compound *= 1.0 + r * g / 365.0
        cursor += dt.timedelta(days=1)
        df_map[cursor] = 1.0 / compound
    return df_map


def _quarterly_schedule(start: dt.date, mat: dt.date, hols: set) -> List[dt.date]:
    """3-monthly coupon schedule from start to maturity."""
    coupons = []
    for i in range(1, 200):
        raw = _add_months(start, 3 * i)
        if raw >= mat:
            coupons.append(mat)
            return coupons
        coupons.append(modified_following(raw, hols))
    coupons.append(mat)
    return coupons


def _df_lookup(df_map: dict, target: dt.date) -> float:
    """Lookup DF with ±5 day tolerance."""
    if target in df_map:
        return df_map[target]
    for offset in range(1, 6):
        for d in [target + dt.timedelta(days=offset), target - dt.timedelta(days=offset)]:
            if d in df_map:
                return df_map[d]
    return df_map.get(max(df_map.keys()), 1.0)


def compute_model_rates(
    today: dt.date,
    spot_rate: float,
    meetings: List[dict],
    market_rates: Optional[dict] = None,
    hols: Optional[set] = None,
) -> List[dict]:
    """
    Compute model OIS rates from user rate path.

    Args:
        today: Trade date
        spot_rate: Current TLREF O/N rate (%)
        meetings: [{date, delta_bps}, ...] — PPK decisions
        market_rates: {tenor: rate} — current market for comparison
        hols: Holiday set

    Returns:
        [{tenor, maturity, cal_days, model_rate, market_rate, diff_bps, method}]
    """
    if market_rates is None:
        market_rates = {}
    if hols is None:
        hols = load_holidays()

    start = modified_following(today, hols)
    results = []

    for label, months, days in STANDARD_TENORS:
        if days > 0:
            raw_mat = today + dt.timedelta(days=days)
        else:
            raw_mat = _add_months(today, months)
        mat = modified_following(raw_mat, hols)
        cal_days = (mat - start).days
        if cal_days <= 0:
            continue

        # Build daily DF map
        df_map = _build_daily_df(start, mat, spot_rate, meetings, hols)
        df_T = _df_lookup(df_map, mat)

        if cal_days <= 95:
            model_rate = (1.0 / df_T - 1.0) * 365.0 / cal_days * 100.0
            method = "ZC"
        else:
            coupons = _quarterly_schedule(start, mat, hols)
            annuity = 0.0
            prev = start
            for cpn in coupons:
                dcf = (cpn - prev).days / 365.0
                annuity += dcf * _df_lookup(df_map, cpn)
                prev = cpn
            model_rate = (1.0 - df_T) / annuity * 100.0 if annuity > 0 else float("nan")
            method = "PAR"

        mkt = market_rates.get(label)
        diff = round((model_rate - mkt) * 100, 0) if mkt is not None else None

        results.append({
            "tenor": label,
            "maturity": mat.isoformat(),
            "cal_days": cal_days,
            "model_rate": round(model_rate, 2),
            "market_rate": mkt,
            "diff_bps": diff,
            "method": method,
        })

    return results
