"""Strategy acceptance cases from EXAMPLES.md section 5 (all SYNTHETIC prices)."""

from datetime import time
from decimal import Decimal

from helpers import evaluate
from trading_scanner.models import (
    BreakoutSide,
    ExtremeStatus,
    QualificationDecision,
    ResultState,
    RuleDecisionCode,
    Signal,
)
from trading_scanner.strategy import permits, permitted_signal
from trading_scanner.synthetic import SyntheticSession, low_qualified

D = Decimal

# SyntheticSession() is a high-qualified SHORT setup; low_qualified() is the LONG mirror
# (REVERSAL_DIRECTION_SPEC.md: new morning high -> SHORT only, new morning low -> LONG only).


def long_breakout() -> SyntheticSession:
    return low_qualified().set("11:15", "108.00", "111.50", "107.80", "111.00").set(
        "11:20", "111.20", "111.90", "110.60", "111.40"
    )


def short_breakout(at: str = "10:50") -> SyntheticSession:
    session = SyntheticSession().set(at, "101.00", "101.50", "98.50", "99.00")
    hh, mm = map(int, at.split(":"))
    nxt = f"{hh + (mm + 5) // 60:02d}:{(mm + 5) % 60:02d}"
    return session.set(nxt, "98.80", "99.20", "98.10", "98.40")


# ------------------------------------------------------------ qualification


def test_a01_high_side_alone_qualifies():
    result = evaluate(SyntheticSession())
    q = result.qualification
    assert q.decision is QualificationDecision.QUALIFIED and q.qualifying_sides == ["high"]
    assert q.high.status is ExtremeStatus.NEW_EXTREME and q.low.status is ExtremeStatus.NOT_EXTREME
    assert (q.reference.low, q.reference.high) == (D("100.00"), D("110.00"))
    assert q.session_low == D("99.50") and q.session_low_slots == (time(9, 20),)


def test_a02_low_side_alone_qualifies():
    session = SyntheticSession().set("09:50", "105.00", "111.00", "104.50", "107.00").set(
        "09:20", "103.00", "104.00", "101.00", "101.50"
    )
    q = evaluate(session).qualification
    assert q.decision is QualificationDecision.QUALIFIED and q.qualifying_sides == ["low"]


def test_a03_neither_side_qualifies_and_later_cross_is_not_an_entry():
    session = (
        SyntheticSession()
        .set("09:50", "105.00", "112.00", "104.50", "107.00")
        .set("09:20", "103.00", "104.00", "98.00", "101.00")
        .set("11:00", "108.00", "111.50", "107.80", "111.00")
    )
    result = evaluate(session)
    assert result.state is ResultState.NOT_QUALIFIED and result.setup_qualified is False
    assert result.breakout is None and result.entry is None
    assert "112.00 (09:50)" in result.reason and "98.00 (09:20)" in result.reason


def test_a18_later_new_extreme_does_not_change_qualification():
    base = evaluate(long_breakout())
    later_high = evaluate(long_breakout().set("14:00", "112.00", "130.00", "111.00", "125.00"))
    assert later_high.qualification == base.qualification and later_high.state is ResultState.ENTRY_IDENTIFIED


def test_a19_candle_color_alone_does_not_change_eligibility():
    green = evaluate(SyntheticSession())
    red = evaluate(SyntheticSession().set("10:30", "109.00", "110.00", "104.80", "105.00"))  # open/close swapped
    assert red.qualification.decision == green.qualification.decision
    assert red.qualification.reference.high == green.qualification.reference.high
    assert red.qualification.reference.low == green.qualification.reference.low


def test_a20_equal_repeated_high_needs_rule_decision():
    result = evaluate(SyntheticSession().set("09:50", "105.00", "110.00", "104.50", "107.00"))
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.EQUAL_REPEATED_EXTREME
    assert result.qualification.high.status is ExtremeStatus.EQUAL_TO_EARLIER
    assert result.setup_qualified is None and result.entry is None and result.breakout is None


