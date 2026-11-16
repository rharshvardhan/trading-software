"""The revised 09:45 SHORT flow; all complete sessions and prices here are SYNTHETIC."""

from decimal import Decimal

import pytest

from helpers import InMemoryProvider, evaluate, in_window, make_service
from trading_scanner.market import THREE_CANDLE_0945
from trading_scanner.models import ResultState, RuleDecisionCode, ScanRequest
from trading_scanner.synthetic import three_candle_session

D = Decimal
W = THREE_CANDLE_0945


def run(session, at="15:30", through=None, stop=True):
    return evaluate(session, at=at, through=through, window=W, stop_loss_enabled=stop)


def delayed(first_close="101.00", confirm_open="101.00"):
    return (three_candle_session("short")
            .set("10:25", "102.00", "103.00", "99.00", first_close)
            .set("11:00", confirm_open, "102.00", "98.50", "99.00")
            .set("11:05", "98.80", "104.00", "98.00", "103.00"))


@pytest.mark.parametrize("first_close", ["101.00", "99.50"])
@pytest.mark.parametrize("confirm_open", ["101.00", "99.00"])
def test_wick_or_close_then_later_confirmation_accepts_either_open(first_close, confirm_open):
    result = run(delayed(first_close, confirm_open))
    assert result.trigger.candle.start.strftime("%H:%M") == "10:25"
    assert result.breakout.candle.start.strftime("%H:%M") == "11:00"
    assert result.confirmation.closed and result.confirmation.satisfies
    assert result.entry.candle.start.strftime("%H:%M") == "11:05"
    assert result.entry.price == D("98.80") and result.stop_loss == D("110.00")


def test_first_close_cannot_also_be_its_own_confirmation():
    result = run(delayed("99.50"), at="10:30", through="10:25")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION
    assert result.trigger is not None and result.breakout is result.entry is result.stop_loss is None


def test_wicks_and_boundary_closes_after_first_break_keep_waiting():
    session = delayed().set("10:30", "101.00", "102.00", "99.00", "101.00").set(
        "10:35", "101.00", "102.00", "99.00", "100.00")
    result = run(session, at="10:40", through="10:35")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION and result.entry is None
    assert run(session).entry.candle.start.strftime("%H:%M") == "11:05"


def test_forming_confirmation_never_enters_from_its_open_or_current_close():
    result = run(delayed(), at="11:03", through="11:00")
    assert result.state is ResultState.WAITING_FOR_CONFIRMATION and result.entry is None
    assert result.confirmation.closed is False and result.confirmation.satisfies is None


def test_next_open_is_pending_only_after_confirmation_finishes():
    result = run(delayed(), at="11:05", through="11:00")
    assert result.state is ResultState.AWAITING_ENTRY and result.entry.price is None
    assert result.entry.expected_start.strftime("%H:%M") == "11:05"
    assert result.stop_loss == D("110.00")


@pytest.mark.parametrize("slot", ["10:00", "10:25", "11:00"])
def test_upper_wick_cancels_before_or_during_confirmation(slot):
    session = delayed().set(slot, "102.00", "111.00", "98.50", "99.00")
    result = run(session)
    assert result.state is ResultState.SETUP_CANCELLED
    assert result.cancellation.candle.start.strftime("%H:%M") == slot
    assert result.cancellation.confirmed_at is None  # no invented intrabar breach timestamp
    assert result.entry is result.stop_loss is None


def test_forming_upper_wick_cancels_without_a_close():
    session = delayed().set("10:25", "102.00", "111.00", "99.00", "101.00")
    result = run(session, at="10:27", through="10:25")
    assert result.state is ResultState.SETUP_CANCELLED and result.entry is None


def test_reference_high_touch_does_not_cancel_and_entry_candle_cannot_erase_entry():
    session = delayed().set("10:25", "102.00", "110.00", "99.00", "101.00").set(
        "11:05", "98.80", "150.00", "98.00", "140.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_IDENTIFIED and result.cancellation is None
    assert result.entry.price == D("98.80")


@pytest.mark.parametrize("missing", ["10:15", "10:30", "11:00", "11:05"])
def test_missing_coverage_cannot_be_skipped(missing):
    result = run(delayed().drop(missing))
    assert result.state is ResultState.INVALID_DATA
    assert result.entry is None or result.entry.price is None


def test_a_later_close_already_below_counts_even_if_its_entire_candle_is_below():
    session = delayed().set("11:00", "99.50", "99.80", "98.50", "99.00")
    assert run(session).state is ResultState.ENTRY_IDENTIFIED


def test_first_break_entirely_below_preserves_existing_gap_question():
    session = delayed().set("10:25", "99.50", "99.80", "98.50", "99.00")
    assert run(session).rule_decision is RuleDecisionCode.GAP_BEYOND_RANGE


@pytest.mark.parametrize("trigger_slot,confirmation_slot", [("15:25", None), ("15:20", "15:25")])
def test_session_end_never_borrows_a_confirmation_or_entry_from_next_day(trigger_slot, confirmation_slot):
    session = three_candle_session("short").set(trigger_slot, "102.00", "103.00", "99.00", "101.00")
    if confirmation_slot:
        session.set(confirmation_slot, "101.00", "102.00", "98.50", "99.00")
    result = run(session)
    assert result.state is ResultState.ENTRY_UNAVAILABLE_SESSION_END
    assert result.entry is None or result.entry.price is None


def test_no_later_confirmation_means_no_trade():
    session = three_candle_session("short").set("10:25", "102.00", "103.00", "99.00", "101.00")
    result = run(session)
    assert result.state is ResultState.NO_BREAKOUT and result.trigger is not None
    assert result.entry is result.stop_loss is None


def test_entry_open_above_cancelling_high_does_not_invent_an_event_priority():
    session = delayed().set("11:05", "111.00", "112.00", "110.50", "111.50")
    result = run(session)
    assert result.state is ResultState.NEEDS_RULE_DECISION
    assert result.rule_decision is RuleDecisionCode.ENTRY_OPEN_CANCELLATION
    assert result.entry is result.stop_loss is None


def test_api_exposes_first_break_confirmation_entry_and_wick_cancellation_separately():
    cancelled = delayed().set("10:25", "102.00", "111.00", "99.00", "101.00")
    provider = InMemoryProvider(sessions={"SYN-CONFIRM": (delayed(), "15:30", None),
                                         "SYN-CANCEL": (cancelled, "15:30", None)})
    service = make_service(lambda _: provider, stop_loss_enabled=True)
    response = service.scan(ScanRequest(trading_date="2026-11-13", stocks=["SYN-CONFIRM", "SYN-CANCEL"], provider="fixture"))
    result, cancel = in_window(response.results, W.key)
    assert result.entry_rule == "break_then_confirm"
    assert result.trigger.candle_start.strftime("%H:%M") == "10:25"
    assert result.breakout.candle_start.strftime("%H:%M") == "11:00"
    assert result.entry.time.strftime("%H:%M") == "11:05"
    assert "confirmation" in result.entry.price_basis and result.risk.stop_loss == D("110.00")
    assert cancel.cancellation.trigger_basis == "high" and cancel.cancellation.close == D("101.00")
    assert cancel.cancellation.confirmed_at is None and cancel.entry is None
    assert response.model_dump(mode="json")["results"][0]["trigger"]["extreme_value"] == "99.00"
