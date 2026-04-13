"""
TLREF OIS Bootstrap Engine

Conventions:
  - Day count: Act/365 (Turkish OIS standard)
  - Settlement: T+1
  - Payment frequency: quarterly (3M) for tenors > 3M
  - Interpolation: log-linear on discount factors
  - Short end (≤ 3M): zero-coupon simple discount
"""

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import List, Set, Optional, Tuple

from .calendar import (
    load_holidays, modified_following, add_business_days,
    is_business_day, next_business_day,
)


@dataclass
class OISQuote:
    tenor: str
    months: int        # 0 for day/week tenors
    days: int          # used only if months == 0
    bid: float         # in % (e.g. 39.60)
    ask: float
    label: str = ""

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


@dataclass
class DFNode:
    """A single bootstrapped discount factor node."""
    days: int          # calendar days from value date
    df: float
    mat_date: dt.date
    tenor: str
    par_rate: float    # par swap rate used (decimal)


@dataclass
class BootstrapResult:
    value_date: dt.date
    trade_date: dt.date
    nodes: List[DFNode]
    holidays: Set[dt.date]

    def get_df(self, days: int) -> float:
        return interpolate_df(self.nodes, days)

    def get_df_at_date(self, target: dt.date) -> float:
        d = (target - self.value_date).days
        return self.get_df(d)

    def zero_rate(self, days: int) -> float:
        """Simple zero rate Act/365."""
        if days <= 0:
            return 0.0
        df = self.get_df(days)
        return (1.0 / df - 1.0) * 365.0 / days

    def forward_rate(self, d1: int, d2: int) -> float:
        """Simple forward rate between d1 and d2 (Act/365)."""
        if d2 <= d1:
            return 0.0
        df1 = self.get_df(d1)
        df2 = self.get_df(d2)
        return (df1 / df2 - 1.0) * 365.0 / (d2 - d1)


# ── Interpolation ────────────────────────────────────────────────────

def interpolate_df(nodes: List[DFNode], target_days: int) -> float:
    """Log-linear interpolation of discount factors."""
    if target_days <= 0:
        return 1.0

    sorted_nodes = sorted(nodes, key=lambda n: n.days)

    # Exact match
    for n in sorted_nodes:
        if n.days == target_days:
            return n.df

    # Bracketing
    lower = sorted_nodes[0]
    upper = sorted_nodes[-1]

    for i in range(len(sorted_nodes) - 1):
        if sorted_nodes[i].days <= target_days <= sorted_nodes[i + 1].days:
            lower = sorted_nodes[i]
            upper = sorted_nodes[i + 1]
            break

    if target_days <= lower.days:
        return lower.df

    if target_days >= upper.days:
        # Flat extrapolation of zero rate
        if upper.days > 0:
            zr = -math.log(upper.df) / upper.days * 365.0
            return math.exp(-zr * target_days / 365.0)
        return 1.0

    # Log-linear
    if upper.days == lower.days:
        return lower.df

    ln_df_l = math.log(lower.df) if lower.df > 0 else -50.0
    ln_df_u = math.log(upper.df) if upper.df > 0 else -50.0
    w = (target_days - lower.days) / (upper.days - lower.days)
    return math.exp(ln_df_l + w * (ln_df_u - ln_df_l))


# ── Maturity date computation ────────────────────────────────────────

def compute_maturity(
    value_date: dt.date,
    months: int,
    days: int,
    hols: Set[dt.date],
) -> dt.date:
    """
    Compute OIS maturity date.
    For month tenors: value_date + N months, modified following.
    For day/week tenors: value_date + N calendar days, modified following.
    """
    if months > 0:
        y = value_date.year
        m = value_date.month + months
        d = value_date.day
        while m > 12:
            m -= 12
            y += 1
        # Handle month-end
        import calendar as cal
        max_day = cal.monthrange(y, m)[1]
        d = min(d, max_day)
        raw = dt.date(y, m, d)
    else:
        raw = value_date + dt.timedelta(days=days)

    return modified_following(raw, hols)


