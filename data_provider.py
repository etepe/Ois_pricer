"""
Veri Sağlayıcı
===============
Bloomberg (blpapi) ve test amaçlı MockProvider.

Kullanım:
    provider = BloombergProvider()   # şirkette
    provider = MockProvider()        # test / geliştirme
    
    ois_data = provider.get_onshore_ois()
    tlref_bonds = provider.get_tlref_bonds(isin_list)
"""
import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from dataclasses import dataclass

import pandas as pd

from config import (
    BISTTREF_TICKER, ONSHORE_OIS_TICKERS, TR_HOLIDAYS,
)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Takvim Yardımcıları
# ═══════════════════════════════════════════════════════════════════

def is_business_day(d: date) -> bool:
    """Hafta sonu veya TR tatili değilse iş günüdür."""
    return d.weekday() < 5 and d not in TR_HOLIDAYS


def next_bday(d: date) -> date:
    """Verilen tarihten itibaren ilk iş gününü bulur (tarih dahil)."""
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def add_bdays(d: date, n: int) -> date:
    """Tarihten n iş günü ilerler."""
    count = 0
    cur = d
    while count < n:
        cur += timedelta(days=1)
        if is_business_day(cur):
            count += 1
    return cur


# ═══════════════════════════════════════════════════════════════════
#  Abstract Base
# ═══════════════════════════════════════════════════════════════════

@dataclass
class OISMarketData:
    """Onshore OIS piyasa verileri."""
    today: date
    bisttref_rate: float               # O/N TLREF oranı (%)
    tickers: pd.DataFrame              # [tenor, ticker, maturity, mid]


class DataProvider(ABC):
    """Bloomberg veya mock veri kaynağı."""

    @abstractmethod
    def get_onshore_ois(self, today: date) -> OISMarketData:
        """Onshore OIS verilerini döndürür."""
        ...

    @abstractmethod
    def get_tlref_bonds(self, isin_list: list[str], today: date) -> pd.DataFrame:
        """TLREF tahvil verilerini döndürür: [isin, maturity, px_last]"""
        ...


# ═══════════════════════════════════════════════════════════════════
#  Bloomberg Provider (blpapi)
# ═══════════════════════════════════════════════════════════════════

class BloombergProvider(DataProvider):
    """
    Bloomberg Terminal'den blpapi ile veri çeker.
    
    Gereksinim: pip install blpapi
    Bloomberg Terminal veya B-PIPE bağlantısı aktif olmalı.
    """

    def __init__(self):
        try:
            import blpapi
            self._blpapi = blpapi
            self._session = None
        except ImportError:
            raise ImportError(
                "blpapi kurulu değil. "
                "pip install blpapi ile kurun veya MockProvider kullanın."
            )

    def _ensure_session(self):
        """Bloomberg session'ı başlatır (lazy init)."""
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

    def _bdp(self, securities: list[str], fields: list[str]) -> pd.DataFrame:
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
                                # Tarih ise date'e çevir
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
        """Bloomberg'den onshore OIS verilerini çeker."""
        log.info("Bloomberg'den onshore OIS verileri çekiliyor...")

        # 1) BISTTREF — O/N referans oranı
        bisttref_df = self._bdp(
            [BISTTREF_TICKER],
            ["PX_LAST"],
        )
        bisttref_rate = float(bisttref_df.iloc[0]["PX_LAST"])
        log.info(f"  BISTTREF O/N = {bisttref_rate:.2f}%")

        # 2) OIS swap ticker'ları — maturity ve mid
        tickers = [t[1] for t in ONSHORE_OIS_TICKERS]
        ois_df = self._bdp(
            tickers,
            ["MATURITY", "PX_MID"],
        )

        # Tenor etiketlerini ekle
        ticker_to_tenor = {t[1]: t[0] for t in ONSHORE_OIS_TICKERS}
        ois_df["tenor"] = ois_df["security"].map(ticker_to_tenor)

        # Kolon düzenle
        result = ois_df.rename(columns={
            "security": "ticker",
            "MATURITY": "maturity",
            "PX_MID": "mid",
        })[["tenor", "ticker", "maturity", "mid"]]

        # Maturity'leri iş gününe ayarla
        result["maturity"] = result["maturity"].apply(
            lambda m: next_bday(m) if m is not None else None
        )
        result = result.dropna(subset=["maturity", "mid"])
        result = result.sort_values("maturity").reset_index(drop=True)

        log.info(f"  {len(result)} OIS tenor yüklendi.")

        return OISMarketData(
            today=today,
            bisttref_rate=bisttref_rate,
            tickers=result,
        )

    def get_tlref_bonds(self, isin_list: list[str], today: date) -> pd.DataFrame:
        """Bloomberg'den TLREF tahvil verilerini çeker."""
        log.info(f"Bloomberg'den {len(isin_list)} TLREF tahvil çekiliyor...")

        securities = [f"{isin} Corp" for isin in isin_list]
        df = self._bdp(securities, ["MATURITY", "PX_LAST"])

        df["isin"] = isin_list
        result = df.rename(columns={
            "MATURITY": "maturity",
            "PX_LAST": "px_last",
        })[["isin", "maturity", "px_last"]]

        return result.dropna().reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════
