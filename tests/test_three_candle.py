"""09:45 three-candle variant, THREE_CANDLE_0945_REVERSAL_SPEC.md acceptance cases T01-T26.

All prices are SYNTHETIC (spec section 10): reference range 100.00 to 110.00 from the
09:45, 09:50 and 09:55 candles; finalized when the 09:55 candle closes at 10:00.
"""

from datetime import time
from decimal import Decimal

from helpers import evaluate, make_service
from trading_scanner.market import THREE_CANDLE_0945, next_slot as following_slot
from trading_scanner.models import BreakoutSide, ResultState, RuleDecisionCode, ScanRequest, Signal
from trading_scanner.synthetic import three_candle_session

D = Decimal
W = THREE_CANDLE_0945


def run(session, at="15:30", through=None):
    return evaluate(session, at=at, through=through, window=W)


def short_at(slot="10:00", next_slot="10:05", next_open="98.80"):
    entry_slot = following_slot(time.fromisoformat(next_slot)).strftime("%H:%M")
    return three_candle_session("short").set(slot, "101.00", "101.50", "98.50", "99.00").set(
        next_slot, next_open, "99.20", "98.10", "98.40"
    ).set(
        entry_slot, next_open, "99.20", "98.10", "98.40"
    )


def long_at(slot="10:00", next_slot="10:05", next_open="111.20"):
    entry_slot = following_slot(time.fromisoformat(next_slot)).strftime("%H:%M")
    return three_candle_session("long").set(slot, "108.00", "111.50", "107.80", "111.00").set(
        next_slot, next_open, "111.90", "110.60", "111.40"
    ).set(
        entry_slot, next_open, "111.90", "110.60", "111.40"
    )


def test_window_definition_matches_the_spec():
    assert W.reference_slots == (time(9, 45), time(9, 50), time(9, 55))
    assert W.earlier_slots[0] == time(9, 15) and W.earlier_slots[-1] == time(9, 40) and len(W.earlier_slots) == 6
    assert len(W.qualification_slots) == 9 and W.range_final_at == time(10, 0) and W.post_slots[0] == time(10, 0)


def test_t01_exactly_the_three_candles_define_the_range():
    result = run(short_at())
    assert [c.start.strftime("%H:%M") for c in result.reference_candles] == ["09:45", "09:50", "09:55"]
    assert (result.qualification.reference.low, result.qualification.reference.high) == (D("100.00"), D("110.00"))
    assert result.qualification.high.earlier_value == D("108.00") and result.qualification.low.earlier_value == D("95.00")


def test_t02_reference_forming_before_1000():
    result = run(three_candle_session("short"), at="09:58", through="09:55")
    assert result.state is ResultState.WAITING_FOR_REFERENCE
    assert "final when the 09:55 candle closes at 10:00" in result.reason
    assert run(three_candle_session("short"), at="10:00", through="09:55").state is ResultState.WAITING_FOR_BREAKOUT


def test_t03_short_pass_enters_after_the_later_confirmation_at_1010():
    result = run(short_at())
    assert result.qualification.permitted_signal is Signal.SHORT
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.SHORT
    assert result.trigger.candle.start.strftime("%H:%M") == "10:00"
    assert result.breakout.candle.start.strftime("%H:%M") == "10:05"
    assert result.breakout.confirmed_at.strftime("%H:%M") == "10:10"
    assert result.entry.candle.start.strftime("%H:%M") == "10:10" and result.entry.price == D("98.80")


def test_t04_long_pass_enters_after_the_later_confirmation_at_1010():
    result = run(long_at())
    assert result.qualification.permitted_signal is Signal.LONG
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.LONG
    assert result.trigger.candle.start.strftime("%H:%M") == "10:00"
    assert result.breakout.candle.start.strftime("%H:%M") == "10:05"
    assert result.entry.candle.start.strftime("%H:%M") == "10:10" and result.entry.price == D("111.20")


def test_t05_setup_rejection_even_if_price_later_crosses():
    session = three_candle_session("long").set("09:20", "97.00", "98.00", "95.00", "96.50")  # earlier 115 high, 95 low
    session.set("10:00", "108.00", "111.50", "107.80", "111.00")
    result = run(session)
    assert result.state is ResultState.NOT_QUALIFIED and result.entry is None
    assert "09:15-09:55 session extreme is in the 09:45-09:55 reference candles" in result.reason


def test_t06_t07_t08_wrong_direction_breach_cancels_without_revival():
    long_cancel = three_candle_session("long").set("10:00", "101.00", "101.50", "98.50", "99.00").set(
        "11:00", "108.00", "111.50", "107.80", "111.00"
    )
    result = run(long_cancel)
    assert result.state is ResultState.SETUP_CANCELLED and result.cancellation.side is BreakoutSide.BELOW
    # The 09:45 LONG now cancels on the low breach itself (a wick suffices), with no invented breach time.
    assert result.cancellation.candle.start.strftime("%H:%M") == "10:00"
    assert result.cancellation.confirmed_at is None and result.entry is None
    short_cancel = three_candle_session("short").set("10:00", "108.00", "111.50", "107.80", "111.00").set(
        "11:00", "101.00", "101.50", "98.50", "99.00"
    )
    assert run(short_cancel).state is ResultState.SETUP_CANCELLED


def test_t09_wick_beyond_the_entry_side_does_not_enter():
    session = three_candle_session("short").set("10:00", "102.00", "102.50", "99.00", "101.00")
    assert run(session).state is ResultState.NO_BREAKOUT


