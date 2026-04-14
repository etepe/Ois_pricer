"""
Veri Sağlayıcı
===============
Bloomberg (blpapi) ve test amaçlı MockProvider.
Offshore TRYI, tahvil fiyatları ve subscription desteği.

Kullanım:
    provider = BloombergProvider()   # şirkette
    provider = MockProvider()        # test / geliştirme

    ois_data = provider.get_onshore_ois()
    offshore_data = provider.get_offshore()
    bond_prices = provider.get_bond_prices()
"""
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from config import (
    BISTTREF_TICKER, ONSHORE_OIS_TICKERS,
    OFFSHORE_TRYI_TICKERS, BOND_UNIVERSE,
)
from engine_v2.calendar import (
    load_holidays, is_business_day, next_business_day, add_business_days,
)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════════════════

@dataclass
class OISMarketData:
    """Onshore OIS piyasa verileri."""
    today: date
    bisttref_rate: float               # O/N TLREF oranı (%)
    tickers: pd.DataFrame              # [tenor, ticker, maturity, bid, ask, mid]


@dataclass
class OffshoreMarketData:
    """Offshore TRYI piyasa verileri."""
    today: date
    quotes: list                        # [{tenor, ticker, days, rate, df}]


@dataclass
class BondPriceData:
    """Tahvil fiyat verileri."""
    today: date
    prices: dict                        # {ISIN: px_last}


class DataProvider(ABC):
    """Bloomberg veya mock veri kaynağı."""

    @abstractmethod
    def get_onshore_ois(self, today: date) -> OISMarketData:
        ...

    @abstractmethod
    def get_offshore(self, today: date) -> OffshoreMarketData:
        ...

    @abstractmethod
    def get_bond_prices(self, today: date) -> BondPriceData:
        ...


# ═══════════════════════════════════════════════════════════════════
#  Bloomberg Provider (blpapi)
# ═══════════════════════════════════════════════════════════════════