#  Mock Provider (test / geliştirme)
# ═══════════════════════════════════════════════════════════════════

class MockProvider(DataProvider):
    """
    13 Nisan 2026 piyasa verisiyle test provider.
    Veriler Bloomberg ekranından alınmıştır.
    """

    # Resimdeki OIS mid rate'leri (% olarak)
    MOCK_OIS_RATES = {
        #  tenor    maturity          mid(%)
        "1W":  (date(2026, 4, 21),   40.10),
        "1M":  (date(2026, 5, 14),   40.45),
        "2M":  (date(2026, 6, 15),   41.15),
        "3M":  (date(2026, 7, 14),   41.45),
        "6M":  (date(2026, 10, 14),  40.25),
        "9M":  (date(2027, 1, 14),   39.25),
        "1Y":  (date(2027, 4, 14),   38.33),
        "18M": (date(2027, 10, 14),  37.04),
        "2Y":  (date(2028, 4, 14),   35.98),
        "3Y":  (date(2029, 4, 16),   34.39),
        "4Y":  (date(2030, 4, 17),   33.14),
        "5Y":  (date(2031, 4, 14),   32.10),
        "6Y":  (date(2032, 4, 14),   31.26),
        "7Y":  (date(2033, 4, 14),   30.53),
        "8Y":  (date(2034, 4, 14),   29.89),
        "9Y":  (date(2035, 4, 16),   29.35),
        "10Y": (date(2036, 4, 14),   28.88),
    }

    MOCK_BISTTREF = 46.00   # TCMB politika faizi yakını

    MOCK_TODAY = date(2026, 4, 13)

    def get_onshore_ois(self, today: date = None) -> OISMarketData:
        today = today or self.MOCK_TODAY

        rows = []
        for tenor, ticker in ONSHORE_OIS_TICKERS:
            if tenor in self.MOCK_OIS_RATES:
                mat, mid = self.MOCK_OIS_RATES[tenor]
                rows.append({
                    "tenor": tenor,
                    "ticker": ticker,
                    "maturity": mat,
                    "mid": mid,
                })

        df = pd.DataFrame(rows).sort_values("maturity").reset_index(drop=True)
        log.info(f"MockProvider: {len(df)} OIS tenor, BISTTREF={self.MOCK_BISTTREF}%")

        return OISMarketData(
            today=today,
            bisttref_rate=self.MOCK_BISTTREF,
            tickers=df,
        )

    def get_tlref_bonds(self, isin_list: list[str], today: date = None) -> pd.DataFrame:
        # Örnek TLREF tahviller
        mock = {
            "TRT140127T13": (date(2027, 1, 14), 101.50),
            "TRT150727T11": (date(2027, 7, 15), 102.75),
            "TRT140128T11": (date(2028, 1, 14), 103.10),
        }
        rows = []
        for isin in isin_list:
            if isin in mock:
                mat, px = mock[isin]
                rows.append({"isin": isin, "maturity": mat, "px_last": px})

        return pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["isin", "maturity", "px_last"]
        )
