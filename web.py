"""
Web Arayuzu - Flask Server
============================
OIS egrisi, offshore TRYI, TLREF spread, implied MPC, model rates.
Real-time guncelleme: Bloomberg subscription (birincil) veya 5dk polling (fallback).

Kullanim:
    python web.py              # Bloomberg ile
    python web.py --mock       # Mock data ile (test)
    python web.py --mock --poll  # Mock + polling fallback

Tarayicida: http://localhost:5000
"""
import sys
import json
import math
import logging
import threading
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, Response

from config import (
    PPK_DATES, BOND_UNIVERSE, ONSHORE_OIS_TICKERS,
    OFFSHORE_TRYI_TICKERS, POLLING_INTERVAL_SEC,
)
from data_provider import BloombergProvider, MockProvider
from engine_v2 import (
    OISQuote, bootstrap, load_holidays, add_business_days,
    build_offshore_curve, OffshoreQuote,
    price_bonds, BondInput,
    calc_implied_mpc, build_mpc_path,
    compute_model_rates, interpolate_df, compute_basis,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("web")

app = Flask(__name__, static_folder="static")

# -- Global state --
_state = {
    "provider": None,
    "market": None,
    "offshore": None,
    "bond_prices": None,
    "bootstrap": None,
    "offshore_result": None,
    "bond_results": None,
    "mpc_results": None,
    "mpc_path": None,
    "holidays": None,
    "last_update": None,
    "update_count": 0,
}

_sse_clients = []
_sse_lock = threading.Lock()


# ===================================================================
#  Computation Pipeline
# ===================================================================

def refresh_data():
    """Full data refresh: fetch -> bootstrap -> price -> analyze."""
    today = date.today()
    provider = _state["provider"]
    hols = _state["holidays"] or load_holidays()
    _state["holidays"] = hols

    log.info(f"Veri yenileniyor... ({today})")

    market = provider.get_onshore_ois(today)
    offshore = provider.get_offshore(today)
    bond_prices = provider.get_bond_prices(today)

    # Build OIS quotes for engine_v2
    ois_quotes = []
    for _, row in market.tickers.iterrows():
        tenor = row["tenor"]
        months, days = 0, 0
        if tenor.endswith("Y"):
            months = int(tenor.replace("Y", "")) * 12
        elif tenor.endswith("M"):
            months = int(tenor.replace("M", ""))
        elif tenor.endswith("W"):
            days = int(tenor.replace("W", "")) * 7

        bid = row.get("bid", row["mid"])
        ask = row.get("ask", row["mid"])
        if pd.isna(bid): bid = row["mid"]
        if pd.isna(ask): ask = row["mid"]
        ois_quotes.append(OISQuote(
            tenor=tenor, months=months, days=days,
            bid=float(bid), ask=float(ask), label=tenor,
        ))

    bs_result = bootstrap(ois_quotes, today, quote_type="mid", hols=hols)

    off_quotes = []
    for q in offshore.quotes:
        off_quotes.append(OffshoreQuote(
            tenor=q["tenor"], days=q["days"],
            rate=q["rate"], df=q["df"], ticker=q.get("ticker", ""),
        ))
    off_result = build_offshore_curve(off_quotes, bs_result.value_date)

    bond_inputs = []
    for isin, mat, cpn, freq, btype in BOND_UNIVERSE:
        if isin in bond_prices.prices:
            bond_inputs.append(BondInput(
                isin=isin, maturity=mat, coupon=cpn,
                freq=freq, px_last=bond_prices.prices[isin],
                bond_type=btype,
            ))
    bond_results = price_bonds(
        bond_inputs, bs_result.nodes, off_result.nodes, bs_result.value_date,
    )

    mpc_results = calc_implied_mpc(PPK_DATES, bs_result)
    mpc_path = build_mpc_path(PPK_DATES, bs_result, market.bisttref_rate)

    _state.update({
        "market": market,
        "offshore": offshore,
        "bond_prices": bond_prices,
        "bootstrap": bs_result,
        "offshore_result": off_result,
        "bond_results": bond_results,
        "mpc_results": mpc_results,
        "mpc_path": mpc_path,
        "last_update": datetime.now().isoformat(),
        "update_count": _state["update_count"] + 1,
    })

    log.info(
        f"Guncellendi: {len(bs_result.nodes)} DF, "
        f"{len(off_result.nodes)} offshore, "
        f"{len(bond_results)} tahvil, "
        f"{len(mpc_results)} PPK"
    )
    _notify_sse()


def _notify_sse():
    with _sse_lock:
        dead = []
        for i, client_q in enumerate(_sse_clients):
            try:
                client_q.append(_state["last_update"])
            except Exception:
                dead.append(i)
        for i in reversed(dead):
            _sse_clients.pop(i)


# ===================================================================
#  Helpers
# ===================================================================

def _json_safe(val):
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return None if np.isnan(val) else round(float(val), 8)
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


# ===================================================================
#  REST Endpoints
# ===================================================================

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def api_status():
    m = _state["market"]
    bs = _state["bootstrap"]
    return jsonify({
        "last_update": _state["last_update"],
        "today": date.today().isoformat(),
        "bisttref": m.bisttref_rate if m else None,
        "value_date": bs.value_date.isoformat() if bs else None,
        "ois_nodes": len(bs.nodes) if bs else 0,
        "offshore_nodes": len(_state["offshore_result"].nodes) if _state["offshore_result"] else 0,
        "bond_count": len(_state["bond_results"]) if _state["bond_results"] else 0,
        "update_count": _state["update_count"],
    })


@app.route("/api/curve")
def api_curve():
    bs = _state["bootstrap"]
    if bs is None:
        return jsonify({"error": "Veri yok"}), 503
    data = []
    for node in bs.nodes:
        zr = bs.zero_rate(node.days) * 100 if node.days > 0 else 0
        data.append({
            "tenor": node.tenor, "days": node.days,
            "date": node.mat_date.isoformat(),
            "df": round(node.df, 8),
            "zero_rate": round(zr, 4),
            "par_rate": round(node.par_rate * 100, 4),
        })
    return jsonify(data)


@app.route("/api/offshore_curve")
def api_offshore_curve():
    off = _state["offshore_result"]
    if off is None:
        return jsonify({"error": "Veri yok"}), 503
    data = []
    for node in off.nodes:
        zr = off.zero_rate(node.days) if node.days > 0 else 0
        data.append({
            "tenor": node.tenor, "days": node.days,
            "date": node.mat_date.isoformat(),
            "df": round(node.df, 8),
            "zero_rate": round(zr, 4),
        })
    return jsonify(data)


@app.route("/api/basis")
def api_basis():
    bs = _state["bootstrap"]
    off = _state["offshore_result"]
    if bs is None or off is None:
        return jsonify({"error": "Veri yok"}), 503
    tenor_days = [7, 14, 30, 63, 91, 183, 275, 365, 548, 731, 1096]
    result = compute_basis(bs.nodes, off, tenor_days)
    return jsonify(result)


@app.route("/api/lookup")
def api_lookup():
    bs = _state["bootstrap"]
    if bs is None:
        return jsonify({"error": "Veri yok"}), 503
    dtm = request.args.get("dtm", type=float)
    if dtm is None:
        return jsonify({"error": "dtm parametresi gerekli"}), 400
    df_val = bs.get_df(dtm)
    zr = bs.zero_rate(dtm) * 100 if dtm > 0 else 0
    gross_up = 1.0 / df_val if df_val > 0 else None
    off = _state["offshore_result"]
    off_zr = off.zero_rate(dtm) * 100 if off and dtm > 0 else None
    return jsonify({
        "dtm": dtm, "df": round(df_val, 8),
        "zero_rate": round(zr, 4),
        "gross_up": round(gross_up, 8) if gross_up else None,
        "offshore_zr": round(off_zr, 4) if off_zr is not None else None,
    })


@app.route("/api/bonds")
def api_bonds():
    results = _state["bond_results"]
    if not results:
        return jsonify([])
    return jsonify([{
        "isin": b.isin, "maturity": b.maturity,
        "bond_type": b.bond_type, "days_to_mat": b.days_to_mat,
        "coupon": b.coupon, "px_last": b.px_last,
        "model_pv_ois": b.model_pv_ois,
        "zspread_ois": _json_safe(b.zspread_ois),
        "zspread_offshore": _json_safe(b.zspread_offshore),
        "basis_delta_bps": _json_safe(b.basis_delta_bps),
        "yield_ois": _json_safe(b.yield_ois),
    } for b in results])


@app.route("/api/mpc")
def api_mpc():
    results = _state["mpc_results"]
    if not results:
        return jsonify([])
    return jsonify([{
        "ppk_date": m.ppk_date.isoformat(),
        "dtm_from_spot": m.dtm_from_spot,
        "period_days": m.period_days,
        "forward_rate": m.forward_rate,
        "implied_mpc": m.implied_mpc,
        "df": m.df,
    } for m in results])


@app.route("/api/mpc_path")
def api_mpc_path():
    path = _state["mpc_path"]
    if path is None:
        return jsonify({"error": "Veri yok"}), 503
    return jsonify(path)


@app.route("/api/market_data")
def api_market_data():
    m = _state["market"]
    off = _state["offshore"]
    if m is None:
        return jsonify({"error": "Veri yok"}), 503
    ois_rows = []
    for _, row in m.tickers.iterrows():
        ois_rows.append({
            "tenor": row["tenor"],
            "bid": _json_safe(row.get("bid")),
            "ask": _json_safe(row.get("ask")),
            "mid": _json_safe(row["mid"]),
        })
    return jsonify({
        "bisttref": m.bisttref_rate,
        "ois": ois_rows,
        "offshore": off.quotes if off else [],
    })


@app.route("/api/model_rates", methods=["POST"])
def api_model_rates():
    m = _state["market"]
    bs = _state["bootstrap"]
    if m is None or bs is None:
        return jsonify({"error": "Veri yok"}), 503
    body = request.get_json(force=True)
    spot = body.get("spot_rate", m.bisttref_rate)
    mtgs = body.get("meetings", [])
    mkt_rates = {}
    for _, row in m.tickers.iterrows():
        mkt_rates[row["tenor"]] = float(row["mid"])
    results = compute_model_rates(
        bs.trade_date, spot, mtgs, mkt_rates, _state["holidays"],
    )
    return jsonify(results)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    try:
        refresh_data()
        return jsonify({"status": "ok", "last_update": _state["last_update"]})
    except Exception as e:
        log.error(f"Refresh hatasi: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ===================================================================
#  SSE
# ===================================================================

@app.route("/api/events")
def api_events():
    def stream():
        q = []
        with _sse_lock:
            _sse_clients.append(q)
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                if q:
                    ts = q.pop(0)
                    yield f"data: {json.dumps({'type': 'update', 'timestamp': ts})}\n\n"
                else:
                    yield ": heartbeat\n\n"
                    time.sleep(15)
        except GeneratorExit:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


# ===================================================================
#  Polling fallback
# ===================================================================

def _polling_loop(interval):
    while True:
        time.sleep(interval)
        try:
            log.info("Polling: veri yenileniyor...")
            refresh_data()
        except Exception as e:
            log.error(f"Polling hatasi: {e}", exc_info=True)


# ===================================================================
#  Main
# ===================================================================

if __name__ == "__main__":
    use_mock = "--mock" in sys.argv
    use_poll = "--poll" in sys.argv

    if use_mock:
        _state["provider"] = MockProvider()
        log.info("MockProvider (test modu)")
    else:
        _state["provider"] = BloombergProvider()
        log.info("Bloomberg baglantisi")

    refresh_data()

    if not use_mock and not use_poll:
        try:
            provider = _state["provider"]
            if hasattr(provider, "start_subscription"):
                provider.start_subscription(on_update=refresh_data)
                log.info("Bloomberg subscription aktif")
        except Exception as e:
            log.warning(f"Subscription basarisiz, polling'e geciliyor: {e}")
            use_poll = True

    if use_poll or use_mock:
        interval = POLLING_INTERVAL_SEC
        log.info(f"Polling modu: her {interval}s")
        t = threading.Thread(target=_polling_loop, args=(interval,), daemon=True)
        t.start()

    port = 5000
    log.info(f"Dashboard: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