class BloombergProvider(DataProvider):
    """
    Bloomberg Terminal'den blpapi ile veri çeker.
    Subscription desteği ile real-time güncelleme.
    """

    def __init__(self):
        try:
            import blpapi
            self._blpapi = blpapi
            self._session = None
            self._sub_session = None
            self._on_update: Optional[Callable] = None
            self._subscribed = False
        except ImportError:
            raise ImportError(
                "blpapi kurulu değil. "
                "pip install blpapi ile kurun veya MockProvider kullanın."
            )

    def _ensure_session(self):
        if self._session is not None:
            return

        options = self._blpapi.SessionOptions()
        options.setServerHost("localhost")
        options.setServerPort(8194)

        self._session = self._blpapi.Session(options)
        if not self._session.start():
            raise ConnectionError("Bloomberg session başlatılamadı.")
        if not self._session.openService("//blp/refdata"):
            raise ConnectionError("//blp/refdata servisi açılamadı.")

        self._refdata = self._session.getService("//blp/refdata")
        log.info("Bloomberg bağlantısı kuruldu.")

    def _bdp(self, securities: list, fields: list) -> pd.DataFrame:
        """Bloomberg Data Point — tek değer çeker."""
        self._ensure_session()

        request = self._refdata.createRequest("ReferenceDataRequest")
        for sec in securities:
            request.append("securities", sec)
        for fld in fields:
            request.append("fields", fld)

        self._session.sendRequest(request)

        rows = []
        while True:
            event = self._session.nextEvent(500)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec = sec_data.getValueAsElement(i)
                        security = sec.getElementAsString("security")
                        field_data = sec.getElement("fieldData")
                        row = {"security": security}
                        for fld in fields:
                            try:
                                val = field_data.getElement(fld)
                                if val.datatype() == self._blpapi.DataType.DATE:
                                    v = val.getValueAsDatetime()
                                    row[fld] = date(v.year, v.month, v.day)
                                else:
                                    row[fld] = val.getValueAsFloat()
                            except Exception:
                                row[fld] = None
                        rows.append(row)
            if event.eventType() == self._blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(rows)

    def get_onshore_ois(self, today: date) -> OISMarketData:
        log.info("Bloomberg'den onshore OIS verileri çekiliyor...")
        hols = load_holidays()

        # BISTTREF
        bisttref_df = self._bdp([BISTTREF_TICKER], ["PX_LAST"])
        bisttref_rate = float(bisttref_df.iloc[0]["PX_LAST"])

        # OIS swap tickers
        tickers = [t[1] for t in ONSHORE_OIS_TICKERS]
        ois_df = self._bdp(tickers, ["MATURITY", "PX_BID", "PX_ASK", "PX_MID"])

        ticker_to_tenor = {t[1]: t[0] for t in ONSHORE_OIS_TICKERS}
        ois_df["tenor"] = ois_df["security"].map(ticker_to_tenor)

        result = ois_df.rename(columns={
            "security": "ticker", "MATURITY": "maturity",
            "PX_BID": "bid", "PX_ASK": "ask", "PX_MID": "mid",
        })[["tenor", "ticker", "maturity", "bid", "ask", "mid"]]

        result["maturity"] = result["maturity"].apply(
            lambda m: next_business_day(m, hols) if m is not None else None
        )
        result = result.dropna(subset=["maturity", "mid"])
        result = result.sort_values("maturity").reset_index(drop=True)

        return OISMarketData(today=today, bisttref_rate=bisttref_rate, tickers=result)

    def get_offshore(self, today: date) -> OffshoreMarketData:
        log.info("Bloomberg'den offshore TRYI verileri çekiliyor...")

        tickers = [t[1] for t in OFFSHORE_TRYI_TICKERS]
        df = self._bdp(tickers, ["PX_LAST"])

        ticker_map = {t[1]: (t[0], t[2]) for t in OFFSHORE_TRYI_TICKERS}
        quotes = []
        for _, row in df.iterrows():
            sec = row["security"]
            if sec in ticker_map:
                tenor, days = ticker_map[sec]
                rate = row.get("PX_LAST", 0) or 0
                disc = 1.0 / (1.0 + rate / 100.0 * days / 360.0) if days > 0 else 1.0
                quotes.append({
                    "tenor": tenor, "ticker": sec,
                    "days": days, "rate": rate, "df": disc,
                })

        return OffshoreMarketData(today=today, quotes=quotes)

    def get_bond_prices(self, today: date) -> BondPriceData:
        isins = [b[0] for b in BOND_UNIVERSE]
        log.info(f"Bloomberg'den {len(isins)} tahvil fiyatı çekiliyor...")

        securities = [f"{isin} Corp" for isin in isins]
        df = self._bdp(securities, ["PX_LAST"])

        prices = {}
        for isin, sec in zip(isins, securities):
            row = df[df["security"] == sec]
            if not row.empty and row.iloc[0]["PX_LAST"] is not None:
                prices[isin] = float(row.iloc[0]["PX_LAST"])

        return BondPriceData(today=today, prices=prices)

    # ── Subscription-based real-time updates ──

    def start_subscription(self, on_update: Callable):
        """
        Bloomberg subscription ile real-time fiyat değişimlerini dinle.
        on_update callback'i her fiyat güncellemesinde çağrılır.
        """
        self._on_update = on_update

        try:
            self._ensure_session()

            # Subscription list oluştur
            sub_list = self._blpapi.SubscriptionList()

            # OIS tickers
            for _, ticker in ONSHORE_OIS_TICKERS:
                sub_list.add(ticker, "PX_BID,PX_ASK,PX_MID",
                            "", self._blpapi.CorrelationId(ticker))

            # BISTTREF
            sub_list.add(BISTTREF_TICKER, "PX_LAST",
                        "", self._blpapi.CorrelationId(BISTTREF_TICKER))

            # Offshore
            for _, ticker, _ in OFFSHORE_TRYI_TICKERS:
                sub_list.add(ticker, "PX_LAST",
                            "", self._blpapi.CorrelationId(ticker))

            # Bond tickers
            for isin, *_ in BOND_UNIVERSE:
                sec = f"{isin} Corp"
                sub_list.add(sec, "PX_LAST",
                            "", self._blpapi.CorrelationId(sec))

            self._session.subscribe(sub_list)
            self._subscribed = True
            log.info("Bloomberg subscription başlatıldı.")

            # Event loop thread
            t = threading.Thread(target=self._subscription_loop, daemon=True)
            t.start()

        except Exception as e:
            log.error(f"Subscription başlatılamadı: {e}")
            self._subscribed = False

    def _subscription_loop(self):
        """Bloomberg event loop for subscriptions."""
        while self._subscribed:
            try:
                event = self._session.nextEvent(1000)
                if event.eventType() == self._blpapi.Event.SUBSCRIPTION_DATA:
                    if self._on_update:
                        self._on_update()
            except Exception as e:
                log.debug(f"Subscription event error: {e}")
                time.sleep(1)

    def stop_subscription(self):
        self._subscribed = False


# ═══════════════════════════════════════════════════════════════════
#  Mock Provider
# ═══════════════════════════════════════════════════════════════════

