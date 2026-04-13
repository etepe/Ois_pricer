"""
Web Arayüzü — Flask Server
============================
OIS eğrisi, TLREF spread ve implied MPC verilerini
REST endpoint olarak sunar + dashboard sayfasını serve eder.

Kullanım:
    python web.py              # Bloomberg ile
    python web.py --mock       # Mock data ile (test)

Tarayıcıda: http://localhost:5000
"""
import sys
import json
import logging
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from config import PPK_DATES
from data_provider import BloombergProvider, MockProvider
from engine import bootstrap_onshore, analyze_tlref_bonds, calc_implied_mpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("web")

app = Flask(__name__, static_folder="static")

# ── Global state ──
_state = {
    "ois_base": None,
    "market": None,
    "tlref_results": None,
    "mpc_results": None,
    "last_update": None,
    "provider": None,
}

TLREF_ISINS = [
    "TRT140127T13",
    "TRT150727T11",
    "TRT140128T11",
]


def _serialize_df(df: pd.DataFrame) -> list[dict]:
    """DataFrame → JSON-serializable list."""
    result = []
    for _, row in df.iterrows():
        d = {}
        for col in df.columns:
            val = row[col]
            if isinstance(val, (date, datetime)):
                d[col] = val.isoformat()
            elif isinstance(val, (np.integer,)):
                d[col] = int(val)
            elif isinstance(val, (np.floating,)):
                d[col] = round(float(val), 8) if not np.isnan(val) else None
            elif isinstance(val, float) and np.isnan(val):
                d[col] = None
            else:
                d[col] = val
        result.append(d)
    return result


def refresh_data():
    """Tüm verileri yeniden hesaplar."""
    today = date.today()
    provider = _state["provider"]

    log.info(f"Veri yenileniyor... ({today})")

    market = provider.get_onshore_ois(today)
    ois_base = bootstrap_onshore(market)

    bonds_df = provider.get_tlref_bonds(TLREF_ISINS, today)
    tlref_results = pd.DataFrame()
    if len(bonds_df) > 0:
        tlref_results = analyze_tlref_bonds(bonds_df, ois_base, today)

    mpc_results = calc_implied_mpc(PPK_DATES, ois_base, today)

    _state["market"] = market
    _state["ois_base"] = ois_base
    _state["tlref_results"] = tlref_results
    _state["mpc_results"] = mpc_results
    _state["last_update"] = datetime.now().isoformat()

    log.info(f"Güncellendi: {len(ois_base)} grid, "
             f"{len(tlref_results)} tahvil, {len(mpc_results)} PPK")


# ═══════════════════════════════════════════════════════════════════
#  REST Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "last_update": _state["last_update"],
        "today": date.today().isoformat(),
        "bisttref": _state["market"].bisttref_rate if _state["market"] else None,
        "grid_size": len(_state["ois_base"]) if _state["ois_base"] is not None else 0,
    })


@app.route("/api/curve")
def api_curve():
    if _state["ois_base"] is None:
        return jsonify({"error": "Veri yok"}), 503
    return jsonify(_serialize_df(_state["ois_base"]))


@app.route("/api/lookup")
def api_lookup():
    """Belirli bir DTM için interpolasyon ile rate ve df döndürür."""
    if _state["ois_base"] is None:
        return jsonify({"error": "Veri yok"}), 503

    dtm = request.args.get("dtm", type=float)
    if dtm is None:
        return jsonify({"error": "dtm parametresi gerekli"}), 400

    ois = _state["ois_base"]
    ois_dtm = ois["DTM"].values.astype(float)

    rate = float(np.interp(dtm, ois_dtm, ois["spot_ois"].values))
    df_val = float(np.interp(dtm, ois_dtm, ois["df"].values))
    gross_up = 1.0 / df_val if df_val > 0 else None

    # Zero coupon rate
    if dtm > 0 and df_val > 0:
        zc_rate = (gross_up - 1.0) / dtm * 36500
    else:
        zc_rate = rate

    return jsonify({
        "dtm": dtm,
        "spot_ois": round(rate, 4),
        "df": round(df_val, 8),
        "gross_up": round(gross_up, 8) if gross_up else None,
        "zc_rate": round(zc_rate, 4),
    })


@app.route("/api/spreads")
def api_spreads():
    if _state["tlref_results"] is None or len(_state["tlref_results"]) == 0:
        return jsonify([])
    return jsonify(_serialize_df(_state["tlref_results"]))


@app.route("/api/mpc")
def api_mpc():
    if _state["mpc_results"] is None:
        return jsonify([])
    return jsonify(_serialize_df(_state["mpc_results"]))


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    try:
        refresh_data()
        return jsonify({"status": "ok", "last_update": _state["last_update"]})
    except Exception as e:
        log.error(f"Refresh hatası: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    use_mock = "--mock" in sys.argv

    if use_mock:
        _state["provider"] = MockProvider()
        log.info("MockProvider (test modu)")
    else:
        _state["provider"] = BloombergProvider()
        log.info("Bloomberg bağlantısı")

    refresh_data()

    port = 5000
    log.info(f"Dashboard: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