def test_equal_repeated_low_needs_rule_decision():
    session = SyntheticSession().set("09:50", "105.00", "111.00", "104.50", "107.00").set(
        "09:20", "103.00", "104.00", "100.00", "101.00"
    )
    result = evaluate(session)
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.qualification.low.status is ExtremeStatus.EQUAL_TO_EARLIER


def test_new_extreme_with_tie_on_other_side_cannot_fix_a_direction():
    # High is new, low only ties: under the open tie policy the low side might also qualify.
    session = SyntheticSession().set("09:20", "103.00", "104.00", "100.00", "101.00").set(
        "10:50", "101.00", "101.50", "98.50", "99.00"
    )
    result = evaluate(session)
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.EQUAL_REPEATED_EXTREME
    assert result.setup_qualified is True and result.qualification.permitted_signal is None
    assert result.breakout is None and result.entry is None and "tie policy" in result.reason


def test_equal_highs_within_the_reference_group_are_not_a_tie_problem():
    session = SyntheticSession().set("10:35", "109.00", "110.00", "103.00", "103.50")
    q = evaluate(session).qualification
    assert q.decision is QualificationDecision.QUALIFIED
    assert q.reference.high_slots == (time(10, 30), time(10, 35))


# ------------------------------------------------------------ breakout


def test_a04_a05_wick_only_crossings_do_not_confirm():
    session = (
        SyntheticSession()
        .set("11:00", "108.00", "111.00", "107.50", "109.00")
        .set("11:30", "102.00", "102.50", "99.00", "101.00")
    )
    assert evaluate(session).state is ResultState.NO_BREAKOUT


def test_a06_close_exactly_on_either_boundary_is_not_outside():
    session = (
        SyntheticSession()
        .set("11:10", "108.50", "110.40", "108.00", "110.00")
        .set("11:40", "101.50", "101.80", "99.80", "100.00")
    )
    result = evaluate(session)
    assert result.state is ResultState.NO_BREAKOUT and result.breakout is None


def test_a07_upward_close_gives_long_entry_at_next_open():
    result = evaluate(long_breakout())
    assert result.state is ResultState.ENTRY_IDENTIFIED
    assert result.breakout.side is BreakoutSide.ABOVE and result.breakout.signal is Signal.LONG
    assert result.entry.price == D("111.20")  # not 110.00 and not the 111.00 breakout close
    assert result.entry.candle.start.strftime("%H:%M") == "11:20"


def test_a08_downward_close_gives_short_entry_at_next_open():
    result = evaluate(short_breakout("10:50"))
    assert result.breakout.signal is Signal.SHORT and result.entry.price == D("98.80")
    assert result.breakout.confirmed_at.strftime("%H:%M") == "10:55"


# ------------------------------------------------- direction rule (REVERSAL_DIRECTION_SPEC.md)


def test_permitted_direction_follows_the_qualifying_side():
    new, equal, none = ExtremeStatus.NEW_EXTREME, ExtremeStatus.EQUAL_TO_EARLIER, ExtremeStatus.NOT_EXTREME
    assert permitted_signal(new, none) is Signal.SHORT  # morning high -> short
    assert permitted_signal(none, new) is Signal.LONG  # morning low -> long
    assert permitted_signal(new, new) is None and permitted_signal(new, equal) is None
    assert permitted_signal(none, none) is None
    assert permits(Signal.SHORT, BreakoutSide.BELOW) and not permits(Signal.SHORT, BreakoutSide.ABOVE)
    assert permits(Signal.LONG, BreakoutSide.ABOVE) and not permits(Signal.LONG, BreakoutSide.BELOW)


def test_dir01_high_setup_shorts_below_the_range():
    result = evaluate(short_breakout("11:30"))
    assert result.qualification.qualifying_sides == ["high"]
    assert result.qualification.permitted_signal is Signal.SHORT
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.SHORT
    assert result.breakout.permitted is True and result.entry.price == D("98.80")


