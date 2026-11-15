"""Dhan provider tests against a mocked Dhan API.

All instrument rows and candle values below are SYNTHETIC test data shaped like Dhan's
documented and observed responses (unquoted JSON numbers, float epoch-second timestamps
marking candle starts, intraday data ending at the 15:10 candle). No real Dhan data or
credentials are used, and the conftest blocks real network access.
"""

import json
from datetime import datetime
from decimal import Decimal

import httpx
import pytest

from helpers import FIXED_NOW, fixed_clock, make_service
from trading_scanner.config import Settings
from trading_scanner.market import IST
from trading_scanner.models import ResultState, ScanRequest
from trading_scanner.providers import ProviderError, SymbolResolutionError
from trading_scanner.providers.dhan import INTRADAY_URL, SCRIP_MASTER_URL, DhanProvider, InstrumentIndex
from trading_scanner.synthetic import SyntheticSession

CLIENT_ID = "cid-test-123"
TOKEN = "tok-secret-xyz"
HEADER = (
    "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_EXPIRY_CODE,SEM_TRADING_SYMBOL,"
    "SEM_LOT_UNITS,SEM_CUSTOM_SYMBOL,SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,SEM_OPTION_TYPE,SEM_TICK_SIZE,"
    "SEM_EXPIRY_FLAG,SEM_EXCH_INSTRUMENT_TYPE,SEM_SERIES,SM_SYMBOL_NAME"
)
CSV = "\n".join([
    HEADER,
    "NSE,E,1001,EQUITY,,HCLTECH,1.0,HCL Technologies,,,,0.1,NA,ES,EQ,HCL TECHNOLOGIES LTD",
    "NSE,D,9001,FUTSTK,0,HCLTECH-Nov2026-FUT,350.0,HCLTECH NOV FUT,2026-11-24 14:30:00,-0.01,XX,0.1,M,FUTSTK,,HCLTECH",
    "BSE,E,5001,EQUITY,,HCLTECH,1.0,HCL Technologies,,,,0.05,NA,A,A,HCL TECHNOLOGIES LTD",
    "NSE,E,1002,EQUITY,,LT,1.0,Larsen & Toubro,,,,0.1,NA,ES,EQ,LARSEN & TOUBRO LTD.",
    "NSE,E,1003,EQUITY,,SUNPHARMA,1.0,Sun Pharmaceutical,,,,0.1,NA,ES,EQ,SUN PHARMACEUTICAL IND L",
    "NSE,E,1004,EQUITY,,DUPCO,1.0,Dup Co,,,,0.1,NA,ES,BE,DUP CO LTD",
    "NSE,E,1005,EQUITY,,DUPCO,1.0,Dup Co,,,,0.1,NA,ES,BZ,DUP CO LTD",
    "NSE,E,1006,EQUITY,,TWINA,1.0,Twin,,,,0.1,NA,ES,EQ,TWIN A LTD",
    "NSE,E,1007,EQUITY,,TWINB,1.0,Twin,,,,0.1,NA,ES,EQ,TWIN B LTD",
    "NSE,D,9002,FUTSTK,0,HCLTECH-Oct2026-FUT,350.0,HCLTECH OCT FUT,2026-10-27 14:30:00,-0.01,XX,0.1,M,FUT,,",
    "NSE,D,9003,FUTSTK,0,HCLTECH-Dec2026-FUT,350.0,HCLTECH DEC FUT,2026-12-29 14:30:00,-0.01,XX,0.1,M,FUT,,",
    "NSE,I,13,INDEX,,NIFTY,1.0,Nifty 50,0001-01-01,,,0.05,NA,INDEX,X,NIFTY 50",
    "NSE,D,9004,FUTIDX,0,NIFTY-Nov2026-FUT,65.0,NIFTY NOV FUT,2026-11-23 14:30:00,-0.01,XX,0.05,M,FUT,,",
]) + "\n"


def long_session() -> SyntheticSession:
    return SyntheticSession().set("11:15", "108.00", "111.50", "107.80", "111.00").set(
        "11:20", "111.20", "111.90", "110.60", "111.40"
    )


