"""The revised 09:45 LONG flow, THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md acceptance cases LC01-LC15.

All prices are SYNTHETIC and follow the spec's section 8: earlier morning high 115.00 and low 95.00,
reference group H = 100.00 (09:45 high) and L = 90.00 (09:50 lower wick), so only the low side makes
a new extreme (LONG setup). Every post-reference candle stays inside the range unless a test changes it.
"""

from decimal import Decimal

import pytest

from helpers import InMemoryProvider, evaluate, in_window, make_service
from trading_scanner.cli import render_report
from trading_scanner.market import FOUR_CANDLE_1030, THREE_CANDLE_0945, TWO_CANDLE_1050, hhmm
from trading_scanner.models import BreakoutSide, ResultState, RuleDecisionCode, ScanRequest, Signal
from trading_scanner.synthetic import three_candle_session, two_candle_session

D = Decimal
W = THREE_CANDLE_0945
INSIDE = ("95.00", "96.00", "94.00", "95.00")


def run(session, at="15:30", through=None, stop=True):
    return evaluate(session, at=at, through=through, window=W, stop_loss_enabled=stop)


def spec_session():
    """Section 8: earlier high 115.00 (09:30) and low 95.00 (09:20); reference H 100.00, L 90.00."""
    session = (
        three_candle_session("long")
        .set("09:20", "97.00", "98.00", "95.00", "96.50")
        .set("09:45", "96.00", "100.00", "94.00", "95.00")
        .set("09:50", "95.00", "97.00", "90.00", "92.00")
        .set("09:55", "92.00", "98.00", "91.00", "96.00")
    )
    for slot in W.post_slots:
        session.set(hhmm(slot), *INSIDE)
    return session


def delayed(first_close="99.00", confirm_open="99.00"):
    """Section 8 'wick then later close': 10:25 high 101.00, 10:55 close 101.00, 11:00 open 101.20."""
    return (spec_session()
            .set("10:25", "99.00", "101.00", "98.00", first_close)
            .set("10:55", confirm_open, "101.50", "98.50", "101.00")
            .set("11:00", "101.20", "102.00", "100.50", "101.50"))


def slot(candle) -> str:
    return candle.start.strftime("%H:%M")


# ------------------------------------------------------------ qualification and range


def test_lc01_low_qualification_uses_the_whole_three_candle_range():
    result = run(delayed())
    q = result.qualification
    assert q.permitted_signal is Signal.LONG
    assert (q.reference.low, q.reference.high) == (D("90.00"), D("100.00"))
    assert q.reference.low_slots == (W.reference_slots[1],) and q.reference.high_slots == (W.reference_slots[0],)
    assert (q.high.earlier_value, q.low.earlier_value) == (D("115.00"), D("95.00"))


# ------------------------------------------------- first break, confirmation, entry


@pytest.mark.parametrize("first_close", ["99.00", "101.00"])  # LC02 upper wick; LC03 outside close
@pytest.mark.parametrize("confirm_open", ["99.00", "100.50"])  # LC05 open below or above H
def test_lc02_lc03_lc05_first_break_then_later_close_above_enters_at_the_next_open(first_close, confirm_open):
    result = run(delayed(first_close, confirm_open))
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.cancellation is None
    assert slot(result.trigger.candle) == "10:25" and result.trigger.side is BreakoutSide.ABOVE
    assert result.trigger.extreme_value == D("101.00") and result.trigger.boundary_value == D("100.00")
    assert slot(result.breakout.candle) == "10:55" and result.breakout.side is BreakoutSide.ABOVE
    assert result.breakout.confirmed_at.strftime("%H:%M") == "11:00"
    assert result.confirmation.closed and result.confirmation.satisfies
    assert result.entry.signal is Signal.LONG and slot(result.entry.candle) == "11:00"
    assert result.entry.price == D("101.20")
    assert result.stop_loss == D("90.00") and "reference low" in result.stop_loss_basis  # LC08


def test_lc03_first_outside_close_cannot_also_be_its_own_confirmation():
    result = run(delayed("101.00"), at="10:30", through="10:25")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION
    assert result.trigger is not None and result.breakout is result.entry is result.stop_loss is None


def test_old_one_close_entry_no_longer_applies_to_the_0945_long():
    # Previously a single close above H entered at the next open. Now the next candle must confirm first.
    session = spec_session().set("10:00", "99.00", "101.00", "98.00", "100.80")
    result = run(session)
    assert result.state is ResultState.NO_BREAKOUT and result.entry is None
    assert slot(result.trigger.candle) == "10:00"
    assert "no later candle closed above it" in result.reason


