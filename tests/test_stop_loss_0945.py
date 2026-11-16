"""09:45 initial stop-loss level, THREE_CANDLE_0945_STOP_LOSS_SPEC.md acceptance cases SL01-SL14.

All prices are SYNTHETIC: the reference candles are the spec's section 6 examples (SHORT: the
09:50 upper wick 110.00 sets the stop while the highest close is 108.00; LONG: the 09:50 lower
wick 90.00 sets the stop while the lowest close is 92.00). Only the stop LEVEL is taught; no
stop hit, exit, target, or loss is ever computed. The logic runs only when the STOP_LOSS_ENABLED
switch is true; these tests turn it on explicitly (the test setup clears it, so it is off by default).
"""

from decimal import Decimal

from helpers import WINDOW_0945, WINDOW_1030, WINDOW_1050, evaluate, fixed_clock, in_window, make_service
from datetime import time
from trading_scanner.market import FOUR_CANDLE_1030, THREE_CANDLE_0945, TWO_CANDLE_1050, next_slot as following_slot
from trading_scanner.config import Settings
from trading_scanner.models import ResultState, ScanRequest, Signal
from trading_scanner.service import ScanService
from trading_scanner.synthetic import three_candle_session

D = Decimal
W = THREE_CANDLE_0945


def run(session, at="15:30", through=None, window=W, stop_loss_enabled=True):
    return evaluate(session, at=at, through=through, window=window, stop_loss_enabled=stop_loss_enabled)


def short_example():
    """Spec section 6 SHORT reference candles on a SHORT-qualified morning (earlier high 108.00, low 95.00)."""
    return (
        three_candle_session("short")
        .set("09:45", "104.00", "108.00", "102.00", "107.00")
        .set("09:50", "107.00", "110.00", "101.00", "108.00")
        .set("09:55", "108.00", "109.00", "100.00", "102.00")
    )


def short_entry(session=None, slot="10:00", next_slot="10:05"):
    entry_slot = following_slot(time.fromisoformat(next_slot)).strftime("%H:%M")
    return (session or short_example()).set(slot, "101.00", "101.50", "98.50", "99.00").set(
        next_slot, "98.80", "99.20", "98.10", "98.40"
    ).set(
        entry_slot, "98.80", "99.20", "98.10", "98.40"
    )


def long_example():
    """Spec section 6 LONG reference candles on a LONG-qualified morning (earlier high 115.00, low 103.00)."""
    return (
        three_candle_session("long")
        .set("09:45", "96.00", "100.00", "94.00", "95.00")
        .set("09:50", "95.00", "97.00", "90.00", "92.00")
        .set("09:55", "92.00", "98.00", "91.00", "96.00")
    )


def long_entry(session=None):
    """First break 10:00, later confirmation close 10:05, entry at the 10:10 open 101.20."""
    return (session or long_example()).set("10:00", "98.00", "101.50", "97.80", "101.00").set(
        "10:05", "101.20", "101.90", "100.60", "101.40"
    ).set(
        "10:10", "101.20", "101.90", "100.60", "101.40"
    )


def test_sl01_sl03_short_stop_is_the_highest_high_not_the_highest_close():
    result = run(short_entry())
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.SHORT
    assert result.entry.price == D("98.80")
    assert result.stop_loss == D("110.00")  # the 09:50 upper wick; the highest close is 108.00
    assert result.stop_loss == result.qualification.reference.high
    assert result.stop_loss_basis == "reference high of the 09:45-09:55 candles (09:50), wicks included"
    assert "Initial stop loss 110.00" in result.reason and "not yet defined" in result.reason


def test_sl02_sl04_long_stop_is_the_lowest_low_not_the_lowest_close():
    result = run(long_entry())
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.LONG
    assert result.entry.price == D("101.20")
    assert result.stop_loss == D("90.00")  # the 09:50 lower wick; the lowest close is 92.00
    assert result.stop_loss == result.qualification.reference.low
    assert result.stop_loss_basis == "reference low of the 09:45-09:55 candles (09:50), wicks included"


def test_sl05_extreme_that_is_also_the_close_is_used_as_is():
    session = short_example().set("09:50", "107.00", "110.00", "101.00", "110.00")  # close equals the high
    assert run(short_entry(session)).stop_loss == D("110.00")


