"""10:50 two-candle variant, TWO_CANDLE_1050_REVERSAL_SPEC.md acceptance cases P01-P26.

All prices are SYNTHETIC (spec section 10): reference range 100.00 to 110.00 from the
10:50 and 10:55 candles, compared with the nineteen earlier candles 09:15-10:45; finalized
when the 10:55 candle closes at 11:00.
"""

from datetime import time
from decimal import Decimal

from helpers import evaluate, make_service
from trading_scanner.market import THREE_CANDLE_0945, TWO_CANDLE_1050
from trading_scanner.models import BreakoutSide, ResultState, RuleDecisionCode, ScanRequest, Signal
from trading_scanner.synthetic import two_candle_session

D = Decimal
W = TWO_CANDLE_1050


def run(session, at="15:30", through=None):
    return evaluate(session, at=at, through=through, window=W)


def short_at(slot="11:00", next_slot="11:05", next_open="98.80"):
    return two_candle_session("short").set(slot, "101.00", "101.50", "98.50", "99.00").set(
        next_slot, next_open, "99.20", "98.10", "98.40"
    )


def long_at(slot="11:00", next_slot="11:05", next_open="111.20"):
    return two_candle_session("long").set(slot, "108.00", "111.50", "107.80", "111.00").set(
        next_slot, next_open, "111.90", "110.60", "111.40"
    )


def test_window_definition_matches_the_spec():
    assert W.reference_slots == (time(10, 50), time(10, 55))
    assert W.earlier_slots[0] == time(9, 15) and W.earlier_slots[-1] == time(10, 45) and len(W.earlier_slots) == 19
    assert len(W.qualification_slots) == 21 and W.range_final_at == time(11, 0) and W.post_slots[0] == time(11, 0)
    assert W.post_slots[-1] == time(15, 25)  # the session end does not move with the window


def test_p01_exactly_the_two_candles_define_the_range():
    result = run(short_at())
    assert [c.start.strftime("%H:%M") for c in result.reference_candles] == ["10:50", "10:55"]
    q = result.qualification
    assert (q.reference.low, q.reference.high) == (D("100.00"), D("110.00"))
    assert q.reference.high_slots == (time(10, 50),) and q.reference.low_slots == (time(10, 55),)  # the whole group
    assert q.high.earlier_value == D("108.00") and q.low.earlier_value == D("95.00")
    # 10:45, the last candle of the 10:30 group, is an earlier comparison candle and never widens this range.
    neighbour = run(short_at().set("10:45", "104.00", "109.80", "99.50", "104.50"))
    assert (neighbour.qualification.reference.low, neighbour.qualification.reference.high) == (D("100.00"), D("110.00"))
    assert neighbour.qualification.high.earlier_slots == (time(10, 45),)
    assert neighbour.state is ResultState.ENTRY_IDENTIFIED


def test_p02_reference_forming_before_1100():
    result = run(two_candle_session("short"), at="10:58", through="10:55")
    assert result.state is ResultState.WAITING_FOR_REFERENCE and result.qualification is None and result.entry is None
    assert "final when the 10:55 candle closes at 11:00" in result.reason
    assert run(two_candle_session("short"), at="11:00", through="10:55").state is ResultState.WAITING_FOR_BREAKOUT


def test_p03_short_pass_enters_at_the_1105_open():
    result = run(short_at())
    assert result.qualification.permitted_signal is Signal.SHORT
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.SHORT
    assert result.breakout.candle.start.strftime("%H:%M") == "11:00"
    assert result.breakout.confirmed_at.strftime("%H:%M") == "11:05"
    assert result.entry.candle.start.strftime("%H:%M") == "11:05" and result.entry.price == D("98.80")


def test_p04_long_pass_enters_at_the_1105_open():
    result = run(long_at())
    q = result.qualification
    assert q.high.earlier_value == D("115.00") and q.low.earlier_value == D("103.00")
    assert q.permitted_signal is Signal.LONG
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.LONG
    assert result.breakout.candle.start.strftime("%H:%M") == "11:00"
    assert result.entry.candle.start.strftime("%H:%M") == "11:05" and result.entry.price == D("111.20")