def generate_coupon_schedule(
    value_date: dt.date,
    maturity_date: dt.date,
    hols: Set[dt.date],
) -> List[dt.date]:
    """
    Generate quarterly coupon dates from value_date to maturity_date.
    Every 3 months from value_date, modified following, up to maturity.
    Maturity is always the last date.
    """
    dates = []
    m = 3
    while True:
        cd = compute_maturity(value_date, m, 0, hols)
        if cd >= maturity_date:
            break
        dates.append(cd)
        m += 3

    # Always include maturity as the last date
    dates.append(maturity_date)
    return dates


# ── Bootstrap ────────────────────────────────────────────────────────

def bootstrap(
    quotes: List[OISQuote],
    trade_date: dt.date,
    quote_type: str = "mid",      # "bid", "ask", "mid"
    hols: Optional[Set[dt.date]] = None,
) -> BootstrapResult:
    """
    Bootstrap the TLREF OIS curve.

    Parameters
    ----------
    quotes : list of OISQuote
    trade_date : the trade date (T). Value date = T+1.
    quote_type : which side to use
    hols : holiday set (loaded automatically if None)

    Returns
    -------
    BootstrapResult with all DFNodes and helper methods
    """
    if hols is None:
        hols = load_holidays()

    # T+1 settlement
    value_date = add_business_days(trade_date, 1, hols)

    # Get rate for each quote
    def get_rate(q: OISQuote) -> float:
        if quote_type == "bid":
            return q.bid / 100.0
        elif quote_type == "ask":
            return q.ask / 100.0
        else:
            return q.mid / 100.0

    # Build nodes with maturity dates and rates
    tenor_nodes = []
    for q in quotes:
        mat = compute_maturity(value_date, q.months, q.days, hols)
        d = (mat - value_date).days
        r = get_rate(q)
        tenor_nodes.append({
            "quote": q,
            "mat_date": mat,
            "days": d,
            "rate": r,
        })

    tenor_nodes.sort(key=lambda x: x["days"])

    # Anchor
    df_nodes: List[DFNode] = [
        DFNode(days=0, df=1.0, mat_date=value_date, tenor="T0", par_rate=0.0)
    ]

    # ── Short end (≤ 95 calendar days ≈ 3M) ──────────────────────
    short_end = [t for t in tenor_nodes if t["days"] <= 95]
    for t in short_end:
        df = 1.0 / (1.0 + t["rate"] * t["days"] / 365.0)
        df_nodes.append(DFNode(
            days=t["days"],
            df=df,
            mat_date=t["mat_date"],
            tenor=t["quote"].tenor,
            par_rate=t["rate"],
        ))

    # ── Long end: sequential quarterly bootstrap ────────────────
    # Build a quarterly grid (3M, 6M, 9M, 12M, 15M, 18M, ...).
    # Interpolate par swap rates at intermediate points from market quotes.
    # Bootstrap sequentially: each node uses all previously solved DFs.

    long_end = [t for t in tenor_nodes if t["days"] > 95]
    if long_end:
        long_end.sort(key=lambda x: x["days"])
        max_months = max(t["quote"].months for t in long_end)

        # Market quote lookup: days → par rate (include ALL tenors for interpolation)
        mkt_pts = sorted([(t["days"], t["rate"]) for t in tenor_nodes])

        def interp_par(target_days: int) -> float:
            for d, r in mkt_pts:
                if d == target_days:
                    return r
            for i in range(len(mkt_pts) - 1):
                d0, r0 = mkt_pts[i]
                d1, r1 = mkt_pts[i + 1]
                if d0 <= target_days <= d1:
                    w = (target_days - d0) / (d1 - d0)
                    return r0 + w * (r1 - r0)
            return mkt_pts[-1][1] if target_days > mkt_pts[-1][0] else mkt_pts[0][1]

        # Quarterly grid: accumulate (days, tau, df) tuples
        grid = []  # list of (days, tau, df, mat_date, tenor, par_rate)

        for qm in range(3, max_months + 1, 3):
            mat = compute_maturity(value_date, qm, 0, hols)
            q_days = (mat - value_date).days
            par_r = interp_par(q_days)

            # Previous coupon is either last grid entry or t=0
            prev_d = grid[-1][0] if grid else 0
            tau_n = q_days - prev_d

            # Σ(tau_i * DF_i) over all previous grid entries
            sum_tau_df = sum(g[1] * g[2] for g in grid)

            # Bootstrap formula
            df_n = (1.0 - par_r * sum_tau_df / 365.0) / (1.0 + par_r * tau_n / 365.0)

            # Label: use market tenor name if exact match, else NNM
            tenor_label = f"{qm}M"
            for t in long_end:
                if t["days"] == q_days:
                    tenor_label = t["quote"].tenor
                    break

            grid.append((q_days, tau_n, df_n, mat, tenor_label, par_r))
            df_nodes.append(DFNode(
                days=q_days, df=df_n, mat_date=mat,
                tenor=tenor_label, par_rate=par_r,
            ))

    # Sort and deduplicate
    df_nodes.sort(key=lambda n: n.days)
    unique = []
    for n in df_nodes:
        if not unique or unique[-1].days != n.days:
            unique.append(n)
        else:
            unique[-1] = n  # keep later (longer tenor wins)

    return BootstrapResult(
        value_date=value_date,
        trade_date=trade_date,
        nodes=unique,
        holidays=hols,
    )