def test_lc04_lc06_wicks_and_boundary_closes_after_the_first_break_keep_waiting():
    session = (delayed()
               .set("10:30", "99.00", "102.00", "98.00", "99.00")    # upper wick only
               .set("10:35", "99.00", "101.00", "98.00", "100.00"))  # close exactly at H
    result = run(session, at="10:40", through="10:35")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION and result.entry is None
    assert result.confirmation.satisfies is False and result.stop_loss is None
    assert "close above that high" in result.reason
    full = run(session)  # the same fixed range: the 10:55 close still confirms
    assert slot(full.breakout.candle) == "10:55" and slot(full.entry.candle) == "11:00"


def test_lc07_forming_high_breach_starts_the_sequence_but_a_forming_close_never_confirms():
    first = run(delayed("101.00"), at="10:27", through="10:25")
    assert first.state is ResultState.WAITING_FOR_CONFIRMATION and slot(first.trigger.candle) == "10:25"
    confirming = run(delayed(), at="10:58", through="10:55")
    assert confirming.state is ResultState.WAITING_FOR_CONFIRMATION and confirming.entry is None
    assert confirming.confirmation.closed is False and confirming.confirmation.satisfies is None


def test_next_open_is_pending_only_after_the_confirmation_finishes():
    result = run(delayed(), at="11:00", through="10:55")
    assert result.state is ResultState.AWAITING_ENTRY and result.entry.price is None
    assert result.entry.expected_start.strftime("%H:%M") == "11:00" and result.entry.signal is Signal.LONG
    assert result.stop_loss == D("90.00")


def test_lc08_stop_switch_off_reports_no_level():
    result = run(delayed(), stop=False)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.entry.price == D("101.20")
    assert result.stop_loss is None and result.stop_loss_basis is None


# ------------------------------------------------------- third point: cancellation


@pytest.mark.parametrize("cancel_slot", ["10:00", "10:25", "10:40", "10:55"])
def test_lc09_lower_wick_cancels_before_entry_even_when_it_closes_above_h(cancel_slot):
    # Low 89.90 < L 90.00 with a close above H: before the break, as the break, while waiting, or as the
    # would-be confirmation. The cancelling breach is checked first, so the close cannot rescue it.
    session = delayed().set(cancel_slot, "99.00", "101.50", "89.90", "101.00")
    result = run(session)
    assert result.state is ResultState.SETUP_CANCELLED
    assert slot(result.cancellation.candle) == cancel_slot
    assert result.cancellation.side is BreakoutSide.BELOW and result.cancellation.boundary_value == D("90.00")
    assert result.cancellation.extreme_value == D("89.90")
    assert result.cancellation.confirmed_at is None  # no invented intrabar breach time
    assert result.breakout is result.entry is result.stop_loss is None
    assert "does not revive" in result.reason


def test_lc09_forming_lower_wick_cancels_without_waiting_for_a_close():
    session = delayed().set("10:25", "99.00", "101.00", "89.90", "99.00")
    result = run(session, at="10:27", through="10:25")
    assert result.state is ResultState.SETUP_CANCELLED and result.entry is None


def test_lc09_cancelled_setup_is_never_revived_by_a_later_upward_confirmation():
    session = spec_session().set("10:05", "95.00", "96.00", "89.50", "95.00")  # cancel, then a full sequence
    session.set("10:25", "99.00", "101.00", "98.00", "99.00").set("10:55", "99.00", "101.50", "98.50", "101.00")
    session.set("11:00", "101.20", "102.00", "100.50", "101.50")
    result = run(session)
    assert result.state is ResultState.SETUP_CANCELLED and slot(result.cancellation.candle) == "10:05"
    assert result.trigger is None and result.entry is None