def test_p05_not_qualified_even_if_price_later_crosses():
    session = two_candle_session("long").set("09:20", "97.00", "98.00", "95.00", "96.50")  # earlier 115 high, 95 low
    session.set("11:00", "108.00", "111.50", "107.80", "111.00").set("12:00", "101.00", "101.50", "98.50", "99.00")
    result = run(session)
    assert result.state is ResultState.NOT_QUALIFIED and result.entry is None and result.breakout is None
    assert "09:15-10:55 session extreme is in the 10:50-10:55 reference candles" in result.reason
    # The 10:30 group is part of this window's earlier comparison: a 112.00 high at 10:40 also disqualifies.
    high_in_1030_group = two_candle_session("short").set("10:40", "105.00", "112.00", "104.50", "107.00")
    assert run(high_in_1030_group).state is ResultState.NOT_QUALIFIED


def test_p06_p07_p08_wrong_direction_close_cancels_without_revival():
    long_cancel = two_candle_session("long").set("11:00", "101.00", "101.50", "98.50", "99.00").set(
        "12:00", "108.00", "111.50", "107.80", "111.00"
    )
    result = run(long_cancel)
    assert result.state is ResultState.SETUP_CANCELLED and result.cancellation.side is BreakoutSide.BELOW
    assert result.cancellation.candle.start.strftime("%H:%M") == "11:00"
    assert result.cancellation.confirmed_at.strftime("%H:%M") == "11:05" and result.entry is None
    assert result.breakout is None and result.setup_qualified is True  # no SHORT, no later LONG; still qualified
    short_cancel = two_candle_session("short").set("11:00", "108.00", "111.50", "107.80", "111.00").set(
        "12:00", "101.00", "101.50", "98.50", "99.00"
    )
    result = run(short_cancel)
    assert result.state is ResultState.SETUP_CANCELLED and result.cancellation.side is BreakoutSide.ABOVE
    assert result.cancellation.confirmed_at.strftime("%H:%M") == "11:05" and result.entry is None
    assert result.breakout is None


def test_p09_wick_beyond_the_entry_side_does_not_enter():
    short_wick = two_candle_session("short").set("11:00", "102.00", "102.50", "99.00", "101.00")
    long_wick = two_candle_session("long").set("11:00", "108.00", "111.00", "107.50", "109.00")
    for session in (short_wick, long_wick):
        result = run(session)
        assert result.state is ResultState.NO_BREAKOUT and result.breakout is None


def test_p10_wick_beyond_the_cancelling_side_does_not_cancel():
    short_wick = short_at("12:00", "12:05").set("11:00", "108.00", "111.00", "107.50", "109.00")
    long_wick = long_at("12:00", "12:05").set("11:00", "102.00", "102.50", "99.00", "101.00")
    for session in (short_wick, long_wick):
        result = run(session)
        assert result.state is ResultState.ENTRY_IDENTIFIED and result.cancellation is None
        assert result.entry.candle.start.strftime("%H:%M") == "12:05"


def test_p11_boundary_closes_neither_enter_nor_cancel():
    for side in ("short", "long"):
        session = two_candle_session(side).set("11:00", "101.00", "101.50", "99.80", "100.00").set(
            "11:30", "108.50", "110.40", "108.00", "110.00"
        )
        result = run(session)
        assert result.state is ResultState.NO_BREAKOUT and result.breakout is None and result.cancellation is None


def test_p12_forming_later_candle_confirms_nothing_yet():
    permitted = two_candle_session("short").set("11:00", "101.00", "101.20", "98.90", "99.00")
    result = run(permitted, at="11:03", through="11:00")
    assert result.state is ResultState.WAITING_FOR_BREAKOUT and result.breakout is None
    assert any("11:00 candle is still forming" in note for note in result.notes)
    prohibited = two_candle_session("short").set("11:00", "108.00", "111.40", "107.80", "111.00")
    result = run(prohibited, at="11:03", through="11:00")
    assert result.state is ResultState.WAITING_FOR_BREAKOUT and result.cancellation is None
    # Once the 11:00 candle closes at 11:05 it decides: a breakout awaiting the 11:05 open, or a cancellation.
    assert run(permitted, at="11:05", through="11:00").state is ResultState.AWAITING_ENTRY
    assert run(prohibited, at="11:05", through="11:00").state is ResultState.SETUP_CANCELLED


def test_p13_delayed_confirmation_without_deadline():
    result = run(short_at("12:00", "12:05", "99.00"))
    assert result.breakout.candle.start.strftime("%H:%M") == "12:00"
    assert result.entry.candle.start.strftime("%H:%M") == "12:05" and result.entry.price == D("99.00")