def dhan_json(session: SyntheticSession, through: str = "15:10", shift_seconds: int = 0, close_override=None) -> str:
    rows = session.raw_candles(through)
    closes = [str(r.close) for r in rows]
    if close_override:
        closes = [close_override.get(r.start.strftime("%H:%M"), c) for r, c in zip(rows, closes)]

    def array(values):
        return "[" + ",".join(values) + "]"

    return (
        '{"open":' + array(str(r.open) for r in rows)
        + ',"high":' + array(str(r.high) for r in rows)
        + ',"low":' + array(str(r.low) for r in rows)
        + ',"close":' + array(closes)
        + ',"volume":' + array(f"{r.volume}.0" for r in rows)
        + ',"timestamp":' + array(f"{int(r.start.timestamp()) + shift_seconds}.0" for r in rows)
        + "}"
    )


class FakeDhan:
    def __init__(self, responses=None, csv_text=CSV, error=None):
        self.responses = responses or {}
        self.csv_text = csv_text
        self.error = error
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if str(request.url) == SCRIP_MASTER_URL:
            return httpx.Response(200, text=self.csv_text)
        if str(request.url) == INTRADAY_URL:
            status, text = self.responses[json.loads(request.content)["securityId"]]
            return httpx.Response(status, text=text)
        return httpx.Response(404)

    def intraday_requests(self):
        return [r for r in self.requests if str(r.url) == INTRADAY_URL]


def make_provider(tmp_path, fake, configured=True, clock=fixed_clock, sleeps=None, ticks=None):
    settings = Settings(
        _env_file=None,
        DHAN_CLIENT_ID=CLIENT_ID if configured else "",
        DHAN_ACCESS_TOKEN=TOKEN if configured else "",
        SCANNER_DATA_DIR=str(tmp_path),
    )
    tick = iter(ticks or [0.0] * 100)
    return DhanProvider(
        settings,
        client=httpx.Client(transport=httpx.MockTransport(fake)),
        clock=clock,
        sleep=(sleeps.append if sleeps is not None else (lambda seconds: None)),
        monotonic=lambda: next(tick),
    )


def scan_one(provider, stock="HCLTECH", day="2026-11-13", clock=fixed_clock):
    service = make_service(lambda name: provider)
    service._clock = clock
    return service.scan(ScanRequest(trading_date=day, stocks=[stock], provider="dhan")).results[0]


# ------------------------------------------------------------- instruments


@pytest.mark.parametrize(
    "name, symbol, security_id",
    [("HCLTECH", "HCLTECH", "1001"), ("hcl technologies", "HCLTECH", "1001"), ("HCL TECHNOLOGIES LTD", "HCLTECH", "1001"),
     ("L&T", "LT", "1002"), ("larsen & toubro", "LT", "1002"), ("Larsen & Toubro Ltd.", "LT", "1002"),
     ("Sun Pharma", "SUNPHARMA", "1003"), ("sun pharmaceutical", "SUNPHARMA", "1003")],
)
def test_names_resolve_to_nse_cash_equity_only(name, symbol, security_id):
    item = InstrumentIndex.from_csv(CSV.splitlines()).resolve(name)
    assert (item.symbol, item.security_id) == (symbol, security_id)  # never the future (9001) or BSE (5001)


def test_unknown_and_ambiguous_names_are_symbol_errors():
    index = InstrumentIndex.from_csv(CSV.splitlines())
    with pytest.raises(SymbolResolutionError, match="did not match"):
        index.resolve("NOTASTOCK")
    with pytest.raises(SymbolResolutionError, match="2 NSE equity listings"):
        index.resolve("DUPCO")
    with pytest.raises(SymbolResolutionError, match="ambiguous"):
        index.resolve("Twin")


def test_changed_instrument_list_format_is_reported():
    with pytest.raises(ProviderError, match="format has changed"):
        InstrumentIndex.from_csv(["EXCH,SYMBOL", "NSE,HCLTECH"])


def test_instrument_list_downloads_once_per_day_and_is_cached(tmp_path):
    fake = FakeDhan()
    make_provider(tmp_path, fake).resolve("HCLTECH")
    make_provider(tmp_path, fake).resolve("LT")
    assert sum(str(r.url) == SCRIP_MASTER_URL for r in fake.requests) == 1
    assert (tmp_path / "dhan" / "api-scrip-master-2026-11-15.csv").exists()


