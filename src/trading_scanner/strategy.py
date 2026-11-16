"""The single four candle reversal strategy engine (SPEC.md R01 to R10, D04 to D07, and
the direction rule in specs/REVERSAL_DIRECTION_SPEC.md: a new morning high permits only a
SHORT below the four-candle low; a new morning low permits only a LONG above its high; a
first close beyond the prohibited boundary cancels the setup before entry, section 11).

The later THREE_CANDLE_0945_CONFIRMATION_SPEC.md (SHORT) and its mirror
THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md (LONG) override the 09:45 window only:
first breach of the entry-side boundary (wick or close), a different later completed close
beyond it, then the next open. A pre-entry wick beyond the opposite boundary cancels
(SHORT: high > H; LONG: low < L). The other windows retain the earlier one-close flow.

This module is pure: no network, files, terminal, or clock. The terminal runner and
the FastAPI interface both reach it through ``service.ScanService``.

The building blocks (``reference_range``, ``compare_side``, ``decide_qualification``,
``find_first_breakout``, ``entry_from_next_candle``) are exactly what
``evaluate_session`` uses, so the teaching examples can be checked against the
observed chart values without inventing the candles that were never recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, time
from decimal import Decimal
from typing import Literal

from trading_scanner.formatting import format_price
from trading_scanner.market import (
    FOUR_CANDLE_1030,
    ReferenceWindow,
    describe_slots,
    hhmm,
    next_slot,
    session_close,
)
from trading_scanner.models import (
    BreakoutSide,
    Candle,
    ExtremeStatus,
    QualificationDecision,
    ResultState,
    RuleDecisionCode,
    Signal,
)
from trading_scanner.normalize import NormalizedSession

RULE_QUESTIONS: dict[RuleDecisionCode, str] = {
    RuleDecisionCode.EQUAL_REPEATED_EXTREME: (
        "Does a reference candle that only equals an earlier morning high or low qualify, "
        "or must the reference candles make a strictly new extreme?"
    ),
    RuleDecisionCode.GAP_BEYOND_RANGE: (
        "Does a candle that lies entirely beyond the range (never trading at or through the "
        "boundary) confirm a breakout?"
    ),
    RuleDecisionCode.BOTH_SIDES_QUALIFIED: (
        "When the reference candles make both a new morning high and a new morning low, "
        "which direction should be traded, if either?"
    ),
    RuleDecisionCode.ENTRY_OPEN_CANCELLATION: (
        "The intended entry opens beyond the setup's cancelling level (above the reference high for a "
        "SHORT, below the reference low for a LONG). Should the setup cancel at that open, or should an "
        "entry be recorded?"
    ),
}


def slot_of(candle: Candle) -> time:
    """The candle's start label, e.g. 11:00."""
    return candle.start.time().replace(tzinfo=None)


# ----------------------------------------------------------- reference range (R04)


@dataclass(frozen=True)
class ReferenceRange:
    """The fixed breakout levels of the whole reference group (wicks included)."""

    high: Decimal
    low: Decimal
    high_slots: tuple[time, ...] = ()
    low_slots: tuple[time, ...] = ()


def reference_range(reference: Sequence[Candle]) -> ReferenceRange:
    """Highest high and lowest low of the whole reference group. Color is irrelevant.

    The caller supplies the window's complete group (four candles at 10:30, three at 09:45).
    """
    if not reference:
        raise ValueError("the reference range needs the reference candles")
    high = max(candle.high for candle in reference)
    low = min(candle.low for candle in reference)
    return ReferenceRange(
        high=high,
        low=low,
        high_slots=tuple(slot_of(c) for c in reference if c.high == high),
        low_slots=tuple(slot_of(c) for c in reference if c.low == low),
    )


# ------------------------------------------------------ qualification (R03, D04)


def compare_side(reference_value: Decimal, earlier_value: Decimal, side: Literal["high", "low"]) -> ExtremeStatus:
    """Compare one side of the reference group with the earlier morning extreme."""
    if reference_value == earlier_value:
        return ExtremeStatus.EQUAL_TO_EARLIER
    beyond = reference_value > earlier_value if side == "high" else reference_value < earlier_value
    return ExtremeStatus.NEW_EXTREME if beyond else ExtremeStatus.NOT_EXTREME


def decide_qualification(high: ExtremeStatus, low: ExtremeStatus) -> QualificationDecision:
    """At least one strictly new extreme qualifies; otherwise a tie is an open rule."""
    if ExtremeStatus.NEW_EXTREME in (high, low):
        return QualificationDecision.QUALIFIED
    if ExtremeStatus.EQUAL_TO_EARLIER in (high, low):
        return QualificationDecision.NEEDS_RULE_DECISION
    return QualificationDecision.NOT_QUALIFIED


