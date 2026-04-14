"""
Implied MPC (PPK) Rate Extraction
==================================
Extracts market-implied policy rate expectations between
consecutive TCMB PPK (Monetary Policy Committee) meetings
from the OIS curve.

Forward rate (daily compounding, annualized):
    fwd = (GU(t2)/GU(t1))^(1/period) - 1) × 36500

Implied MPC (simple interest equivalent):
    mpc = ((1 + fwd/36500)^period - 1) / period × 36500
"""

import datetime as dt
from typing import List
from dataclasses import dataclass

from .bootstrap import DFNode, BootstrapResult, interpolate_df
from .calendar import add_business_days


DAY_CONV_X100 = 36_500  # 365 × 100


@dataclass
class ImpliedMPC:
    """Single PPK meeting implied rate."""
    ppk_date: dt.date
    dtm_from_spot: int
    period_days: int
    forward_rate: float      # daily compounding, annualized %
    implied_mpc: float       # simple interest equivalent %
    df: float


def calc_implied_mpc(
    ppk_dates: List[dt.date],
    bootstrap_result: BootstrapResult,
) -> List[ImpliedMPC]:
    """
    Calculate implied MPC rates between PPK meetings.

    Uses the bootstrapped OIS curve to extract forward rates
    between consecutive meeting dates.

    Args:
        ppk_dates: List of PPK meeting dates
        bootstrap_result: Bootstrapped OIS curve result

    Returns:
        List of ImpliedMPC for each future meeting
    """
    vd = bootstrap_result.value_date
    nodes = bootstrap_result.nodes

    results = []
    prev_dtm = 0
    prev_gu = 1.0  # at spot: df=1 → gross_up=1

    for ppk_date in sorted(ppk_dates):
        if ppk_date <= vd:
            continue

        dtm = (ppk_date - vd).days
        df = interpolate_df(nodes, dtm)
        gu = 1.0 / df if df > 0 else 1.0

        period = dtm - prev_dtm
        if period <= 0:
            continue

        # Forward rate (daily compounding, annualized %)
        if prev_gu > 0:
            fwd = ((gu / prev_gu) ** (1.0 / period) - 1.0) * DAY_CONV_X100
        else:
            fwd = 0.0

        # Implied MPC (simple interest equivalent, annualized %)
        mpc = ((1.0 + fwd / DAY_CONV_X100) ** period - 1.0) / period * DAY_CONV_X100

        results.append(ImpliedMPC(
            ppk_date=ppk_date,
            dtm_from_spot=dtm,
            period_days=period,
            forward_rate=round(fwd, 2),
            implied_mpc=round(mpc, 2),
            df=round(df, 8),
        ))

        prev_dtm = dtm
        prev_gu = gu

    return results


def build_mpc_path(
    ppk_dates: List[dt.date],
    bootstrap_result: BootstrapResult,
    spot_rate: float,
) -> dict:
    """
    Build slider-friendly MPC path for frontend.

    Returns:
        {
            "spot_rate": float,
            "meetings": [{
                "date": str,
                "implied_rate": float,
                "implied_delta_bps": int,
                "period_days": int,
            }]
        }
    """
    implied = calc_implied_mpc(ppk_dates, bootstrap_result)

    meetings = []
    prev_rate = spot_rate

    for m in implied:
        raw_delta = m.implied_mpc - prev_rate
        rounded_delta = round(raw_delta * 100 / 25) * 25  # round to 25 bps

        meetings.append({
            "date": m.ppk_date.isoformat(),
            "implied_rate": round(m.implied_mpc, 2),
            "implied_delta_bps": int(rounded_delta),
            "period_days": m.period_days,
        })

        prev_rate = m.implied_mpc

    return {
        "spot_rate": round(spot_rate, 2),
        "meetings": meetings,
    }