def test_p14_missing_earlier_candle_is_invalid():
    # The first earlier candle, one inside the 09:45 group, and the last one before 10:50.
    for label, slot in (("09:15", time(9, 15)), ("09:50", time(9, 50)), ("10:45", time(10, 45))):
        result = run(short_at().drop(label))
        assert result.state is ResultState.INVALID_DATA and "earlier morning extreme" in result.reason
        assert result.missing_slots == (slot,) and result.qualification is None


def test_p15_missing_reference_candle_is_invalid():
    for label, slot in (("10:50", time(10, 50)), ("10:55", time(10, 55))):
        result = run(short_at().drop(label))
        assert result.state is ResultState.INVALID_DATA and result.qualification is None
        assert "fewer than two reference candles" in result.reason and result.missing_slots == (slot,)


def test_p16_missing_later_candle_blocks_the_first_decisive_close():
    for label, slot in (("11:00", time(11, 0)), ("11:30", time(11, 30))):
        result = run(short_at("12:00", "12:05").drop(label))  # proposed breakout at 12:00
        assert result.state is ResultState.INVALID_DATA and result.entry is None and slot in result.missing_slots
    cancel_after_gap = two_candle_session("short").set("12:00", "108.00", "111.50", "107.80", "111.00").drop("11:30")
    result = run(cancel_after_gap)  # proposed cancellation at 12:00
    assert result.state is ResultState.INVALID_DATA and result.cancellation is None
    # Coverage is required only through the first decisive close: a gap after the 11:00 breakout does not matter.
    assert run(short_at().drop("11:30")).state is ResultState.ENTRY_IDENTIFIED


def test_p17_missing_next_open_is_never_skipped():
    result = run(short_at().drop("11:05"))
    assert result.state is ResultState.INVALID_DATA and result.entry.price is None and result.entry.candle is None
    assert result.entry.expected_start.strftime("%H:%M") == "11:05" and result.missing_slots == (time(11, 5),)


def test_p18_entry_candle_closing_back_inside_keeps_the_entry_open():
    session = short_at().set("11:05", "98.80", "104.00", "98.10", "103.00")  # closes back inside the range
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.price == D("98.80")


def test_p19_both_sides_or_tie_need_rule_decisions():
    cases = (
        ("09:20", ("104.00", "105.00", "103.00", "104.50"), RuleDecisionCode.BOTH_SIDES_QUALIFIED),  # earlier low 103
        ("10:00", ("105.00", "110.00", "104.50", "107.00"), RuleDecisionCode.EQUAL_REPEATED_EXTREME),  # high tie
        ("09:20", ("101.00", "102.00", "100.00", "101.50"), RuleDecisionCode.EQUAL_REPEATED_EXTREME),  # low tie
    )
    for slot, row, code in cases:
        result = run(short_at().set(slot, *row))  # the later 11:00 close below 100.00 must not pick a direction
        assert result.state is ResultState.NEEDS_RULE_DECISION and result.rule_decision is code
        assert result.entry is None and result.breakout is None


def test_p20_permitted_gap_keeps_the_open_gap_policy():
    result = run(two_candle_session("short").set("11:00", "99.50", "99.80", "98.90", "99.00"))
    assert result.rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE and result.entry is None
    assert result.breakout.entirely_beyond and result.breakout.candle.start.strftime("%H:%M") == "11:00"
    long_gap = two_candle_session("long").set("11:00", "110.50", "111.50", "110.20", "111.00")
    assert run(long_gap).rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE


def test_p21_prohibited_gap_cancels():
    short_setup = two_candle_session("short").set("11:00", "111.50", "112.40", "111.20", "112.00")
    long_setup = two_candle_session("long").set("11:00", "99.50", "99.80", "98.90", "99.00")
    for session in (short_setup, long_setup):
        result = run(session)
        assert result.state is ResultState.SETUP_CANCELLED and result.rule_decision is None


def test_p22_complete_day_inside_the_range_is_no_breakout():
    for side in ("short", "long"):
        result = run(two_candle_session(side))
        assert result.state is ResultState.NO_BREAKOUT and "No candle from 11:00 to 15:25" in result.reason