class MockProvider(DataProvider):
    """
    13 Nisan 2026 piyasa verisiyle test provider.
    JSX frontend'teki veriler kullanılıyor.
    """

    MOCK_TODAY = date(2026, 4, 13)
    MOCK_BISTTREF = 46.00

    # OIS bid/ask from JSX Q_OIS
    MOCK_OIS = [
        ("1W",  date(2026, 4, 21),   39.60, 40.60),
        ("1M",  date(2026, 5, 14),   40.30, 40.50),
        ("2M",  date(2026, 6, 15),   40.69, 40.89),
        ("3M",  date(2026, 7, 14),   41.15, 41.35),
        ("6M",  date(2026, 10, 14),  39.98, 40.18),
        ("9M",  date(2027, 1, 14),   38.98, 39.18),
        ("1Y",  date(2027, 4, 14),   38.05, 38.25),
        ("18M", date(2027, 10, 14),  36.75, 36.95),
        ("2Y",  date(2028, 4, 14),   35.68, 35.88),
        ("3Y",  date(2029, 4, 16),   34.08, 34.30),
        ("4Y",  date(2030, 4, 17),   32.84, 33.05),
        ("5Y",  date(2031, 4, 14),   31.79, 32.02),
    ]

    # Offshore TRYI from JSX Q_OFF
    MOCK_OFFSHORE = [
        ("ON",  "TRYION",  0,    31.75, 1.0),
        ("TN",  "TRYITN",  1,    28.00, 0.99922),
        ("1W",  "TRYI1W",  7,    30.35, 0.99411),
        ("2W",  "TRYI2W",  14,   33.15, 0.98722),
        ("1M",  "TRYI1M",  30,   34.53, 0.97124),
        ("2M",  "TRYI2M",  63,   36.35, 0.94034),
        ("3M",  "TRYI3M",  91,   37.40, 0.91365),
        ("6M",  "TRYI6M",  183,  38.75, 0.83543),
        ("9M",  "TRYI9M",  275,  39.69, 0.76710),
        ("1Y",  "TRYI12M", 365,  41.02, 0.70629),
        ("18M", "TRYI18M", 548,  38.05, 0.63321),
        ("2Y",  "TRYI2Y",  731,  39.04, 0.55768),
        ("3Y",  "TRYI3Y",  1096, 36.94, 0.47101),
    ]

    # Bond prices from JSX BONDS
    MOCK_BOND_PRICES = {
        "TRB170626T13": 93.545,
        "TRT080726T13": 100.2,
        "TRT190826T19": 100.8,
        "TRT060127T10": 77.254,
        "TRT130127T11": 99.0,
        "TRT160627T13": 101.05,
        "TRT140727T14": 99.4,
        "TRT131027T10": 100.4,
        "TRT131027T36": 99.45,
        "TRD171127T13": 100.0,
        "TRT190128T14": 100.25,
        "TRT010328T12": 100.4,
        "TRT170528T12": 100.2,
        "TRT060928T11": 100.5,
        "TRT081128T15": 92.25,
        "TRT061228T16": 100.425,
        "TRT070329T15": 100.2,
        "TRT040729T14": 100.0,
        "TRT130629T30": 100.1,
        "TRT120929T12": 90.175,
        "TRT090130T12": 97.075,
        "TRT100730T13": 100.0,
    }

    def get_onshore_ois(self, today: date = None) -> OISMarketData:
        today = today or self.MOCK_TODAY
        rows = []
        for tenor, mat, bid, ask in self.MOCK_OIS:
            ticker = dict(ONSHORE_OIS_TICKERS).get(tenor, "")
            rows.append({
                "tenor": tenor, "ticker": ticker,
                "maturity": mat, "bid": bid, "ask": ask,
                "mid": (bid + ask) / 2,
            })
        df = pd.DataFrame(rows).sort_values("maturity").reset_index(drop=True)
        return OISMarketData(today=today, bisttref_rate=self.MOCK_BISTTREF, tickers=df)

    def get_offshore(self, today: date = None) -> OffshoreMarketData:
        today = today or self.MOCK_TODAY
        quotes = []
        for tenor, ticker, days, rate, df_val in self.MOCK_OFFSHORE:
            quotes.append({
                "tenor": tenor, "ticker": ticker,
                "days": days, "rate": rate, "df": df_val,
            })
        return OffshoreMarketData(today=today, quotes=quotes)

    def get_bond_prices(self, today: date = None) -> BondPriceData:
        today = today or self.MOCK_TODAY
        return BondPriceData(today=today, prices=dict(self.MOCK_BOND_PRICES))