def permitted_signal(high: ExtremeStatus, low: ExtremeStatus) -> Signal | None:
    """The only entry direction a qualification allows (REVERSAL_DIRECTION_SPEC.md section 3).

    New morning high only -> SHORT; new morning low only -> LONG. Both sides new, or a new
    extreme with a tie on the other side, leave the direction undecided (section 8).
    """
    if high is ExtremeStatus.NEW_EXTREME and low is ExtremeStatus.NOT_EXTREME:
        return Signal.SHORT
    if low is ExtremeStatus.NEW_EXTREME and high is ExtremeStatus.NOT_EXTREME:
        return Signal.LONG
    return None


def entry_side(signal: Signal) -> BreakoutSide:
    """The boundary a setup enters through: SHORT below the range, LONG above it."""
    return BreakoutSide.BELOW if signal is Signal.SHORT else BreakoutSide.ABOVE


def permits(signal: Signal, side: BreakoutSide) -> bool:
    """A SHORT setup needs a close below the range; a LONG setup needs a close above it."""
    return side is entry_side(signal)


@dataclass(frozen=True)
class SideAssessment:
    status: ExtremeStatus
    reference_value: Decimal
    reference_slots: tuple[time, ...]
    earlier_value: Decimal
    earlier_slots: tuple[time, ...]


@dataclass(frozen=True)
class Qualification:
    decision: QualificationDecision
    high: SideAssessment
    low: SideAssessment
    session_high: Decimal
    session_high_slots: tuple[time, ...]
    session_low: Decimal
    session_low_slots: tuple[time, ...]
    reference: ReferenceRange

    @property
    def qualifying_sides(self) -> list[Literal["high", "low"]]:
        sides: list[Literal["high", "low"]] = []
        if self.high.status is ExtremeStatus.NEW_EXTREME:
            sides.append("high")
        if self.low.status is ExtremeStatus.NEW_EXTREME:
            sides.append("low")
        return sides

    @property
    def permitted_signal(self) -> Signal | None:
        if self.decision is not QualificationDecision.QUALIFIED:
            return None
        return permitted_signal(self.high.status, self.low.status)


def assess_qualification(earlier: Sequence[Candle], reference: Sequence[Candle]) -> Qualification:
    """Session-extreme qualification using only 09:15 through the last reference candle.

    Later candles are never consulted, so a later new extreme cannot retroactively
    change the qualification (EXAMPLES.md A18).
    """
    if not earlier:
        raise ValueError("qualification needs the earlier morning candles")
    rng = reference_range(reference)
    earlier_high = max(c.high for c in earlier)
    earlier_low = min(c.low for c in earlier)
    window = [*earlier, *reference]
    session_high = max(c.high for c in window)
    session_low = min(c.low for c in window)
    high = SideAssessment(
        status=compare_side(rng.high, earlier_high, "high"),
        reference_value=rng.high,
        reference_slots=rng.high_slots,
        earlier_value=earlier_high,
        earlier_slots=tuple(slot_of(c) for c in earlier if c.high == earlier_high),
    )
    low = SideAssessment(
        status=compare_side(rng.low, earlier_low, "low"),
        reference_value=rng.low,
        reference_slots=rng.low_slots,
        earlier_value=earlier_low,
        earlier_slots=tuple(slot_of(c) for c in earlier if c.low == earlier_low),
    )
    return Qualification(
        decision=decide_qualification(high.status, low.status),
        high=high,
        low=low,
        session_high=session_high,
        session_high_slots=tuple(slot_of(c) for c in window if c.high == session_high),
        session_low=session_low,
        session_low_slots=tuple(slot_of(c) for c in window if c.low == session_low),
        reference=rng,
    )


# ------------------------------------------------- breakout and entry (R05 to R08)


def close_side(close: Decimal, rng: ReferenceRange) -> BreakoutSide | None:
    """Which side a closing price is strictly outside of, if any. A close on a boundary is inside."""
    if close > rng.high:
        return BreakoutSide.ABOVE
    if close < rng.low:
        return BreakoutSide.BELOW
    return None


def classify_close(candle: Candle, rng: ReferenceRange) -> BreakoutSide | None:
    """Strictly outside closes only. Wicks and closes exactly on a boundary do not count."""
    return close_side(candle.close, rng)


