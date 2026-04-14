"""
TLREF Bond Spread Calculation
==============================
Calculates OIS Z-spread and offshore Z-spread for TLREF bonds.
Adapted from engine.py to work with engine_v2 BootstrapResult.

Bond types:
  - ZCB (zero coupon): df = price / 100
  - FLT (TLREF-linked floating): forward coupons from OIS curve
  - FIX (fixed coupon): known coupon stream

Z-spread: parallel shift to the discount curve that equates
model PV to market dirty price. Solved via Brent's method.
"""

import math
import datetime as dt
from typing import List, Optional
from dataclasses import dataclass

from scipy.optimize import brentq

from .bootstrap import DFNode, interpolate_df


TLREF_CPN_PERIOD = 91   # quarterly coupon, days
FIXED_CPN_PERIOD = 182  # semi-annual coupon, days


@dataclass
class BondInput:
    """Bond specification for pricing."""
    isin: str
    maturity: str        # ISO date string
    coupon: float        # annual coupon rate (%)
    freq: int            # 0=ZCB, 2=semi, 4=quarterly
    px_last: float       # last/dirty price
    bond_type: str       # "zcb", "flt", "fix"


@dataclass
class BondResult:
    """Pricing result for a single bond."""
    isin: str
    maturity: str
    bond_type: str
    days_to_mat: int
    coupon: float
    px_last: float
    model_pv_ois: float
    zspread_ois: float       # basis points
    zspread_offshore: float  # basis points
    basis_delta_bps: float   # offshore - onshore spread difference
    yield_ois: float         # zero rate + OIS z-spread


def _generate_coupon_dates(
    value_date: dt.date,
    maturity: dt.date,
    period_months: int,
) -> List[int]:
    """
    Generate coupon dates as days-from-value-date.
    Works backward from maturity in period_months steps.
    """
    dates_days = []
    cursor = maturity

    while True:
        d = (cursor - value_date).days
        if d <= 0:
            break
        dates_days.append(d)
        # Step back by period_months
        m = cursor.month - period_months
        y = cursor.year
        while m < 1:
            m += 12
            y -= 1
        import calendar as cal
        max_day = cal.monthrange(y, m)[1]
        cursor = dt.date(y, m, min(cursor.day, max_day))

    dates_days.sort()
    return dates_days


def _generate_cashflows(
    bond: BondInput,
    value_date: dt.date,
    ois_nodes: List[DFNode],
) -> List[dict]:
    """
    Generate cashflow schedule for a bond.

    Returns list of {days, cf} where cf is the cashflow amount per 100 face.
    """
    mat = dt.date.fromisoformat(bond.maturity)
    dtm = (mat - value_date).days
    if dtm <= 0:
        return []

    # Zero coupon bond
    if bond.freq == 0 or bond.coupon == 0:
        return [{"days": dtm, "cf": 100.0}]

    # Determine coupon period
    period_months = 3 if bond.freq == 4 else 6
    dates = _generate_coupon_dates(value_date, mat, period_months)
    if not dates:
        return [{"days": dtm, "cf": 100.0}]

    cfs = []
    if bond.bond_type == "flt":
        # Floating (TLREF-linked): forward rate coupons
        for i, d in enumerate(dates):
            prev_d = dates[i - 1] if i > 0 else 0
            df_prev = interpolate_df(ois_nodes, prev_d)
            df_curr = interpolate_df(ois_nodes, d)
            if df_curr > 0:
                forward_cpn = (df_prev / df_curr - 1.0) * 100.0
            else:
                forward_cpn = 0.0
            cf = forward_cpn + 100.0 if i == len(dates) - 1 else forward_cpn
            cfs.append({"days": d, "cf": cf})
    else:
        # Fixed coupon
        cpn_per_period = bond.coupon / bond.freq
        for i, d in enumerate(dates):
            cf = cpn_per_period + 100.0 if i == len(dates) - 1 else cpn_per_period
            cfs.append({"days": d, "cf": cf})

    return cfs