def test_lc10_low_equal_to_l_does_not_cancel():
    session = delayed().set("10:25", "99.00", "101.00", "90.00", "99.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.cancellation is None


def test_lc11_entry_is_not_erased_and_no_stop_hit_is_inferred_from_a_later_low():
    session = delayed().set("11:00", "101.20", "102.00", "50.00", "60.00").set("11:05", "60.00", "61.00", "40.00", "45.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.cancellation is None
    assert result.entry.price == D("101.20") and result.stop_loss == D("90.00")
    assert "not yet defined" in result.reason  # stop-hit and exit rules remain untaught


def test_entry_open_below_l_keeps_the_priority_question_open():
    session = delayed().set("11:00", "89.50", "90.50", "89.00", "90.00")
    result = run(session)
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.ENTRY_OPEN_CANCELLATION
    assert "below the cancelling low 90.00" in result.reason
    assert result.entry is result.stop_loss is None


# --------------------------------------------------------- data and session edges


@pytest.mark.parametrize("missing", ["10:15", "10:30", "10:55", "11:00"])
def test_lc12_missing_coverage_is_never_skipped(missing):
    result = run(delayed().drop(missing))
    assert result.state is ResultState.INVALID_DATA
    assert result.entry is None or result.entry.price is None
    assert result.stop_loss is None


@pytest.mark.parametrize("trigger_slot,confirmation_slot", [("15:25", None), ("15:20", "15:25")])
def test_lc12_session_end_never_borrows_a_next_day_confirmation_or_entry(trigger_slot, confirmation_slot):
    session = spec_session().set(trigger_slot, "99.00", "101.00", "98.00", "99.00")
    if confirmation_slot:
        session.set(confirmation_slot, "99.00", "101.50", "98.50", "101.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_UNAVAILABLE_SESSION_END
    assert result.entry is None or result.entry.price is None


def test_lc12_no_later_confirmation_means_no_trade():
    session = spec_session().set("10:25", "99.00", "101.00", "98.00", "99.00")
    result = run(session)
    assert result.state is ResultState.NO_BREAKOUT and result.trigger is not None
    assert result.entry is result.stop_loss is None


def test_lc13_first_break_entirely_above_h_preserves_the_gap_question():
    session = delayed().set("10:25", "100.50", "101.00", "100.20", "100.80")
    result = run(session)
    assert result.rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE and result.entry is None


def test_lc14_confirmation_entirely_above_h_is_a_valid_later_close():
    session = delayed().set("10:55", "100.50", "101.50", "100.20", "101.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.breakout.entirely_beyond is True


# ------------------------------------------------------------- shared interfaces


def test_lc15_api_and_terminal_expose_first_break_confirmation_entry_and_wick_cancellation():
    cancelled = delayed().set("10:40", "95.00", "96.00", "89.90", "95.00")
    provider = InMemoryProvider(sessions={"SYN-LCONFIRM": (delayed(), "15:30", None),
                                         "SYN-LCANCEL": (cancelled, "15:30", None)})
    service = make_service(lambda _: provider, stop_loss_enabled=True)
    response = service.scan(ScanRequest(trading_date="2026-11-13", stocks=["SYN-LCONFIRM", "SYN-LCANCEL"], provider="fixture"))
    result, cancel = in_window(response.results, W.key)
    assert result.entry_rule == "break_then_confirm" and result.qualification.permitted_signal is Signal.LONG
    assert result.trigger.side is BreakoutSide.ABOVE and result.trigger.candle_start.strftime("%H:%M") == "10:25"
    assert result.breakout.candle_start.strftime("%H:%M") == "10:55" and result.breakout.signal is Signal.LONG
    assert result.entry.time.strftime("%H:%M") == "11:00" and result.entry.price == D("101.20")
    assert "confirmation" in result.entry.price_basis and result.risk.stop_loss == D("90.00")
    assert cancel.entry_rule == "break_then_confirm"
    assert cancel.cancellation.trigger_basis == "low" and cancel.cancellation.side is BreakoutSide.BELOW
    assert cancel.cancellation.confirmed_at is None and cancel.entry is None and cancel.risk.stop_loss is None
    payload = response.model_dump(mode="json")
    served = in_window(payload["results"], W.key)[0]
    assert served["trigger"]["extreme_value"] == "101.00" and served["trigger"]["side"] == "above"
    text = render_report(response, details=True)
    assert "First break: 10:25 candle high 101.00 above 100.00" in text
    assert "Setup cancelled by the 10:40 candle: low 89.90 breached 90.00 before entry" in text


def test_other_windows_keep_their_single_close_long_flow():
    assert FOUR_CANDLE_1030.entry_rule == TWO_CANDLE_1050.entry_rule == "single_close"
    session = two_candle_session("long").set("11:00", "108.00", "111.50", "107.80", "111.00").set(
        "11:05", "111.20", "111.90", "110.60", "111.40")
    result = evaluate(session, window=TWO_CANDLE_1050)
    assert result.state is ResultState.ENTRY_IDENTIFIED and slot(result.entry.candle) == "11:05"
    assert result.trigger is None
    # A lower wick alone does not cancel the 10:50 LONG; only its taught close rule does.
    wick = two_candle_session("long").set("11:00", "101.00", "101.50", "99.50", "100.50").set(
        "11:30", "108.00", "111.50", "107.80", "111.00")
    assert evaluate(wick, window=TWO_CANDLE_1050).state is ResultState.ENTRY_IDENTIFIED