def is_entirely_beyond(candle: Candle, rng: ReferenceRange, side: BreakoutSide) -> bool:
    """True when the candle never traded at or through the boundary it closed beyond (D05)."""
    return candle.low > rng.high if side is BreakoutSide.ABOVE else candle.high < rng.low


def _opposite(side: BreakoutSide) -> BreakoutSide:
    return BreakoutSide.BELOW if side is BreakoutSide.ABOVE else BreakoutSide.ABOVE


def _level(rng: ReferenceRange, side: BreakoutSide) -> Decimal:
    return rng.high if side is BreakoutSide.ABOVE else rng.low


def _beyond(price: Decimal, rng: ReferenceRange, side: BreakoutSide) -> bool:
    """Strictly beyond one boundary at source precision; equality is not a crossing."""
    return price > rng.high if side is BreakoutSide.ABOVE else price < rng.low


def _extreme(candle: Candle, side: BreakoutSide) -> Decimal:
    """The candle's price toward one side: its high for above, its low for below (wick included)."""
    return candle.high if side is BreakoutSide.ABOVE else candle.low


_SIDE_WORDS = {BreakoutSide.ABOVE: ("above", "high"), BreakoutSide.BELOW: ("below", "low")}


@dataclass(frozen=True)
class Breakout:
    candle: Candle
    side: BreakoutSide
    boundary_value: Decimal
    entirely_beyond: bool
    permitted: bool | None = None  # set by evaluate_session against the setup's direction

    @property
    def signal(self) -> Signal:
        return Signal.LONG if self.side is BreakoutSide.ABOVE else Signal.SHORT

    @property
    def confirmed_at(self) -> datetime:
        return self.candle.end


def find_first_breakout(rng: ReferenceRange, closed_candles: Sequence[Candle]) -> Breakout | None:
    """The first closed candle, in order, whose close is strictly outside the range.

    ``closed_candles`` must be the contiguous closed candles following the reference
    group. No time deadline applies (R05).
    """
    for candle in closed_candles:
        side = classify_close(candle, rng)
        if side is not None:
            boundary = rng.high if side is BreakoutSide.ABOVE else rng.low
            return Breakout(candle, side, boundary, is_entirely_beyond(candle, rng, side))
    return None


@dataclass(frozen=True)
class EntryReference:
    signal: Signal
    expected_start: datetime | None
    candle: Candle | None = None

    @property
    def price(self) -> Decimal | None:
        return self.candle.open if self.candle is not None else None


def entry_from_next_candle(breakout: Breakout, next_candle: Candle | None) -> EntryReference:
    """Entry is the open of the candle immediately after the breakout candle (R07)."""
    expected = breakout.candle.end
    if next_candle is not None and next_candle.start != expected:
        raise ValueError(
            f"entry must use the candle starting at {hhmm(expected)}, not {hhmm(next_candle.start)}"
        )
    return EntryReference(signal=breakout.signal, expected_start=expected, candle=next_candle)


@dataclass(frozen=True)
class RangeBreach:
    """An observed high/low breach. Five-minute OHLC does not reveal its exact time."""

    candle: Candle
    side: BreakoutSide
    boundary_value: Decimal
    observed_at: datetime

    @property
    def extreme_value(self) -> Decimal:
        return _extreme(self.candle, self.side)

    @property
    def confirmed_at(self) -> None:
        return None


@dataclass(frozen=True)
class Confirmation:
    earliest_start: datetime
    candle: Candle | None = None
    closed: bool = False
    satisfies: bool | None = None


# ------------------------------------------------------------ initial stop loss


def initial_stop_loss(window: ReferenceWindow, q: Qualification) -> tuple[Decimal, str] | None:
    """The taught initial stop-loss level for a window's setup, or None where none is taught.

    THREE_CANDLE_0945_STOP_LOSS_SPEC.md (09:45 window only): SHORT uses the highest high and LONG
    the lowest low of the reference candles, full wick or body extreme, exact source value, no
    buffer, never recalculated from later candles. It is a level only: no stop-hit, exit, or loss
    is computed, and it is attached only to a confirmed entry (identified or pending).
    """
    if window.initial_stop_rule != "reference_extreme":
        return None
    signal = q.permitted_signal
    if signal is Signal.SHORT:
        slots = _slots_text(q.reference.high_slots)
        return q.reference.high, f"reference high of the {window.reference_text} candles ({slots}), wicks included"
    if signal is Signal.LONG:
        slots = _slots_text(q.reference.low_slots)
        return q.reference.low, f"reference low of the {window.reference_text} candles ({slots}), wicks included"
    return None