def test_sl06_selected_by_price_whichever_candle_holds_it():
    session = short_example().set("09:55", "108.00", "111.00", "100.00", "102.00")  # now 09:55 holds the high
    result = run(short_entry(session))
    assert result.stop_loss == D("111.00") and "(09:55)" in result.stop_loss_basis


def test_sl07_equal_internal_extremes_give_the_same_price():
    session = short_example().set("09:45", "104.00", "110.00", "102.00", "107.00")  # 09:45 and 09:50 both 110.00
    result = run(short_entry(session))
    assert result.stop_loss == D("110.00") and "(09:45, 09:50)" in result.stop_loss_basis


def test_sl08_late_entry_still_uses_the_original_reference_candles():
    result = run(short_entry(slot="13:00", next_slot="13:05"))
    assert result.entry.candle.start.strftime("%H:%M") == "13:10" and result.stop_loss == D("110.00")


def test_sl09_later_candles_never_replace_the_level():
    session = short_entry().set("10:00", "101.00", "109.90", "98.50", "99.00")  # breakout candle high 109.90
    session.set("10:05", "98.80", "105.00", "98.10", "98.40")  # entry candle high 105.00
    assert run(session).stop_loss == D("110.00")


def test_sl10_exact_source_value_without_buffer():
    stop = run(short_entry()).stop_loss
    assert stop == D("110.00") and str(stop) == "110.00"
    assert run(long_entry()).stop_loss == D("90.00")


def test_sl11_invalid_or_unfinished_reference_data_gives_no_level():
    missing = run(short_entry().drop("09:50"))
    assert missing.state is ResultState.INVALID_DATA and missing.stop_loss is None
    forming = run(short_example(), at="09:58", through="09:55")
    assert forming.state is ResultState.WAITING_FOR_REFERENCE and forming.stop_loss is None


def test_sl12_other_windows_get_no_stop():
    assert FOUR_CANDLE_1030.initial_stop_rule is None and TWO_CANDLE_1050.initial_stop_rule is None
    from trading_scanner.synthetic import SyntheticSession, two_candle_session

    ten_thirty = run(SyntheticSession().set("10:50", "101.00", "101.50", "98.50", "99.00").set(
        "10:55", "98.80", "99.20", "98.10", "98.40"), window=FOUR_CANDLE_1030)
    ten_fifty = run(two_candle_session("short").set("11:00", "101.00", "101.50", "98.50", "99.00").set(
        "11:05", "98.80", "99.20", "98.10", "98.40"), window=TWO_CANDLE_1050)
    for result in (ten_thirty, ten_fifty):
        assert result.state is ResultState.ENTRY_IDENTIFIED and result.stop_loss is None


def test_sl13_no_stop_hit_exit_or_loss_even_when_price_trades_through_the_stop():
    session = short_entry().set("10:30", "108.00", "112.00", "107.50", "111.50").set(  # through 110.00 after entry
        "11:00", "111.00", "113.00", "110.50", "112.50"
    )
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.stop_loss == D("110.00")
    assert result.cancellation is None  # after an entry, a later opposite close never cancels it


def test_sl14_no_stop_without_an_unambiguous_direction_or_trade():
    tie = run(short_entry(short_example().set("09:30", "105.00", "110.00", "104.50", "107.00")))  # ties earlier high
    both = run(short_entry(short_example().set("09:20", "104.00", "105.00", "103.00", "104.50")))  # both sides new
    cancelled = run(short_example().set("10:00", "108.00", "111.50", "107.80", "111.00"))  # wrong-way close
    waiting = run(short_example(), at="10:20", through="10:15")  # qualified, no breakout yet
    for result in (tie, both, cancelled, waiting):
        assert result.entry is None or result.entry.price is None
        assert result.stop_loss is None
    assert tie.state is both.state is ResultState.NEEDS_RULE_DECISION
    assert cancelled.state is ResultState.SETUP_CANCELLED and waiting.state is ResultState.WAITING_FOR_BREAKOUT


def test_pending_entry_carries_its_stop_and_last_candle_breakout_does_not():
    awaiting = run(short_entry(), at="10:10", through="10:05")
    assert awaiting.state is ResultState.AWAITING_ENTRY and awaiting.stop_loss == D("110.00")
    session_end = run(short_example().set("15:25", "101.00", "101.20", "98.80", "99.00"))
    assert session_end.state is ResultState.ENTRY_UNAVAILABLE_SESSION_END and session_end.stop_loss is None