def test_dir02_can02_high_setup_cancels_on_a_close_above_and_is_not_revived():
    session = SyntheticSession().set("11:15", "108.00", "111.50", "107.80", "111.00").set(
        "12:00", "101.00", "101.20", "98.60", "99.10"  # CAN-07: a later permitted close does not revive it
    ).set("12:05", "99.00", "99.40", "98.20", "98.50")
    result = evaluate(session)
    assert result.state is ResultState.SETUP_CANCELLED and result.setup_qualified is True
    assert result.cancellation.side is BreakoutSide.ABOVE and result.cancellation.candle.close == D("111.00")
    assert result.cancellation.candle.start.strftime("%H:%M") == "11:15"
    assert result.cancellation.confirmed_at.strftime("%H:%M") == "11:20"
    assert result.breakout is None and result.entry is None and result.rule_decision is None
    assert "Setup cancelled" in result.reason and "does not revive" in result.reason


def test_dir03_low_setup_goes_long_above_the_range():
    result = evaluate(long_breakout())
    assert result.qualification.qualifying_sides == ["low"]
    assert result.qualification.permitted_signal is Signal.LONG
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.LONG


def test_dir04_can01_low_setup_cancels_on_a_close_below():
    result = evaluate(low_qualified().set("11:30", "101.00", "101.20", "98.60", "99.00"))
    assert result.state is ResultState.SETUP_CANCELLED
    assert result.cancellation.side is BreakoutSide.BELOW and result.entry is None


def test_can03_can04_wick_beyond_the_prohibited_boundary_does_not_cancel():
    long_wick = long_breakout().set("11:00", "102.00", "102.50", "99.00", "101.00")  # low 99, close inside
    assert evaluate(long_wick).state is ResultState.ENTRY_IDENTIFIED
    short_wick = short_breakout("11:30").set("11:00", "108.00", "111.00", "107.50", "109.00")  # high 111, close inside
    assert evaluate(short_wick).state is ResultState.ENTRY_IDENTIFIED


def test_can05_close_exactly_on_the_prohibited_boundary_does_not_cancel():
    assert evaluate(long_breakout().set("11:00", "101.00", "101.50", "99.80", "100.00")).state is ResultState.ENTRY_IDENTIFIED
    assert evaluate(short_breakout("11:30").set("11:00", "108.50", "110.40", "108.00", "110.00")).state is ResultState.ENTRY_IDENTIFIED


def test_can06_forming_candle_beyond_the_prohibited_boundary_does_not_cancel_yet():
    session = SyntheticSession().set("11:00", "108.00", "111.40", "107.90", "111.00")
    result = evaluate(session, at="11:03", through="11:00")
    assert result.state is ResultState.WAITING_FOR_BREAKOUT and result.cancellation is None
    assert evaluate(session, at="11:05", through="11:00").state is ResultState.SETUP_CANCELLED