def test_t10_wick_beyond_the_cancelling_side_now_cancels_both_directions():
    short_wick = short_at("11:00", "11:05").set("10:00", "108.00", "111.00", "107.50", "109.00")
    assert run(short_wick).state is ResultState.SETUP_CANCELLED
    long_wick = long_at("11:00", "11:05").set("10:00", "102.00", "102.50", "99.00", "101.00")
    result = run(long_wick)
    assert result.state is ResultState.SETUP_CANCELLED and result.cancellation.side is BreakoutSide.BELOW
    assert result.entry is None


def test_t11_boundary_closes_neither_enter_nor_cancel():
    session = three_candle_session("short").set("10:00", "101.00", "101.50", "99.80", "100.00").set(
        "10:30", "108.50", "110.00", "108.00", "110.00"
    )
    assert run(session).state is ResultState.NO_BREAKOUT


def test_t12_forming_later_candle_confirms_nothing_yet():
    session = three_candle_session("short").set("10:00", "101.00", "101.20", "98.90", "99.00")
    result = run(session, at="10:03", through="10:00")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION and result.breakout is None


def test_t13_delayed_reversal_without_deadline():
    result = run(short_at("12:00", "12:05", "99.00"))
    assert result.entry.candle.start.strftime("%H:%M") == "12:10" and result.entry.price == D("99.00")


def test_t14_missing_earlier_candle_is_invalid():
    result = run(three_candle_session("short").drop("09:30"))
    assert result.state is ResultState.INVALID_DATA and "earlier morning extreme" in result.reason


def test_t15_missing_reference_candle_is_invalid():
    result = run(short_at().drop("09:50"))
    assert result.state is ResultState.INVALID_DATA
    assert "fewer than three reference candles" in result.reason and result.missing_slots == (time(9, 50),)


def test_t16_missing_later_candle_blocks_the_first_decisive_close():
    result = run(short_at("11:00", "11:05").drop("10:15"))
    assert result.state is ResultState.INVALID_DATA and time(10, 15) in result.missing_slots


def test_t17_missing_next_open_is_never_skipped():
    result = run(short_at().drop("10:10"))
    assert result.state is ResultState.INVALID_DATA and result.entry.price is None


def test_t18_entry_candle_closing_back_inside_keeps_the_entry_open():
    session = short_at().set("10:10", "98.80", "104.00", "98.10", "103.00")  # entry closes back inside
    assert run(session).entry.price == D("98.80")


def test_t19_later_new_extreme_does_not_recompute_qualification():
    base = run(short_at())
    later = run(short_at().set("13:00", "105.00", "130.00", "104.00", "106.00"))
    assert later.qualification == base.qualification and later.state is ResultState.ENTRY_IDENTIFIED


def test_t20_both_sides_or_tie_need_rule_decisions():
    both = three_candle_session("short").set("09:20", "104.00", "105.00", "103.00", "104.50")  # earlier low 103
    assert run(both).rule_decision is RuleDecisionCode.BOTH_SIDES_QUALIFIED
    tie = three_candle_session("short").set("09:30", "105.00", "110.00", "104.50", "107.00")  # earlier high 110
    assert run(tie).rule_decision is RuleDecisionCode.EQUAL_REPEATED_EXTREME


def test_t21_permitted_gap_keeps_the_open_gap_policy():
    session = three_candle_session("short").set("10:00", "99.50", "99.80", "98.90", "99.00")
    assert run(session).rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE


def test_t22_prohibited_gap_cancels():
    session = three_candle_session("short").set("10:00", "111.50", "112.40", "111.20", "112.00")
    result = run(session)
    assert result.state is ResultState.SETUP_CANCELLED and result.rule_decision is None


def test_t23_complete_day_inside_the_range_is_no_breakout():
    result = run(three_candle_session("short"))
    assert result.state is ResultState.NO_BREAKOUT and "No candle from 10:00 to 15:25" in result.reason


def test_t24_last_candle_breakout_has_no_same_session_entry():
    session = three_candle_session("short").set("15:25", "101.00", "101.20", "98.80", "99.00")
    assert run(session).state is ResultState.ENTRY_UNAVAILABLE_SESSION_END


def test_t26_risk_fields_through_the_service():
    response = make_service(stop_loss_enabled=True).scan(  # STOP_LOSS_ENABLED=true
        ScanRequest(trading_date="2026-11-13", stocks=["SYN-0945-SHORT"], provider="fixture")
    )
    (result,) = [r for r in response.results if r.strategy_window == "0945_three_candle"]
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.strategy_window == "0945_three_candle"
    assert result.qualification.window == "09:15-09:55"
    # THREE_CANDLE_0945_STOP_LOSS_SPEC.md later taught the initial stop level; everything else stays null.
    risk = result.risk.model_dump()
    assert risk.pop("stop_loss") == D("110.00") and "reference high" in risk.pop("stop_loss_basis")
    assert risk.pop("reason").startswith("Initial stop-loss level") and all(v is None for v in risk.values())


def test_windows_are_independent_and_never_combined():
    session = short_at()
    assert run(session).state is ResultState.ENTRY_IDENTIFIED
    original = evaluate(session)  # the 10:30 window sees its own (inside-range) group only
    assert [c.start.strftime("%H:%M") for c in original.reference_candles] == ["10:30", "10:35", "10:40", "10:45"]
    assert original.entry is None or original.entry.candle.start.strftime("%H:%M") != "10:05"
