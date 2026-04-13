"""
Ana Orkestrasyon
================
Bloomberg'den veri çek → OIS bootstrap → TLREF spread → Implied MPC

Kullanım:
    python main.py              # Bloomberg ile (şirkette)
    python main.py --mock       # Mock data ile (test)
"""
import sys
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config import PPK_DATES, OUTPUT_DIR
from data_provider import BloombergProvider, MockProvider
from engine import bootstrap_onshore, analyze_tlref_bonds, calc_implied_mpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ois_pricer")

# ── Örnek TLREF ISIN listesi (ihtiyaca göre güncelle) ──
TLREF_ISINS = [
    "TRT140127T13",
    "TRT150727T11",
    "TRT140128T11",
]


def run(use_mock: bool = False, today: date = None):
    """Ana hesaplama."""

    if today is None:
        today = date.today()

    log.info("=" * 60)
    log.info(f"OIS Pricer — {today}")
    log.info("=" * 60)

    # ── 1) Veri kaynağı seç ──
    if use_mock:
        provider = MockProvider()
        log.info("MockProvider kullanılıyor (test modu)")
    else:
        provider = BloombergProvider()
        log.info("Bloomberg bağlantısı kullanılıyor")

    # ── 2) OIS piyasa verileri ──
    market = provider.get_onshore_ois(today)
    log.info(f"BISTTREF O/N = {market.bisttref_rate:.2f}%")
    log.info(f"OIS tenor sayısı: {len(market.tickers)}")

    # ── 3) Bootstrap ──
    ois_base = bootstrap_onshore(market)
    log.info(f"Grid: {len(ois_base)} satır")
    log.info(f"  3M df = {ois_base.iloc[4]['df']:.6f}")
    log.info(f"  1Y df = {ois_base[ois_base['label'] == '1Y'].iloc[0]['df']:.6f}")
    log.info(f" 10Y df = {ois_base.iloc[-1]['df']:.6f}")

    # ── 4) TLREF spread ──
    bonds_df = provider.get_tlref_bonds(TLREF_ISINS, today)
    tlref_results = pd.DataFrame()
    if len(bonds_df) > 0:
        log.info(f"TLREF spread: {len(bonds_df)} tahvil")
        tlref_results = analyze_tlref_bonds(bonds_df, ois_base, today)
        for _, row in tlref_results.iterrows():
            log.info(f"  {row['isin']}  DTM={row['DTM']:>4d}  "
                     f"spread={row['ois_spread_bps']:>+7.1f} bps")

    # ── 5) Implied MPC ──
    log.info("Implied MPC hesaplanıyor...")
    mpc_results = calc_implied_mpc(PPK_DATES, ois_base, today)
    for _, row in mpc_results.iterrows():
        log.info(f"  PPK {row['ppk_date']}  "
                 f"fwd={row['forward_rate']:>6.2f}%  "
                 f"mpc={row['implied_mpc']:>6.2f}%")

    # ── 6) Sonuçları kaydet ──
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    out_file = out_dir / f"ois_pricer_{ts}.xlsx"
    with pd.ExcelWriter(out_file, engine="openpyxl") as w:
        ois_base.to_excel(w, sheet_name="OIS_Curve", index=False)
        if len(tlref_results) > 0:
            tlref_results.to_excel(w, sheet_name="TLREF_Spreads", index=False)
        mpc_results.to_excel(w, sheet_name="Implied_MPC", index=False)

    log.info(f"Sonuçlar: {out_file}")
    log.info("Tamamlandı.")

    return ois_base, tlref_results, mpc_results


if __name__ == "__main__":
    use_mock = "--mock" in sys.argv
    run(use_mock=use_mock)
