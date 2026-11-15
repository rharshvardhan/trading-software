from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading_scanner.formatting import format_inr, format_price
from trading_scanner.market import IST, describe_slots, QUALIFICATION_SLOTS
from trading_scanner.models import Candle, ScanRequest, parse_price

OK = {"open": "100.00", "high": "101.00", "low": "99.00", "close": "100.50"}


def test_candle_normalizes_utc_timestamp_to_kolkata():
    candle = Candle(start="2026-11-13T05:30:00+00:00", **OK)
    assert candle.start.utcoffset() == timedelta(hours=5, minutes=30)
    assert candle.start.strftime("%Y-%m-%d %H:%M") == "2026-11-13 11:00"


def test_candle_accepts_epoch_seconds_as_utc():
    epoch = int(datetime(2026, 11, 13, 4, 0, tzinfo=timezone.utc).timestamp())
    assert Candle(start=epoch, **OK).start.strftime("%H:%M") == "09:30"


def test_candle_rejects_timezone_naive_timestamp():
    with pytest.raises(ValidationError, match="no timezone"):
        Candle(start="2026-11-13T10:30:00", **OK)


def test_candle_end_is_start_plus_five_minutes():
    candle = Candle(start=datetime(2026, 11, 13, 11, 0, tzinfo=IST), **OK)
    assert candle.end.strftime("%H:%M") == "11:05"


@pytest.mark.parametrize(
    "prices, message",
    [
        ({"open": "100", "high": "99", "low": "98", "close": "98.5"}, "high 99 is below open 100"),
        ({"open": "100", "high": "101", "low": "100.5", "close": "100.7"}, "low 100.5 is above open 100"),
        ({"open": "100", "high": "101", "low": "102", "close": "100.5"}, "below low"),
    ],
)
def test_candle_rejects_inconsistent_ohlc(prices, message):
    with pytest.raises(ValidationError, match=message):
        Candle(start="2026-11-13T10:30:00+05:30", **prices)


@pytest.mark.parametrize("bad", ["0", "-1", "NaN", "Infinity", True, "abc", None])
def test_price_must_be_positive_finite_number(bad):
    with pytest.raises(ValueError):
        parse_price(bad)


def test_prices_keep_source_precision_without_float_drift():
    assert parse_price("1384.90") == Decimal("1384.90") and str(parse_price("1384.90")) == "1384.90"
    assert str(parse_price(1384.9)) == "1384.9"
    assert str(parse_price(0.1 + 0.2)) == "0.30000000000000004"  # the float the provider actually sent


def test_volume_is_informational_and_only_needs_to_be_nonnegative():
    assert Candle(start="2026-11-13T10:30:00+05:30", volume=None, **OK).volume is None
    assert Candle(start="2026-11-13T10:30:00+05:30", volume="1200", **OK).volume == 1200
    assert Candle(start="2026-11-13T10:30:00+05:30", volume=1.5, **OK).volume == Decimal("1.5")
    for bad in (-1, "abc", "NaN", True):
        with pytest.raises(ValidationError):
            Candle(start="2026-11-13T10:30:00+05:30", volume=bad, **OK)


def test_out_of_range_epoch_timestamp_is_a_validation_error():
    with pytest.raises(ValidationError, match="out of range"):
        Candle(start=10**20, **OK)


def test_scan_request_valid_and_stock_names_trimmed():
    request = ScanRequest(trading_date="2026-11-13", stocks=["  HCLTECH "], provider="fixture")
    assert request.trading_date == date(2026, 11, 13) and request.stocks == ["HCLTECH"]


@pytest.mark.parametrize(
    "payload",
    [
        {"trading_date": "2026-13-01", "stocks": ["A"], "provider": "fixture"},
        {"trading_date": "2026-02-30", "stocks": ["A"], "provider": "fixture"},
        {"trading_date": "13-11-2026", "stocks": ["A"], "provider": "fixture"},
        {"trading_date": 20261113, "stocks": ["A"], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": [], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["   "], "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["A"] * 101, "provider": "fixture"},
        {"trading_date": "2026-11-13", "stocks": ["A"]},
        {"trading_date": "2026-11-13", "stocks": ["A"], "provider": "yahoo"},
        {"trading_date": "2026-11-13", "stocks": ["A"], "provider": "fixture", "extra": 1},
    ],
)
def test_scan_request_rejects_malformed_shapes(payload):
    with pytest.raises(ValidationError):
        ScanRequest.model_validate(payload)


def test_price_formatting_uses_indian_grouping_without_rounding():
    assert format_price(Decimal("1384.90")) == "1,384.90"
    assert format_inr(Decimal("1384.90")) == "₹1,384.90"
    assert format_price(Decimal("1384.9")) == "1,384.90"
    assert format_price(Decimal("123456.7")) == "1,23,456.70"
    assert format_price(Decimal("1384.905")) == "1,384.905"
    assert format_price(None) == "—"


def test_describe_slots_compresses_runs():
    assert describe_slots(QUALIFICATION_SLOTS) == "09:15-10:45 (19 candles)"
