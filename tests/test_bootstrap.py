"""
Bootstrap Doğrulama
====================
13 Nisan 2026 piyasa verileriyle (Bloomberg ekranından) OIS bootstrap'ı test eder.

Kontrol noktaları:
    1. Grid 44 satır (index 0–43)
    2. df monoton azalan, (0, 1] aralığında
    3. df[0] = 1.0 (bugün)
    4. Kısa vade (Bölge 2): basit faiz doğrulaması
    5. Uzun vade (Bölge 3): swap par rate reproduksiyon
    6. TLREF spread mantıklı aralıkta
    7. Implied MPC indirim patikası tutarlı
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
import numpy as np
import pandas as pd

from config import PPK_DATES, DAY_CONV_X100
from data_provider import MockProvider, add_bdays
from engine import (
    build_onshore_grid,
    bootstrap_onshore,
    calc_tlref_spread,
    analyze_tlref_bonds,
    calc_implied_mpc,
)

TODAY = date(2026, 4, 13)
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

all_passed = True


def check(condition: bool, msg: str):
    global all_passed
    if condition:
        print(f"  {PASS} {msg}")
    else:
        print(f"  {FAIL} {msg}")
        all_passed = False


def test_grid():
    """Tarih gridi doğrulama."""
    print("\n── 1) Tarih Gridi ──")

    grid = build_onshore_grid(TODAY)

    check(len(grid) == 44, f"44 satır (bulunan: {len(grid)})")
    check(grid.iloc[0]["date"] == TODAY, f"Row 0 = bugün ({TODAY})")
    check(grid.iloc[0]["DTM"] == 0, "Row 0 DTM = 0")
    check(grid.iloc[0]["period"] == 0, "Row 0 period = 0")

    # O/N = bugün + 1BD = 14.04.2026 (Salı)
    on_date = grid.iloc[1]["date"]
    check(on_date == date(2026, 4, 14), f"Row 1 O/N = 14.04.2026 (bulunan: {on_date})")
    check(grid.iloc[1]["DTM"] == 1, "Row 1 DTM = 1")

    # 1W = 13.04 + 1W = 20.04 (Pzt) + 1BD = 21.04 (Sal)
    w1_date = grid.iloc[2]["date"]
    check(w1_date == date(2026, 4, 21), f"Row 2 1W = 21.04.2026 (bulunan: {w1_date})")

    # 1M = 13.04 + 1M = 13.05 (Çar) + 1BD = 14.05 (Per)
    m1_date = grid.iloc[3]["date"]
    check(m1_date == date(2026, 5, 14), f"Row 3 1M = 14.05.2026 (bulunan: {m1_date})")

    # 3M = ilk quarterly node (Row 4)
    m3_date = grid.iloc[4]["date"]
    check(grid.iloc[4]["label"] == "3M", f"Row 4 label = 3M")
    # 13.04 + 3M = 13.07.2026 (Pzt) + 1BD = 14.07.2026 (Sal)
    check(m3_date == date(2026, 7, 14), f"Row 4 3M = 14.07.2026 (bulunan: {m3_date})")

    # Son satır = 10Y (Row 43)
    check(grid.iloc[43]["label"] == "10Y", f"Row 43 label = 10Y")

    # Quarterly grid: Row 4'ten itibaren her 3 ayda bir
    for i in range(4, 44):
        expected_months = 3 * (i - 3)  # Row 4 = 3M, Row 5 = 6M, ...
        check(
            grid.iloc[i]["label"] in [f"{expected_months}M", f"{expected_months // 12}Y"],
            f"Row {i}: {grid.iloc[i]['label']} ({expected_months}M)"
        ) if expected_months % 12 != 0 else None

    return grid


def test_bootstrap():
    """OIS bootstrap doğrulama."""
    print("\n── 2) OIS Bootstrap ──")

    provider = MockProvider()
    market = provider.get_onshore_ois(TODAY)
    ois = bootstrap_onshore(market)

    check(len(ois) == 44, f"44 satır (bulunan: {len(ois)})")

    # df[0] = 1.0
    check(ois.iloc[0]["df"] == 1.0, "df[0] = 1.0")

    # Tüm df > 0
    check(all(ois["df"] > 0), "Tüm df > 0")

    # Tüm df ≤ 1
    check(all(ois["df"] <= 1.0), "Tüm df ≤ 1")

    # df monoton azalan (Row 1'den itibaren)
    dfs = ois["df"].values[1:]
    check(all(dfs[i] >= dfs[i + 1] for i in range(len(dfs) - 1)),
          "df monoton azalan")

    # ── Bölge 2 doğrulama: basit faiz ──
    print("\n  Bölge 2 (kısa vade — basit faiz):")
    for i in range(1, 5):
        dtm = ois.iloc[i]["DTM"]
        rate = ois.iloc[i]["spot_ois"]
        df_calc = 1.0 / (1.0 + rate * dtm / DAY_CONV_X100)
        df_actual = ois.iloc[i]["df"]
        diff = abs(df_calc - df_actual)
        check(diff < 1e-12,
              f"  {ois.iloc[i]['label']:>4s}  DTM={dtm:>3.0f}  "
              f"rate={rate:>6.2f}%  df={df_actual:.8f}  (fark={diff:.1e})")

    # ── Bölge 3: swap par rate reproduksiyon ──
    print("\n  Bölge 3 (uzun vade — swap bootstrap):")
    # 6M swap: par rate = spot_ois[6M]
    # Fixed leg = S × (df(3M)×period(3M→0) + df(6M)×period(6M→3M)) / 36500
    # Float leg = 1 − df(6M)
    for idx, label in [(5, "6M"), (6, "9M"), (7, "1Y"), (11, "2Y"), (43, "10Y")]:
        row = ois.iloc[idx]
        rate = row["spot_ois"]
        df_n = row["df"]

        # Swap PV hesapla: fixed = Σ df[j] × period[j] × S / 36500
        fixed_pv = 0.0
        for j in range(4, idx + 1):  # 3M'den itibaren
            fixed_pv += ois.iloc[j]["df"] * ois.iloc[j]["period"]
        fixed_pv *= rate / DAY_CONV_X100

        float_pv = 1.0 - df_n
        error = abs(fixed_pv - float_pv)
        check(error < 1e-8,
              f"  {label:>4s}  rate={rate:>6.2f}%  "
              f"fixed={fixed_pv:.8f}  float={float_pv:.8f}  "
              f"hata={error:.2e}")

    # ── Grid özeti yazdır ──
    print("\n  Grid özeti:")
    key_rows = [0, 1, 2, 3, 4, 5, 6, 7, 9, 11, 15, 19, 23, 31, 43]
    for i in key_rows:
        r = ois.iloc[i]
        print(f"    {r['label']:>4s}  {r['date']}  DTM={r['DTM']:>5.0f}  "
              f"rate={r['spot_ois']:>6.2f}%  df={r['df']:.6f}  "
              f"SumProd={r['SumProduct']:>10.4f}")

    return ois


def test_tlref_spread(ois):
    """TLREF spread doğrulama."""
    print("\n── 3) TLREF Spread ──")

    provider = MockProvider()
    bonds = provider.get_tlref_bonds(
        ["TRT140127T13", "TRT150727T11", "TRT140128T11"], TODAY
    )
    results = analyze_tlref_bonds(bonds, ois, TODAY)

    for _, row in results.iterrows():
        is_valid = not np.isnan(row["ois_spread_bps"])
        in_range = is_valid and -500 < row["ois_spread_bps"] < 500
        check(is_valid and in_range,
              f"{row['isin']}  DTM={row['DTM']:>4d}  "
              f"next_cpn={row['dt_next_cpn']:>3d}d  "
              f"dirty={row['px_last']:>7.2f}  "
              f"spread={row['ois_spread_bps']:>+7.1f} bps")

    return results


def test_implied_mpc(ois):
    """Implied MPC doğrulama."""
    print("\n── 4) Implied MPC ──")

    mpc = calc_implied_mpc(PPK_DATES, ois, TODAY)

    check(len(mpc) > 0, f"{len(mpc)} PPK toplantısı")
    check(all(mpc["implied_mpc"] > 0), "Tüm implied MPC > 0")
    check(all(mpc["implied_mpc"] < 60), "Tüm implied MPC < 60%")

    for _, row in mpc.iterrows():
        print(f"    PPK {row['ppk_date']}  period={row['period_days']:>3d}d  "
              f"fwd={row['forward_rate']:>6.2f}%  "
              f"mpc={row['implied_mpc']:>6.2f}%")

    return mpc


def test_sumproduct_transition():
    """SumProduct Bölge 2→3 geçiş doğrulaması."""
    print("\n── 5) SumProduct Geçiş Kontrolü ──")

    provider = MockProvider()
    market = provider.get_onshore_ois(TODAY)
    ois = bootstrap_onshore(market)

    # Row 4 (3M) — son Bölge 2 satırı
    # SumProduct[5] = df[4] × DTM[4] (overwrite)
    df_3m = ois.iloc[4]["df"]
    dtm_3m = ois.iloc[4]["DTM"]
    expected_sp5 = df_3m * dtm_3m
    actual_sp5 = ois.iloc[5]["SumProduct"]
    check(abs(expected_sp5 - actual_sp5) < 1e-12,
          f"SumProduct[5] = df(3M)×DTM(3M) = {df_3m:.8f}×{dtm_3m:.0f} "
          f"= {expected_sp5:.6f}  (actual: {actual_sp5:.6f})")

    # Row 5 (6M) → Row 6 (9M): accumulate
    # SumProduct[6] = SumProduct[5] + df[5] × period[5]
    df_6m = ois.iloc[5]["df"]
    period_6m = ois.iloc[5]["period"]
    expected_sp6 = actual_sp5 + df_6m * period_6m
    actual_sp6 = ois.iloc[6]["SumProduct"]
    check(abs(expected_sp6 - actual_sp6) < 1e-12,
          f"SumProduct[6] = SP[5] + df(6M)×period(6M) = {expected_sp6:.6f}  "
          f"(actual: {actual_sp6:.6f})")


if __name__ == "__main__":
    print("=" * 60)
    print(f"OIS Pricer — Test Suite ({TODAY})")
    print("=" * 60)

    grid = test_grid()
    ois = test_bootstrap()
    spreads = test_tlref_spread(ois)
    mpc = test_implied_mpc(ois)
    test_sumproduct_transition()

    print("\n" + "=" * 60)
    if all_passed:
        print(f"{PASS}  TÜM TESTLER BAŞARILI")
    else:
        print(f"{FAIL}  BAZI TESTLER BAŞARISIZ")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