def test_can08_entry_survives_a_later_wrong_way_close():
    session = long_breakout().set("12:00", "101.00", "101.20", "98.60", "99.00")  # after the 11:20 entry
    result = evaluate(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.price == D("111.20")
    assert result.cancellation is None


def test_wrong_way_wick_does_not_block_a_later_permitted_close():
    session = (
        SyntheticSession()
        .set("11:00", "108.00", "111.00", "107.50", "109.00")  # wick above, close inside
        .set("12:00", "101.00", "101.20", "98.60", "99.10")
        .set("12:05", "99.00", "99.40", "98.20", "98.50")
    )
    result = evaluate(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.signal is Signal.SHORT


def test_both_sides_qualifying_needs_a_direction_decision():
    session = SyntheticSession().set("09:20", "103.00", "104.00", "101.00", "101.50").set(
        "10:50", "101.00", "101.50", "98.50", "99.00"
    )
    result = evaluate(session)
    assert result.qualification.qualifying_sides == ["high", "low"]
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.BOTH_SIDES_QUALIFIED
    assert result.setup_qualified is True and result.breakout is None and result.entry is None


def test_wrong_direction_close_cancels_even_when_it_gaps_beyond_the_range():
    session = SyntheticSession().set("11:00", "111.50", "112.40", "111.20", "112.00")  # entirely above
    result = evaluate(session)
    assert result.state is ResultState.SETUP_CANCELLED and result.rule_decision is None


def test_a09_delayed_breakout_with_no_deadline():
    session = SyntheticSession().set("12:00", "101.00", "101.20", "98.60", "99.10").set(
        "12:05", "99.00", "99.40", "98.20", "98.50"
    )
    result = evaluate(session)
    assert result.breakout.candle.start.strftime("%H:%M") == "12:00"
    assert result.breakout.confirmed_at.strftime("%H:%M") == "12:05"
    assert result.entry.candle.start.strftime("%H:%M") == "12:05" and result.entry.price == D("99.00")


def test_late_afternoon_breakout_is_still_valid():
    session = SyntheticSession().set("15:15", "101.00", "101.20", "98.80", "99.00").set(
        "15:20", "98.90", "99.30", "98.50", "98.70"
    )
    assert evaluate(session).state is ResultState.ENTRY_IDENTIFIED


def test_hcl_style_timing_breakout_at_1100_enters_at_1105_open():
    session = SyntheticSession().set("11:00", "101.00", "101.40", "98.70", "99.00").set(
        "11:05", "98.90", "99.00", "98.20", "98.40"
    )
    result = evaluate(session)
    assert result.breakout.candle.start.strftime("%H:%M") == "11:00"
    assert result.breakout.candle.end.strftime("%H:%M") == "11:05"
    assert result.entry.candle.start.strftime("%H:%M") == "11:05" and result.entry.price == D("98.90")


def test_a10_forming_candle_cannot_confirm():
    session = SyntheticSession().set("11:00", "101.00", "101.20", "98.90", "99.00")
    result = evaluate(session, at="11:03", through="11:00")
    assert result.state is ResultState.WAITING_FOR_BREAKOUT and result.breakout is None
    assert any("still forming" in note for note in result.notes)


def test_breakout_confirms_exactly_when_candle_closes():
    session = SyntheticSession().set("11:00", "101.00", "101.20", "98.90", "99.00")
    assert evaluate(session, at="11:04", through="11:00").state is ResultState.WAITING_FOR_BREAKOUT
    assert evaluate(session, at="11:05", through="11:00").state is ResultState.AWAITING_ENTRY


def test_a11_awaiting_entry_when_next_candle_not_yet_available():
    session = SyntheticSession().set("11:00", "101.00", "101.40", "98.70", "99.00")
    result = evaluate(session, at="11:05", through="11:00")
    assert result.state is ResultState.AWAITING_ENTRY
    assert result.entry.expected_start.strftime("%H:%M") == "11:05" and result.entry.price is None


def test_entry_does_not_wait_for_entry_candle_to_close():
    result = evaluate(long_breakout(), at="11:22", through="11:20")
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.price == D("111.20")


def test_a17_later_reversal_keeps_original_entry():
    base = evaluate(long_breakout())
    reversed_later = evaluate(
        long_breakout().set("12:00", "106.00", "106.50", "98.00", "98.50").set("12:05", "98.40", "99.00", "97.00", "97.50")
    )
    assert reversed_later == base and reversed_later.state is ResultState.ENTRY_IDENTIFIED


def test_a21_entire_candle_beyond_range_needs_gap_decision():
    session = (
        SyntheticSession()
        .set("11:00", "99.50", "99.80", "98.90", "99.00")  # entirely below the 100.00 low
        .set("11:05", "98.90", "99.10", "98.40", "98.60")
        .set("12:00", "101.00", "101.20", "98.60", "99.10")  # a later ordinary breakout is not searched for
    )
    result = evaluate(session)
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE
    assert result.breakout.entirely_beyond and result.breakout.candle.start.strftime("%H:%M") == "11:00"
    assert result.entry is None and result.setup_qualified is True


def test_breakout_that_opens_beyond_but_trades_back_through_is_ordinary():
    session = low_qualified().set("11:00", "110.50", "112.00", "109.80", "111.50").set(
        "11:05", "111.60", "112.00", "111.00", "111.80"
    )
    result = evaluate(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and not result.breakout.entirely_beyond


def test_breakout_candle_touching_the_boundary_is_ordinary():
    session = low_qualified().set("11:00", "110.50", "112.00", "110.00", "111.50").set(
        "11:05", "111.60", "112.00", "111.00", "111.80"
    )
    assert evaluate(session).state is ResultState.ENTRY_IDENTIFIED


def test_a22_breakout_on_last_candle_has_no_entry():
    result = evaluate(SyntheticSession().set("15:25", "101.00", "101.20", "98.80", "99.00"))
    assert result.state is ResultState.ENTRY_UNAVAILABLE_SESSION_END
    assert result.entry.price is None and result.entry.expected_start is None
    assert result.breakout.confirmed_at.strftime("%H:%M") == "15:30"


def test_a24_no_breakout_all_day():
    result = evaluate(SyntheticSession())
    assert result.state is ResultState.NO_BREAKOUT and result.entry is None


def test_a25_only_first_breakout_is_reported():
    session = long_breakout().set("13:00", "101.00", "101.20", "98.60", "99.10").set(
        "13:05", "99.00", "99.40", "98.20", "98.50"
    )
    result = evaluate(session)
    assert result.breakout.signal is Signal.LONG and result.entry.price == D("111.20")


# ------------------------------------------------------------ coverage


def test_waiting_for_reference_until_1045_candle_closes():
    assert evaluate(SyntheticSession(), at="10:42", through="10:40").state is ResultState.WAITING_FOR_REFERENCE
    assert evaluate(SyntheticSession(), at="10:49", through="10:45").state is ResultState.WAITING_FOR_REFERENCE
    assert evaluate(SyntheticSession(), at="10:50", through="10:45").state is ResultState.WAITING_FOR_BREAKOUT


def test_a12_missing_reference_candle_is_invalid():
    result = evaluate(SyntheticSession().drop("10:35"))
    assert result.state is ResultState.INVALID_DATA and result.missing_slots == (time(10, 35),)
    assert result.qualification is None and "fewer than four reference candles" in result.reason


def test_a13_missing_morning_candle_is_invalid():
    result = evaluate(SyntheticSession().drop("09:15"))
    assert result.state is ResultState.INVALID_DATA and "earlier morning extreme" in result.reason


def test_a14_missing_candle_before_breakout_blocks_first_breakout():
    session = SyntheticSession().drop("11:30").set("12:00", "101.00", "101.20", "98.60", "99.10")
    result = evaluate(session)
    assert result.state is ResultState.INVALID_DATA
    assert result.breakout is None and result.entry is None and time(11, 30) in result.missing_slots


def test_missing_candle_after_entry_does_not_matter():
    result = evaluate(long_breakout().drop("13:00", "14:00"))
    assert result.state is ResultState.ENTRY_IDENTIFIED


def test_a15_missing_immediate_next_candle_is_never_skipped():
    result = evaluate(long_breakout().drop("11:20"))
    assert result.state is ResultState.INVALID_DATA
    assert result.missing_slots == (time(11, 20),)
    assert result.breakout is not None and result.entry.price is None


def test_gap_inside_an_in_progress_session_is_invalid():
    result = evaluate(SyntheticSession().drop("10:10"), at="11:00", through="10:55")
    assert result.state is ResultState.INVALID_DATA


def test_undelivered_tail_of_in_progress_session_is_waiting():
    result = evaluate(SyntheticSession(), at="11:30", through="11:00")
    assert result.state is ResultState.WAITING_FOR_BREAKOUT


def test_completed_session_missing_tail_cannot_declare_no_breakout():
    result = evaluate(SyntheticSession(), at="15:30", through="14:00")
    assert result.state is ResultState.INVALID_DATA and time(15, 25) in result.missing_slots


def test_completed_session_missing_tail_after_entry_still_reports_entry():
    result = evaluate(long_breakout(), at="15:30", through="12:00")
    assert result.state is ResultState.ENTRY_IDENTIFIED


def test_evaluation_is_deterministic():
    assert evaluate(long_breakout()) == evaluate(long_breakout())