def test_p23_last_candle_breakout_has_no_same_session_entry():
    result = run(two_candle_session("short").set("15:25", "101.00", "101.20", "98.80", "99.00"))
    assert result.state is ResultState.ENTRY_UNAVAILABLE_SESSION_END
    assert result.breakout.candle.start.strftime("%H:%M") == "15:25"
    assert result.entry.price is None and result.entry.expected_start is None  # no next trading day's open


def test_p24_later_adverse_move_preserves_the_entry():
    base = run(short_at())
    # After the 11:05 SHORT entry: an opposite close above 110.00 at 11:30, then a new session high at 13:00.
    adverse = short_at().set("11:30", "108.00", "111.50", "107.80", "111.00").set(
        "13:00", "105.00", "130.00", "104.00", "106.00"
    )
    result = run(adverse)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry == base.entry and result.cancellation is None
    assert result.qualification == base.qualification  # never recomputed from later candles (section 3)
    long_result = run(long_at().set("11:30", "101.00", "101.50", "98.50", "99.00"))  # closes below 100.00 later
    assert long_result.state is ResultState.ENTRY_IDENTIFIED and long_result.entry.price == D("111.20")


def test_p25_risk_fields_stay_null_through_the_service():
    stocks = ["SYN-1050-SHORT", "SYN-1050-LONG", "SYN-1050-CANCEL"]
    response = make_service().scan(ScanRequest(trading_date="2026-11-13", stocks=stocks, provider="fixture"))
    window_results = [r for r in response.results if r.strategy_window == "1050_two_candle"]
    assert sorted(r.input_name for r in window_results) == sorted(stocks)  # one 10:50 result per stock
    short, long_, cancelled = ({r.input_name: r for r in window_results}[name] for name in stocks)
    assert short.state is ResultState.ENTRY_IDENTIFIED and short.entry.price == D("98.80")
    assert long_.state is ResultState.ENTRY_IDENTIFIED and long_.entry.price == D("111.20")
    assert short.entry.time.strftime("%H:%M") == long_.entry.time.strftime("%H:%M") == "11:05"
    # P24 as served: both entries are followed by closes against the trade (back at 105.00), yet nothing is computed.
    assert max(c.close for c in short.candles if c.start > short.entry.time) > short.entry.price
    assert min(c.close for c in long_.candles if c.start > long_.entry.time) < long_.entry.price
    # Section 7: a cancellation is not a stop-loss hit or a loss, and the setup stays qualified.
    assert cancelled.state is ResultState.SETUP_CANCELLED and cancelled.setup_qualified is True
    assert cancelled.entry is None and cancelled.cancellation.candle_start.strftime("%H:%M") == "11:00"
    for result in window_results:
        assert result.qualification.window == "09:15-10:55"
        risk = result.risk.model_dump()
        assert risk.pop("reason") == "Rules not yet defined" and all(v is None for v in risk.values())


def test_p26_each_window_keeps_its_own_range_and_outcome():
    # The 09:45 group makes its own new high (106.50) and the 10:00 close at 107.00 cancels that SHORT setup.
    session = short_at().set("09:45", "105.00", "106.50", "104.80", "106.00")
    two, four, three = run(session), evaluate(session), evaluate(session, window=THREE_CANDLE_0945)
    assert [c.start.strftime("%H:%M") for c in two.reference_candles] == ["10:50", "10:55"]
    assert [c.start.strftime("%H:%M") for c in four.reference_candles] == ["10:30", "10:35", "10:40", "10:45"]
    assert [c.start.strftime("%H:%M") for c in three.reference_candles] == ["09:45", "09:50", "09:55"]
    ranges = [(r.qualification.reference.low, r.qualification.reference.high) for r in (two, four, three)]
    assert ranges == [(D("100.00"), D("110.00")), (D("103.00"), D("105.00")), (D("103.00"), D("106.50"))]
    assert two.state is ResultState.ENTRY_IDENTIFIED and two.entry.price == D("98.80")
    assert four.state is ResultState.NOT_QUALIFIED and four.entry is None
    assert three.state is ResultState.SETUP_CANCELLED and three.entry is None
    assert three.cancellation.candle.start.strftime("%H:%M") == "10:00"
    # No cross-window effect: without that 09:45 change the 09:45 window has a tie instead of a cancellation,
    # and the 10:50 evaluation is identical either way.
    assert evaluate(short_at(), window=THREE_CANDLE_0945).state is ResultState.NEEDS_RULE_DECISION
    assert run(short_at()) == two
