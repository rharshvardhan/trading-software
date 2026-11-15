from datetime import date, datetime, time, timedelta, timezone

from helpers import evaluate, raw
from trading_scanner.models import RawCandle, ResultState
from trading_scanner.normalize import normalize_candles
from trading_scanner.strategy import evaluate_session
from trading_scanner.synthetic import SyntheticSession, as_of

DAY = date(2026, 11, 13)
CLOSE = as_of("15:30")


def test_candles_are_sorted_chronologically():
    rows = [raw("2026-11-13T09:25:00+05:30", "1", "2", "1", "1.5"), raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.5")]
    result = normalize_candles(rows, DAY, CLOSE)
    assert list(result.session.candles) == [time(9, 15), time(9, 25)]


def test_other_dates_and_out_of_session_candles_are_dropped_with_notes():
    rows = [
        raw("2026-11-12T15:25:00+05:30", "1", "2", "1", "1.5"),  # previous day
        raw("2026-11-13T09:05:00+05:30", "1", "2", "1", "1.5"),  # pre-market
        raw("2026-11-13T15:30:00+05:30", "1", "2", "1", "1.5"),  # after session
        raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.5"),
    ]
    result = normalize_candles(rows, DAY, CLOSE)
    assert not result.problems
    assert list(result.session.candles) == [time(9, 15)]
    assert any("dated other than 2026-11-13" in n for n in result.notes)
    assert any("outside the 09:15-15:25 session" in n for n in result.notes)


def test_off_grid_timestamp_is_contradictory():
    result = normalize_candles([raw("2026-11-13T09:17:00+05:30", "1", "2", "1", "1.5")], DAY, CLOSE)
    assert result.session is None and "five-minute grid" in result.problems[0]


def test_conflicting_duplicate_is_rejected_and_identical_duplicate_removed():
    a = raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.5")
    b = raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.6")
    conflicting = normalize_candles([a, b], DAY, CLOSE)
    assert conflicting.session is None and "Conflicting duplicate candles at 09:15" in conflicting.problems[0]
    identical = normalize_candles([a, a], DAY, CLOSE)
    assert len(identical.session.candles) == 1
    assert any("identical duplicate" in n for n in identical.notes)


def test_same_instant_in_another_timezone_counts_as_duplicate():
    a = raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.5")
    b = raw("2026-11-13T03:45:00+00:00", "1", "2", "1", "1.5")
    assert len(normalize_candles([a, b], DAY, CLOSE).session.candles) == 1


def test_candle_after_as_of_time_is_contradictory():
    result = normalize_candles([raw("2026-11-13T11:10:00+05:30", "1", "2", "1", "1.5")], DAY, as_of("11:07"))
    assert result.session is None and "starts after the data as-of time 11:07" in result.problems[0]


def test_invalid_ohlc_names_the_candle():
    result = normalize_candles([raw("2026-11-13T10:35:00+05:30", "100", "99", "98", "98.5")], DAY, CLOSE)
    assert result.session is None and result.problems[0].startswith("Candle at 10:35 is invalid")


def test_naive_timestamps_and_as_of_are_rejected():
    assert normalize_candles([raw("2026-11-13T10:35:00", "1", "2", "1", "1.5")], DAY, CLOSE).session is None
    assert normalize_candles([], DAY, datetime(2026, 11, 13, 15, 30)).session is None


def test_utc_timestamps_evaluate_identically_to_kolkata_timestamps():
    session = SyntheticSession().set("11:15", "108.00", "111.50", "107.80", "111.00").set(
        "11:20", "111.20", "111.90", "110.60", "111.40"
    )
    utc_rows = [
        RawCandle(c.start.astimezone(timezone.utc).isoformat(), c.open, c.high, c.low, c.close, c.volume)
        for c in session.raw_candles()
    ]
    from_utc = evaluate_session(normalize_candles(utc_rows, DAY, CLOSE.astimezone(timezone.utc)).session)
    assert from_utc == evaluate(session)
    assert from_utc.entry.candle.start.utcoffset() == timedelta(hours=5, minutes=30)
    assert from_utc.state is ResultState.ENTRY_IDENTIFIED


def test_pre_market_candles_are_dropped_before_grid_and_ohlc_checks():
    rows = [
        raw("2026-11-13T09:07:00+05:30", "1", "2", "1", "1.5"),  # pre-market, off the 09:15 grid
        raw("2026-11-13T09:10:00+05:30", "100", "99", "98", "98.5"),  # pre-market, bad OHLC
        raw("2026-11-13T09:15:00+05:30", "1", "2", "1", "1.5"),
    ]
    result = normalize_candles(rows, DAY, CLOSE)
    assert not result.problems and list(result.session.candles) == [time(9, 15)]


def test_off_grid_candle_inside_the_session_is_still_contradictory():
    result = normalize_candles([raw("2026-11-13T12:02:00+05:30", "1", "2", "1", "1.5")], DAY, CLOSE)
    assert result.session is None and "12:02:00" in result.problems[0]


def test_unparseable_volume_and_extreme_epoch_become_problems_not_crashes():
    bad_volume = normalize_candles([raw("2026-11-13T15:25:00+05:30", "1", "2", "1", "1.5", "abc")], DAY, CLOSE)
    assert bad_volume.session is None and "Candle at 15:25 is invalid" in bad_volume.problems[0]
    bad_epoch = normalize_candles([RawCandle(10**20, "1", "2", "1", "1.5")], DAY, CLOSE)
    assert bad_epoch.session is None and "out of range" in bad_epoch.problems[0]