def test_not_configured_makes_no_network_request(tmp_path):
    fake = FakeDhan()
    provider = make_provider(tmp_path, fake, configured=False)
    result = scan_one(provider)
    assert result.state is ResultState.PROVIDER_ERROR and "not configured" in result.reason
    assert fake.requests == []


# ------------------------------------------------------------------ candles


def test_intraday_request_matches_the_confirmed_contract(tmp_path):
    fake = FakeDhan({"1001": (200, dhan_json(long_session()))})
    scan_one(make_provider(tmp_path, fake))
    (request,) = fake.intraday_requests()
    assert request.method == "POST"
    assert request.headers["access-token"] == TOKEN and request.headers["client-id"] == CLIENT_ID
    assert json.loads(request.content) == {
        "securityId": "1001", "exchangeSegment": "NSE_EQ", "instrument": "EQUITY", "interval": 5, "oi": False,
        "fromDate": "2026-11-13 09:00:00", "toDate": "2026-11-14 00:00:00",
    }


def test_full_scan_through_dhan_identifies_entry(tmp_path):
    fake = FakeDhan({"1001": (200, dhan_json(long_session()))})
    result = scan_one(make_provider(tmp_path, fake), stock="HCL Technologies")
    assert result.state is ResultState.ENTRY_IDENTIFIED
    assert result.provider == "dhan" and result.synthetic is False and result.data.source == "dhan:/v2/charts/intraday"
    assert result.instrument.provider_id == "1001"
    assert result.entry.time.strftime("%H:%M") == "11:20" and result.entry.price == Decimal("111.20")
    assert result.data.as_of == FIXED_NOW and result.data.session_complete is True
    assert any("ended with the 15:10 candle" in note for note in result.data.notes)


def test_missing_late_candles_prevent_a_no_breakout_claim(tmp_path):
    fake = FakeDhan({"1001": (200, dhan_json(SyntheticSession()))})
    result = scan_one(make_provider(tmp_path, fake))
    assert result.state is ResultState.INVALID_DATA
    assert result.data.missing_candles == ["15:15", "15:20", "15:25"]


def test_unquoted_prices_keep_exact_decimal_precision(tmp_path):
    session = SyntheticSession().set("11:15", "108.00", "111.50", "107.80", "111.00").set(
        "11:20", "110.90", "111.90", "110.60", "111.40"
    )
    payload = dhan_json(session, close_override={"11:15": "110.000000000000001"})
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (200, payload)})))
    assert result.state is ResultState.ENTRY_IDENTIFIED and str(result.breakout.close) == "110.000000000000001"


def test_empty_past_day_is_no_session(tmp_path):
    empty = '{"open":[],"high":[],"low":[],"close":[],"volume":[],"timestamp":[]}'
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (200, empty)})))
    assert result.state is ResultState.NO_SESSION


def test_empty_today_before_the_open_is_waiting_for_reference(tmp_path):
    morning = lambda: datetime(2026, 11, 13, 9, 5, tzinfo=IST)  # noqa: E731
    empty = '{"open":[],"high":[],"low":[],"close":[],"volume":[],"timestamp":[]}'
    provider = make_provider(tmp_path, FakeDhan({"1001": (200, empty)}), clock=morning)
    result = scan_one(provider, clock=morning)
    assert result.state is ResultState.WAITING_FOR_REFERENCE


def test_live_session_uses_only_closed_candles(tmp_path):
    at_1103 = lambda: datetime(2026, 11, 13, 11, 3, tzinfo=IST)  # noqa: E731
    session = SyntheticSession().set("11:00", "101.00", "101.20", "98.90", "99.00")  # forming, trading below range
    provider = make_provider(tmp_path, FakeDhan({"1001": (200, dhan_json(session, through="11:00"))}), clock=at_1103)
    result = scan_one(provider, clock=at_1103)
    assert result.state is ResultState.WAITING_FOR_BREAKOUT and result.breakout is None


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (401, '{"errorType":"Invalid_Authentication","errorCode":"DH-901","errorMessage":"Client ID or user generated access token is invalid or expired."}', "rejected the credentials"),
        (400, '{"status":"failed","data":{"806":"Data APIs not Subscribed"}}', "no Data API subscription"),
        (429, '{"errorCode":"DH-904","errorMessage":"Too many requests"}', "rate limit"),
        (400, '{"errorCode":"DH-905","errorMessage":"Missing required fields"}', "request parameters"),
        (500, "<html>oops</html>", "HTTP 500"),
    ],
)
def test_dhan_errors_become_sanitized_provider_errors(tmp_path, status, body, expected):
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (status, body.replace("Missing", f"Missing {TOKEN}"))})))
    assert result.state is ResultState.PROVIDER_ERROR and expected in result.reason
    assert TOKEN not in result.model_dump_json() and CLIENT_ID not in result.model_dump_json()
    assert "No fixture or synthetic data was substituted" in result.reason