# ── Implied PPK extraction ───────────────────────────────────────────

@dataclass
class ImpliedPPK:
    date: dt.date
    days_from_vd: int
    period_days: int
    df: float
    forward_rate: float      # decimal
    implied_rate_pct: float  # percentage

    @property
    def implied_rate_bp(self) -> float:
        return self.implied_rate_pct * 100


def extract_implied_ppk(
    result: BootstrapResult,
    ppk_dates: List[dt.date],
) -> List[ImpliedPPK]:
    """
    Extract market-implied policy rates between consecutive PPK meetings.
    """
    vd = result.value_date
    future_dates = sorted([d for d in ppk_dates if d > vd])

    implied = []
    prev_date = vd
    prev_df = 1.0

    for md in future_dates:
        days = (md - vd).days
        df = result.get_df(days)
        period_days = (md - prev_date).days

        if period_days > 0 and prev_df > 0 and df > 0:
            fwd = (prev_df / df - 1.0) * 365.0 / period_days
            implied.append(ImpliedPPK(
                date=md,
                days_from_vd=days,
                period_days=period_days,
                df=df,
                forward_rate=fwd,
                implied_rate_pct=fwd * 100.0,
            ))

        prev_date = md
        prev_df = df

    return implied


# ── Par rate from DF curve (for scenario recomputation) ──────────────

def par_rate_from_dfs(
    value_date: dt.date,
    maturity_months: int,
    maturity_days: int,
    df_curve_nodes: List[DFNode],
    hols: Set[dt.date],
) -> float:
    """Compute par swap rate from a DF curve for a given tenor."""
    mat = compute_maturity(value_date, maturity_months, maturity_days, hols)
    total_days = (mat - value_date).days

    if total_days <= 95:
        df = interpolate_df(df_curve_nodes, total_days)
        return (1.0 / df - 1.0) * 365.0 / total_days * 100.0

    # Quarterly coupons
    coupon_dates = generate_coupon_schedule(value_date, mat, hols)
    prev_d = 0
    sum_tau_df = 0.0
    last_df = 1.0

    for cd in coupon_dates:
        cd_days = (cd - value_date).days
        tau = cd_days - prev_d
        df = interpolate_df(df_curve_nodes, cd_days)
        sum_tau_df += tau * df
        last_df = df
        prev_d = cd_days

    if sum_tau_df == 0:
        return 0.0

    return (1.0 - last_df) / sum_tau_df * 365.0 * 100.0