def _stop_text(stop: tuple[Decimal, str] | None) -> str:
    if stop is None:
        return ""
    return f" Initial stop loss {format_price(stop[0])}: the {stop[1]}; stop-hit and exit rules are not yet defined."


# ------------------------------------------------------------ session evaluation


@dataclass(frozen=True)
class Evaluation:
    state: ResultState
    reason: str
    notes: tuple[str, ...] = ()
    qualification: Qualification | None = None
    reference_candles: tuple[Candle, ...] = ()
    breakout: Breakout | None = None
    entry: EntryReference | None = None
    cancellation: Breakout | RangeBreach | None = None
    trigger: RangeBreach | None = None
    confirmation: Confirmation | None = None
    stop_loss: Decimal | None = None  # initial stop-loss level, only where the user has taught one
    stop_loss_basis: str | None = None
    rule_decision: RuleDecisionCode | None = None
    session_complete: bool = False
    last_closed_slot: time | None = None
    missing_slots: tuple[time, ...] = ()

    @property
    def setup_qualified(self) -> bool | None:
        if self.qualification is None:
            return None
        return {
            QualificationDecision.QUALIFIED: True,
            QualificationDecision.NOT_QUALIFIED: False,
        }.get(self.qualification.decision)


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:]


def _range_text(rng: ReferenceRange) -> str:
    return f"{format_price(rng.low)} to {format_price(rng.high)}"


def _slots_text(slots: Sequence[time]) -> str:
    return ", ".join(hhmm(s) for s in slots)


def _qualified_text(q: Qualification) -> str:
    parts = []
    if q.high.status is ExtremeStatus.NEW_EXTREME:
        parts.append(
            f"new session high {format_price(q.high.reference_value)} in the "
            f"{_slots_text(q.high.reference_slots)} reference candle"
        )
    if q.low.status is ExtremeStatus.NEW_EXTREME:
        parts.append(
            f"new session low {format_price(q.low.reference_value)} in the "
            f"{_slots_text(q.low.reference_slots)} reference candle"
        )
    text = "Qualified: " + " and ".join(parts) + f"; reference range {_range_text(q.reference)}."
    signal = q.permitted_signal
    if signal is Signal.SHORT:
        text += f" SHORT setup: entry needs a close below {format_price(q.reference.low)}."
    elif signal is Signal.LONG:
        text += f" LONG setup: entry needs a close above {format_price(q.reference.high)}."
    return text


def _not_qualified_text(q: Qualification, window: ReferenceWindow) -> str:
    return (
        f"Not qualified: neither {window.qualification_text} session extreme is in the "
        f"{window.reference_text} reference candles. "
        f"Earlier high {format_price(q.high.earlier_value)} ({_slots_text(q.high.earlier_slots)}) is above the "
        f"reference high {format_price(q.high.reference_value)}, and earlier low "
        f"{format_price(q.low.earlier_value)} ({_slots_text(q.low.earlier_slots)}) is below the reference low "
        f"{format_price(q.low.reference_value)}. No strategy entry applies."
    )


def _tie_text(q: Qualification) -> str:
    tied = []
    for name, side in (("high", q.high), ("low", q.low)):
        if side.status is ExtremeStatus.EQUAL_TO_EARLIER:
            tied.append(
                f"the reference {name} {format_price(side.reference_value)} "
                f"({_slots_text(side.reference_slots)}) equals the earlier morning {name} "
                f"({_slots_text(side.earlier_slots)})"
            )
    return (
        "Needs a rule decision: " + " and ".join(tied) + ", and no strictly new extreme was made. "
        "Whether matching an earlier extreme qualifies is an open rule (SPEC.md section 10); "
        "no tie policy is assumed and no entry is reported."
    )


def _breakout_text(b: Breakout) -> str:
    where = "above the reference high" if b.side is BreakoutSide.ABOVE else "below the reference low"
    return (
        f"The {hhmm(b.candle.start)} candle closed at {format_price(b.candle.close)}, {where} "
        f"{format_price(b.boundary_value)}, confirming a {b.signal.value} breakout at {hhmm(b.confirmed_at)}."
    )


