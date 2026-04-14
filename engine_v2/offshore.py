"""
Offshore TRY (TRYI) Curve Processing
=====================================
Offshore curve uses Act/360 convention with directly observed discount factors.
No bootstrap needed — DFs come directly from Bloomberg.
"""

import math
import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional

from .bootstrap import DFNode, interpolate_df


@dataclass
class OffshoreQuote:
    """Single offshore TRYI deposit rate quote."""
    tenor: str
    days: int          # calendar days from spot
    rate: float        # deposit rate in % (e.g. 31.75)
    df: float          # observed discount factor
    ticker: str = ""


@dataclass
class OffshoreResult:
    """Offshore curve result with interpolation helpers."""
    value_date: dt.date
    nodes: List[DFNode]
    day_count: int = 360  # Act/360

    def get_df(self, days: int) -> float:
        return interpolate_df(self.nodes, days)

    def zero_rate(self, days: int) -> float:
        """Simple zero rate Act/360."""
        if days <= 0:
            return 0.0
        df = self.get_df(days)
        return (1.0 / df - 1.0) * float(self.day_count) / days

    def forward_rate(self, d1: int, d2: int) -> float:
        """Simple forward rate between d1 and d2 (Act/360)."""
        if d2 <= d1:
            return 0.0
        df1 = self.get_df(d1)
        df2 = self.get_df(d2)
        return (df1 / df2 - 1.0) * float(self.day_count) / (d2 - d1)


def build_offshore_curve(
    quotes: List[OffshoreQuote],
    value_date: dt.date,
) -> OffshoreResult:
    """
    Build offshore TRY curve from TRYI deposit rate quotes.

    DFs are directly observed (no bootstrap), but we recompute them
    from rates for consistency: df = 1 / (1 + rate/100 * days/360).
    """
    nodes = [DFNode(days=0, df=1.0, mat_date=value_date, tenor="T0", par_rate=0.0)]

    for q in quotes:
        if q.days <= 0:
            continue
        # Use observed DF if available and positive, otherwise compute
        if q.df > 0 and q.df < 1.0:
            df = q.df
        else:
            df = 1.0 / (1.0 + q.rate / 100.0 * q.days / 360.0)

        mat = value_date + dt.timedelta(days=q.days)
        nodes.append(DFNode(
            days=q.days,
            df=df,
            mat_date=mat,
            tenor=q.tenor,
            par_rate=q.rate / 100.0,
        ))

    nodes.sort(key=lambda n: n.days)
    return OffshoreResult(value_date=value_date, nodes=nodes)


def compute_basis(
    onshore_nodes: List[DFNode],
    offshore_result: OffshoreResult,
    tenors_days: List[int],
) -> List[dict]:
    """
    Compute onshore-offshore basis at given tenor points.

    Returns list of {days, onshore_zr, offshore_zr, basis_bps}.
    Basis = Offshore - Onshore (positive = offshore premium).
    """
    results = []
    for d in tenors_days:
        if d <= 0:
            continue
        ois_df = interpolate_df(onshore_nodes, d)
        off_df = offshore_result.get_df(d)

        ois_zr = (1.0 / ois_df - 1.0) * 365.0 / d * 100.0 if ois_df > 0 else 0.0
        off_zr = (1.0 / off_df - 1.0) * 360.0 / d * 100.0 if off_df > 0 else 0.0

        results.append({
            "days": d,
            "onshore_zr": round(ois_zr, 4),
            "offshore_zr": round(off_zr, 4),
            "basis_bps": round((off_zr - ois_zr) * 100, 1),
        })

    return results