def test_api_reports_the_level_and_keeps_every_other_risk_field_null():
    response = make_service(stop_loss_enabled=True).scan(
        ScanRequest(trading_date="2026-11-13", stocks=["SYN-0945-SHORT", "SYN-0945-CANCEL", "SYN-1050-SHORT"], provider="fixture")
    )
    assert response.stop_loss_enabled is True
    by = {(r.input_name, r.strategy_window): r for r in response.results}
    entry = by[("SYN-0945-SHORT", WINDOW_0945)].risk
    assert entry.stop_loss == D("110.00") and entry.stop_loss_basis.startswith("reference high")
    assert entry.reason.startswith("Initial stop-loss level")
    assert (entry.targets, entry.exit_time, entry.exit_price, entry.outcome, entry.profit_loss) == (None,) * 5
    cancelled = by[("SYN-0945-CANCEL", WINDOW_0945)].risk
    assert cancelled.stop_loss is None and cancelled.reason.startswith("No entry, so no stop loss")
    other = by[("SYN-1050-SHORT", WINDOW_1050)].risk
    assert other.stop_loss is None and other.reason == "Rules not yet defined"
    payload = response.model_dump(mode="json")
    served = [r for r in payload["results"] if r["input_name"] == "SYN-0945-SHORT" and r["strategy_window"] == WINDOW_0945]
    assert served[0]["risk"]["stop_loss"] == "110.00"  # decimal string, exact source precision
    assert all(r["risk"]["stop_loss"] is None for r in in_window(payload["results"], WINDOW_1030))


# ------------------------------------------------------- STOP_LOSS_ENABLED switch


def test_switch_off_means_no_stop_from_the_engine():
    result = run(short_entry(), stop_loss_enabled=False)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.price == D("98.80")
    assert result.stop_loss is None and result.stop_loss_basis is None and "stop loss" not in result.reason.lower()


def test_switch_is_off_by_default_and_the_api_says_why():
    response = make_service().scan(ScanRequest(trading_date="2026-11-13", stocks=["SYN-0945-SHORT"], provider="fixture"))
    assert response.stop_loss_enabled is False
    by = {r.strategy_window: r for r in response.results}
    assert by[WINDOW_0945].state is ResultState.ENTRY_IDENTIFIED and by[WINDOW_0945].risk.stop_loss is None
    assert by[WINDOW_0945].risk.reason.startswith("Stop-loss logic is turned off (STOP_LOSS_ENABLED")
    assert by[WINDOW_1030].risk.reason == "Rules not yet defined"  # other windows never had a stop rule


def test_env_true_turns_the_logic_on_through_settings(monkeypatch):
    monkeypatch.setenv("STOP_LOSS_ENABLED", "true")
    service = ScanService(clock=fixed_clock)  # reads STOP_LOSS_ENABLED like the app does at start-up
    assert service.stop_loss_enabled is True
    response = service.scan(ScanRequest(trading_date="2026-11-13", stocks=["SYN-0945-SHORT"], provider="fixture"))
    (result,) = in_window(response.results, WINDOW_0945)
    assert result.risk.stop_loss == D("110.00") and response.stop_loss_enabled is True


def test_only_true_enables_the_switch():
    for raw in ("true", "TRUE", " True ", "1", "yes", "on"):
        assert Settings(_env_file=None, STOP_LOSS_ENABLED=raw).stop_loss_enabled is True, raw
    for raw in ("false", "False", "0", "no", "off", "", "ture", "maybe"):
        assert Settings(_env_file=None, STOP_LOSS_ENABLED=raw).stop_loss_enabled is False, raw
    assert Settings(_env_file=None).stop_loss_enabled is False  # missing line: disabled


def test_health_reports_the_switch():
    from fastapi.testclient import TestClient

    from trading_scanner.api import create_app

    assert TestClient(create_app(make_service())).get("/health").json()["stop_loss_enabled"] is False
    assert TestClient(create_app(make_service(stop_loss_enabled=True))).get("/health").json()["stop_loss_enabled"] is True