def evaluate_session(
    session: NormalizedSession, window: ReferenceWindow = FOUR_CANDLE_1030, stop_loss_enabled: bool = False
) -> Evaluation:
    """Evaluate one normalized session for one reference window: data validity, qualification,
    direction, breakout or cancellation, and entry. The taught initial stop-loss level is attached
    only when ``stop_loss_enabled`` is true (the STOP_LOSS_ENABLED switch in .env)."""
    trading_date = session.trading_date
    as_of = session.as_of
    candles = session.candles
    complete = as_of >= session_close(trading_date)

    def closed(candle: Candle) -> bool:
        return as_of >= candle.end

    present = sorted(candles)
    last_returned = present[-1] if present else None
    closed_slots = [slot for slot in present if closed(candles[slot])]
    last_closed = closed_slots[-1] if closed_slots else None
    as_of_text = (
        f"data as of {as_of.strftime('%H:%M')}"
        + (f", last closed candle {hhmm(last_closed)}" if last_closed else ", no closed candle yet")
    )
    common = {"session_complete": complete, "last_closed_slot": last_closed}

    def is_gap(slot: time) -> bool:
        return complete or (last_returned is not None and slot < last_returned)

    # 1. Coverage of the whole qualification window comes before any qualification decision.
    missing = [slot for slot in window.qualification_slots if slot not in candles]
    gaps = [slot for slot in missing if is_gap(slot)]
    if gaps:
        consequences = []
        if any(slot in window.earlier_slots for slot in gaps):
            consequences.append("an earlier morning extreme cannot be ruled out")
        if any(slot in window.reference_slots for slot in gaps):
            consequences.append(f"the range cannot be formed from fewer than {window.count_word} reference candles")
        return Evaluation(
            state=ResultState.INVALID_DATA,
            reason=(
                f"Missing required candle(s): {describe_slots(gaps)}. "
                + _sentence("; ".join(consequences))
                + ". No candles were filled in."
            ),
            missing_slots=tuple(gaps),
            **common,
        )
    if missing or any(not closed(candles[slot]) for slot in window.qualification_slots):
        return Evaluation(
            state=ResultState.WAITING_FOR_REFERENCE,
            reason=(
                f"The {window.reference_text} reference candles have not all closed yet ({as_of_text}). "
                f"The range becomes final when the {hhmm(window.reference_slots[-1])} candle closes at "
                f"{hhmm(window.range_final_at)}."
            ),
            **common,
        )

    earlier = [candles[slot] for slot in window.earlier_slots]
    reference = [candles[slot] for slot in window.reference_slots]
    q = assess_qualification(earlier, reference)
    rng = q.reference
    base = {"qualification": q, "reference_candles": tuple(reference), **common}

    if q.decision is QualificationDecision.NOT_QUALIFIED:
        return Evaluation(state=ResultState.NOT_QUALIFIED, reason=_not_qualified_text(q, window), **base)
    if q.decision is QualificationDecision.NEEDS_RULE_DECISION:
        return Evaluation(
            state=ResultState.NEEDS_RULE_DECISION,
            reason=_tie_text(q),
            rule_decision=RuleDecisionCode.EQUAL_REPEATED_EXTREME,
            **base,
        )

    qualified = _qualified_text(q)
    notes: list[str] = []
    signal = q.permitted_signal
    if signal is None:
        # The direction rule cannot fix a direction here (REVERSAL_DIRECTION_SPEC.md section 8).
        if q.high.status is ExtremeStatus.NEW_EXTREME and q.low.status is ExtremeStatus.NEW_EXTREME:
            reason = (
                f"{qualified} Needs a rule decision: the {window.count_word} reference candles made both a new "
                "morning high and a new "
                "morning low, and which direction to trade is an open rule (REVERSAL_DIRECTION_SPEC.md "
                "section 8). No entry is reported."
            )
            code = RuleDecisionCode.BOTH_SIDES_QUALIFIED
        else:
            new_side, tied_side = (q.high, q.low) if q.high.status is ExtremeStatus.NEW_EXTREME else (q.low, q.high)
            new_name, tied_name = ("high", "low") if new_side is q.high else ("low", "high")
            reason = (
                f"{qualified} Needs a rule decision: the reference {tied_name} "
                f"{format_price(tied_side.reference_value)} only equals the earlier morning {tied_name} "
                f"({_slots_text(tied_side.earlier_slots)}). Whether that tie also qualifies the {tied_name} side "
                f"is the open tie policy, so the permitted direction cannot be fixed from the new {new_name} "
                "alone. No entry is reported."
            )
            code = RuleDecisionCode.EQUAL_REPEATED_EXTREME
        return Evaluation(state=ResultState.NEEDS_RULE_DECISION, reason=reason, rule_decision=code, **base)

    if window.entry_rule == "break_then_confirm":
        return _evaluate_break_then_confirm(session, window, q, base, stop_loss_enabled)

    # 2. Contiguous closed candles after the reference group, in order.
    run: list[Candle] = []
    stop_kind: Literal["missing", "forming", "end"] = "end"
    stop_slot: time | None = None
    for slot in window.post_slots:
        candle = candles.get(slot)
        if candle is None:
            stop_kind, stop_slot = "missing", slot
            break
        if not closed(candle):
            stop_kind, stop_slot = "forming", slot
            break
        run.append(candle)

    breakout = find_first_breakout(rng, run)

    if breakout is None:
        if stop_kind == "missing" and stop_slot is not None and is_gap(stop_slot):
            post_gaps = [s for s in window.post_slots if s not in candles and is_gap(s)]
            return Evaluation(
                state=ResultState.INVALID_DATA,
                reason=(
                    f"{qualified} Missing candle(s) after the reference group: {describe_slots(post_gaps)}. "
                    "The first breakout cannot be established across a gap, so no breakout or entry is reported."
                ),
                notes=tuple(notes),
                missing_slots=tuple(post_gaps),
                **base,
            )
        if stop_kind == "forming" and stop_slot is not None:
            notes.append(
                f"The {hhmm(stop_slot)} candle is still forming; a forming candle cannot confirm a breakout."
            )
        if stop_kind in ("missing", "forming"):
            return Evaluation(
                state=ResultState.WAITING_FOR_BREAKOUT,
                reason=(
                    f"{qualified} No candle has closed outside the range yet ({as_of_text}). "
                    "There is no breakout deadline."
                ),
                notes=tuple(notes),
                **base,
            )
        return Evaluation(
            state=ResultState.NO_BREAKOUT,
            reason=(
                f"{qualified} No candle from {hhmm(window.range_final_at)} to 15:25 closed strictly outside the range; "
                "wick-only crossings and closes on a boundary do not count. No entry."
            ),
            notes=tuple(notes),
            **base,
        )

    breakout = replace(breakout, permitted=permits(signal, breakout.side))
    breakout_text = _breakout_text(breakout)
    if not breakout.permitted:
        # REVERSAL_DIRECTION_SPEC.md section 11: the setup fails before entry and cannot be revived.
        if breakout.side is BreakoutSide.ABOVE:
            where, permitted_boundary = "above the reference high", f"a close below {format_price(rng.low)}"
        else:
            where, permitted_boundary = "below the reference low", f"a close above {format_price(rng.high)}"
        return Evaluation(
            state=ResultState.SETUP_CANCELLED,
            reason=(
                f"{qualified} Setup cancelled: the {hhmm(breakout.candle.start)} candle closed at "
                f"{format_price(breakout.candle.close)}, {where} {format_price(breakout.boundary_value)}, the wrong "
                f"direction for this {signal.value.upper()} setup (confirmed at {hhmm(breakout.confirmed_at)}). "
                f"No entry; {permitted_boundary} later does not revive the setup."
            ),
            notes=tuple(notes),
            cancellation=breakout,
            **base,
        )
    if breakout.entirely_beyond:
        boundary_name = "reference high" if breakout.side is BreakoutSide.ABOVE else "reference low"
        extreme = breakout.candle.low if breakout.side is BreakoutSide.ABOVE else breakout.candle.high
        extreme_name = "low" if breakout.side is BreakoutSide.ABOVE else "high"
        return Evaluation(
            state=ResultState.NEEDS_RULE_DECISION,
            reason=(
                f"{qualified} Needs a rule decision: the first close outside the range ({hhmm(breakout.candle.start)} "
                f"candle, close {format_price(breakout.candle.close)}) lies entirely beyond the {boundary_name} "
                f"{format_price(breakout.boundary_value)}; its {extreme_name} {format_price(extreme)} never traded at "
                "or through the level. Gap treatment is an open rule (SPEC.md section 10), so no entry is reported "
                "and no later breakout is searched for."
            ),
            notes=tuple(notes),
            breakout=breakout,
            rule_decision=RuleDecisionCode.GAP_BEYOND_RANGE,
            **base,
        )

    return _evaluate_entry(session, window, q, breakout, base, notes, stop_loss_enabled, qualified)