def test_unequal_arrays_are_rejected(tmp_path):
    payload = json.loads(dhan_json(long_session()))
    payload["close"].pop()
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (200, json.dumps(payload))})))
    assert result.state is ResultState.PROVIDER_ERROR and "unequal lengths" in result.reason


def test_timezone_shifted_timestamps_are_rejected_not_used(tmp_path):
    payload = dhan_json(long_session(), shift_seconds=19800)  # IST wall time sent as UTC
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (200, payload)})))
    assert result.state is ResultState.PROVIDER_ERROR and "do not line up" in result.reason


def test_end_labeled_timestamps_are_rejected(tmp_path):
    payload = dhan_json(long_session(), through="15:25", shift_seconds=300)
    result = scan_one(make_provider(tmp_path, FakeDhan({"1001": (200, payload)})))
    assert result.state is ResultState.PROVIDER_ERROR and "labeled by end time" in result.reason


def test_network_failure_is_reported(tmp_path):
    fake = FakeDhan(error=httpx.ConnectError("boom"))
    result = scan_one(make_provider(tmp_path, fake))
    assert result.state is ResultState.PROVIDER_ERROR and "instrument list" in result.reason


def test_requests_are_throttled_below_the_documented_rate_limit(tmp_path):
    sleeps: list[float] = []
    fake = FakeDhan({"1001": (200, dhan_json(long_session())), "1002": (200, dhan_json(long_session()))})
    provider = make_provider(tmp_path, fake, sleeps=sleeps, ticks=[0.0, 0.0, 0.1, 0.25])
    service = make_service(lambda name: provider)
    service.scan(ScanRequest(trading_date="2026-11-13", stocks=["HCLTECH", "LT"], provider="dhan"))
    assert sleeps == [pytest.approx(0.15)]


# ------------------------------------------------------------------ search


def test_search_labels_stocks_futures_and_indices(tmp_path):
    provider = make_provider(tmp_path, FakeDhan())
    results = provider.search("hcl", 10)
    assert [(r.symbol, r.kind) for r in results] == [
        ("HCLTECH", "stock"), ("HCLTECH-Nov2026-FUT", "future"), ("HCLTECH-Dec2026-FUT", "future"),
    ]  # the expired Oct contract is dropped; the stock comes first
    stock, nearest = results[0], results[1]
    assert stock.scannable is True and stock.name == "HCL Technologies"
    assert nearest.scannable is False and nearest.lot_size == 350 and str(nearest.expiry) == "2026-11-24"
    assert "cash stocks only" in nearest.note and nearest.underlying == "HCLTECH"
    nifty = provider.search("nifty", 5)
    assert [(r.symbol, r.kind, r.scannable) for r in nifty] == [("NIFTY", "index", False), ("NIFTY-Nov2026-FUT", "future", False)]


def test_search_ranks_exact_names_and_taught_aliases_first(tmp_path):
    provider = make_provider(tmp_path, FakeDhan())
    assert provider.search("L&T", 3)[0].symbol == "LT"
    assert provider.search("sun pharma", 3)[0].symbol == "SUNPHARMA"
    assert provider.search("zzz", 3) == []


def test_search_needs_no_credentials_but_reports_download_failures(tmp_path):
    assert make_provider(tmp_path, FakeDhan(), configured=False).search("hcl", 3)[0].symbol == "HCLTECH"
    with pytest.raises(ProviderError, match="instrument list"):
        make_provider(tmp_path / "other", FakeDhan(error=httpx.ConnectError("down"))).search("hcl", 3)