def _solve_zspread(
    cashflows: List[dict],
    nodes: List[DFNode],
    target_price: float,
    day_count: int = 365,
) -> float:
    """
    Solve for Z-spread (in decimal) that equates PV of cashflows to target price.

    Z-spread is applied as a parallel shift to the zero rate:
        df_shifted(t) = exp(-(zr(t) + z) * t / day_count)

    Returns spread in decimal (multiply by 10000 for bps).
    """
    def pv_at_spread(z: float) -> float:
        total = 0.0
        for cf in cashflows:
            d = cf["days"]
            if d <= 0:
                continue
            base_df = interpolate_df(nodes, d)
            if base_df <= 0:
                continue
            # Convert DF to zero rate, add spread, convert back
            zr = -math.log(base_df) / d * day_count
            shifted_df = math.exp(-(zr + z) * d / day_count)
            total += cf["cf"] * shifted_df
        return total

    def objective(z: float) -> float:
        return pv_at_spread(z) - target_price

    try:
        spread = brentq(objective, -0.50, 0.50, xtol=1e-10, maxiter=200)
        return spread
    except (ValueError, RuntimeError):
        return float("nan")


def price_bonds(
    bonds: List[BondInput],
    ois_nodes: List[DFNode],
    offshore_nodes: List[DFNode],
    value_date: dt.date,
) -> List[BondResult]:
    """
    Price a list of bonds and compute OIS and offshore Z-spreads.

    Args:
        bonds: List of BondInput specifications
        ois_nodes: Onshore OIS bootstrapped DF nodes
        offshore_nodes: Offshore TRYI DF nodes
        value_date: Settlement/value date

    Returns:
        List of BondResult sorted by days to maturity
    """
    results = []

    for bond in bonds:
        mat = dt.date.fromisoformat(bond.maturity)
        dtm = (mat - value_date).days
        if dtm <= 0:
            continue

        # Generate cashflows (floating uses OIS curve for forwards)
        cfs = _generate_cashflows(bond, value_date, ois_nodes)
        if not cfs:
            continue

        # Model PV using OIS curve (no spread)
        model_pv = sum(
            cf["cf"] * interpolate_df(ois_nodes, cf["days"])
            for cf in cfs if cf["days"] > 0
        )

        # OIS Z-spread (Act/365)
        zs_ois = _solve_zspread(cfs, ois_nodes, bond.px_last, 365)
        zs_ois_bps = round(zs_ois * 10000, 1) if math.isfinite(zs_ois) else float("nan")

        # Offshore Z-spread (Act/360)
        # For floating bonds, we still use OIS forwards for coupons
        zs_off = _solve_zspread(cfs, offshore_nodes, bond.px_last, 360)
        zs_off_bps = round(zs_off * 10000, 1) if math.isfinite(zs_off) else float("nan")

        # Basis delta
        if math.isfinite(zs_ois_bps) and math.isfinite(zs_off_bps):
            basis_delta = round(zs_ois_bps - zs_off_bps, 1)
        else:
            basis_delta = float("nan")

        # Yield = zero rate + z-spread
        ois_zr = 0.0
        if dtm > 0:
            df_at_mat = interpolate_df(ois_nodes, dtm)
            if df_at_mat > 0:
                ois_zr = (1.0 / df_at_mat - 1.0) * 365.0 / dtm * 100.0

        yield_ois = round(ois_zr + (zs_ois * 100 if math.isfinite(zs_ois) else 0), 2)

        results.append(BondResult(
            isin=bond.isin,
            maturity=bond.maturity,
            bond_type=bond.bond_type,
            days_to_mat=dtm,
            coupon=bond.coupon,
            px_last=bond.px_last,
            model_pv_ois=round(model_pv, 4),
            zspread_ois=zs_ois_bps,
            zspread_offshore=zs_off_bps,
            basis_delta_bps=basis_delta,
            yield_ois=yield_ois,
        ))

    results.sort(key=lambda r: r.days_to_mat)
    return results