def _evaluate_entry(
    session: NormalizedSession,
    window: ReferenceWindow,
    q: Qualification,
    breakout: Breakout,
    base: dict,
    notes: list[str],
    stop_loss_enabled: bool,
    qualified: str,
) -> Evaluation:
    """Shared next-open handling after the applicable entry confirmation is complete."""
    candles = session.candles
    as_of = session.as_of
    complete = as_of >= session_close(session.trading_date)
    last_returned = max(candles, default=None)
    as_of_text = f"data as of {as_of.strftime('%H:%M')}"
    breakout_text = _breakout_text(breakout)

    def is_gap(slot: time) -> bool:
        return complete or (last_returned is not None and slot < last_returned)

    breakout_slot = slot_of(breakout.candle)
    entry_slot = next_slot(breakout_slot)
    if entry_slot is None:
        return Evaluation(
            state=ResultState.ENTRY_UNAVAILABLE_SESSION_END,
            reason=(
                f"{qualified} {breakout_text} That is the last candle of the session, so no same-session candle "
                "follows; entry is unavailable and the next trading day's open is not substituted."
            ),
            notes=tuple(notes),
            breakout=breakout,
            entry=EntryReference(signal=breakout.signal, expected_start=None),
            **base,
        )

    entry_candle = candles.get(entry_slot)
    if entry_candle is None:
        if is_gap(entry_slot):
            return Evaluation(
                state=ResultState.INVALID_DATA,
                reason=(
                    f"{qualified} {breakout_text} The immediately following {hhmm(entry_slot)} candle is missing, "
                    "and a later candle is never substituted for the entry."
                ),
                notes=tuple(notes),
                breakout=breakout,
                entry=entry_from_next_candle(breakout, None),
                missing_slots=(entry_slot,),
                **base,
            )
        stop = initial_stop_loss(window, q) if stop_loss_enabled else None
        return Evaluation(
            state=ResultState.AWAITING_ENTRY,
            reason=(
                f"{qualified} {breakout_text} Entry is the open of the {hhmm(entry_slot)} candle, "
                f"which is not available yet ({as_of_text}).{_stop_text(stop)}"
            ),
            notes=tuple(notes),
            breakout=breakout,
            entry=entry_from_next_candle(breakout, None),
            stop_loss=stop[0] if stop else None,
            stop_loss_basis=stop[1] if stop else None,
            **base,
        )

    if window.entry_rule == "break_then_confirm" and q.permitted_signal is not None:
        cancel_side = _opposite(entry_side(q.permitted_signal))
        if _beyond(entry_candle.open, q.reference, cancel_side):
            where, name = _SIDE_WORDS[cancel_side]
            return Evaluation(
                state=ResultState.NEEDS_RULE_DECISION,
                reason=(
                    f"{qualified} {breakout_text} The intended {hhmm(entry_slot)} entry opens at "
                    f"{format_price(entry_candle.open)}, {where} the cancelling {name} "
                    f"{format_price(_level(q.reference, cancel_side))}. "
                    "Entry-open versus cancellation priority has not been taught; no entry is reported."
                ),
                breakout=breakout,
                rule_decision=RuleDecisionCode.ENTRY_OPEN_CANCELLATION,
                **base,
            )

    entry = entry_from_next_candle(breakout, entry_candle)
    stop = initial_stop_loss(window, q) if stop_loss_enabled else None
    return Evaluation(
        state=ResultState.ENTRY_IDENTIFIED,
        reason=(
            f"{qualified} {breakout_text} {breakout.signal.value.capitalize()} entry reference: open of the "
            f"{hhmm(entry_candle.start)} candle, {format_price(entry_candle.open)}.{_stop_text(stop)}"
        ),
        notes=tuple(notes),
        breakout=breakout,
        entry=entry,
        stop_loss=stop[0] if stop else None,
        stop_loss_basis=stop[1] if stop else None,
        **base,
    )


def _evaluate_break_then_confirm(
    session: NormalizedSession,
    window: ReferenceWindow,
    q: Qualification,
    base: dict,
    stop_loss_enabled: bool,
) -> Evaluation:
    """First entry-side breach -> different later close beyond it -> following open (09:45 window).

    SHORT (THREE_CANDLE_0945_CONFIRMATION_SPEC.md): first low < L, later close < L; high > H cancels.
    LONG (THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md): first high > H, later close > H; low < L cancels.
    The cancelling breach is checked first on every candle, a wick is sufficient, and it is final.
    """
    rng = q.reference
    signal = q.permitted_signal
    assert signal is not None
    side = entry_side(signal)
    cancel_side = _opposite(side)
    where, name = _SIDE_WORDS[side]  # SHORT: "below", "low"; LONG: "above", "high"
    cancel_name = _SIDE_WORDS[cancel_side][1]
    boundary = _level(rng, side)
    candles = session.candles
    as_of = session.as_of
    complete = as_of >= session_close(session.trading_date)
    last_returned = max(candles, default=None)
    qualified = (
        f"{_qualified_text(q)} First wait for a {name} breach, then a later candle must finish "
        f"with a close {where} that same {name}; entry is the candle immediately after that confirmation."
    )
    trigger: RangeBreach | None = None
    confirmation: Confirmation | None = None

    def evidence() -> dict:
        return {**base, "trigger": trigger, "confirmation": confirmation}

    def waiting() -> Evaluation:
        if trigger is not None:
            return Evaluation(
                state=ResultState.WAITING_FOR_CONFIRMATION,
                reason=(
                    f"{qualified} The {hhmm(trigger.candle.start)} candle reached {name} "
                    f"{format_price(trigger.extreme_value)}, {where} {format_price(boundary)}. "
                    f"Wait for a later candle to finish with a close {where} that {name}; its open may be above or "
                    "below. No entry or trade stop is available before confirmation."
                ),
                **evidence(),
            )
        return Evaluation(
            state=ResultState.WAITING_FOR_BREAKOUT,
            reason=f"{qualified} No post-reference candle has breached the {name} yet (as of {hhmm(as_of)}).",
            **evidence(),
        )

    for slot in window.post_slots:
        candle = candles.get(slot)
        if candle is None:
            if complete or (last_returned is not None and slot < last_returned):
                return Evaluation(
                    state=ResultState.INVALID_DATA,
                    reason=(f"{qualified} Required {hhmm(slot)} candle is missing. "
                            "The first break and subsequent confirmation cannot be established across a gap; "
                            "no later candle is substituted."),
                    missing_slots=(slot,),
                    **evidence(),
                )
            return waiting()

        closed = as_of >= candle.end
        # Check pre-entry cancellation even for a reliable forming candle, and before its breach/close.
        if _beyond(_extreme(candle, cancel_side), rng, cancel_side):
            cancellation = RangeBreach(candle, cancel_side, _level(rng, cancel_side), as_of)
            return Evaluation(
                state=ResultState.SETUP_CANCELLED,
                reason=(
                    f"{qualified} Setup cancelled: the {hhmm(candle.start)} candle {cancel_name} "
                    f"{format_price(cancellation.extreme_value)} breached the reference {cancel_name} "
                    f"{format_price(cancellation.boundary_value)} before entry. A wick is sufficient; no outside "
                    "close is required. No entry, stop loss, target or exit; a later reversal does not revive "
                    "this setup."
                ),
                cancellation=cancellation,
                **evidence(),
            )

        if trigger is None:
            if not _beyond(_extreme(candle, side), rng, side):
                if not closed:
                    return waiting()
                continue
            trigger = RangeBreach(candle, side, boundary, as_of)
            if closed and is_entirely_beyond(candle, rng, side):
                return Evaluation(
                    state=ResultState.NEEDS_RULE_DECISION,
                    reason=(f"{qualified} The first break candle {hhmm(candle.start)} lies entirely {where} "
                            f"{format_price(boundary)}; its {cancel_name} never traded at or through the boundary. "
                            "The existing gap rule is unresolved, so no entry is reported."),
                    rule_decision=RuleDecisionCode.GAP_BEYOND_RANGE,
                    **evidence(),
                )
            confirmation = Confirmation(earliest_start=candle.end)
            if next_slot(slot) is None:
                return Evaluation(
                    state=ResultState.ENTRY_UNAVAILABLE_SESSION_END,
                    reason=(f"{qualified} The first break is on the final session candle; "
                            "no same-session confirmation and entry candles follow. No next-day substitution."),
                    **evidence(),
                )
            if not closed:
                return waiting()
            continue

        # A later candle may confirm after consolidation; its open is not a price filter.
        confirmation = Confirmation(trigger.candle.end, candle, closed,
                                    _beyond(candle.close, rng, side) if closed else None)
        if not closed:
            return waiting()
        if not confirmation.satisfies:
            continue
        breakout = Breakout(candle, side, boundary, is_entirely_beyond(candle, rng, side), permitted=True)
        confirmed_text = (
            f"{qualified} First break: {hhmm(trigger.candle.start)}, {name} {format_price(trigger.extreme_value)}. "
            f"The later {hhmm(candle.start)} candle supplied the required confirmation close."
        )
        return _evaluate_entry(session, window, q, breakout, evidence(), [], stop_loss_enabled, confirmed_text)

    return Evaluation(
        state=ResultState.NO_BREAKOUT,
        reason=(
            f"{qualified} No candle from {hhmm(window.range_final_at)} to 15:25 breached the reference {name}; "
            "no entry."
            if trigger is None else
            f"{qualified} The {hhmm(trigger.candle.start)} candle first breached the {name}, but no later candle "
            f"closed {where} it before session end. No confirmed entry."
        ),
        **evidence(),
    )
