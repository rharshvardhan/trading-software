"""The single four candle reversal strategy engine (SPEC.md R01 to R10, D04 to D07).

This module is pure: no network, files, terminal, or clock. The terminal runner and
the FastAPI interface both reach it through ``service.ScanService``.

The building blocks (``reference_range``, ``compare_side``, ``decide_qualification``,
``find_first_breakout``, ``entry_from_next_candle``) are exactly what
``evaluate_session`` uses, so the teaching examples can be checked against the
observed chart values without inventing the candles that were never recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from typing import Literal

from trading_scanner.formatting import format_price
from trading_scanner.market import (
    EARLIER_SLOTS,
    POST_REFERENCE_SLOTS,
    QUALIFICATION_SLOTS,
    REFERENCE_SLOTS,
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
        "or must the four reference candles make a strictly new extreme?"
    ),
    RuleDecisionCode.GAP_BEYOND_RANGE: (
        "Does a candle that lies entirely beyond the range (never trading at or through the "
        "boundary) confirm a breakout?"
    ),
}


def slot_of(candle: Candle) -> time:
    """The candle's start label, e.g. 11:00."""
    return candle.start.time().replace(tzinfo=None)


# ----------------------------------------------------------- reference range (R04)


@dataclass(frozen=True)
class ReferenceRange:
    """The fixed breakout levels of the whole four-candle group (wicks included)."""

    high: Decimal
    low: Decimal
    high_slots: tuple[time, ...] = ()
    low_slots: tuple[time, ...] = ()


def reference_range(reference: Sequence[Candle]) -> ReferenceRange:
    """Highest high and lowest low of the four reference candles. Color is irrelevant."""
    if len(reference) != 4:
        raise ValueError("the reference range needs exactly four candles")
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


def assess_qualification(earlier: Sequence[Candle], reference: Sequence[Candle]) -> Qualification:
    """Session-extreme qualification using only 09:15 through the 10:45 candle.

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


def classify_close(candle: Candle, rng: ReferenceRange) -> BreakoutSide | None:
    """Strictly outside closes only. Wicks and closes exactly on a boundary do not count."""
    if candle.close > rng.high:
        return BreakoutSide.ABOVE
    if candle.close < rng.low:
        return BreakoutSide.BELOW
    return None


def is_entirely_beyond(candle: Candle, rng: ReferenceRange, side: BreakoutSide) -> bool:
    """True when the candle never traded at or through the boundary it closed beyond (D05)."""
    return candle.low > rng.high if side is BreakoutSide.ABOVE else candle.high < rng.low


@dataclass(frozen=True)
class Breakout:
    candle: Candle
    side: BreakoutSide
    boundary_value: Decimal
    entirely_beyond: bool

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
    return "Qualified: " + " and ".join(parts) + f"; reference range {_range_text(q.reference)}."


def _not_qualified_text(q: Qualification) -> str:
    return (
        "Not qualified: neither 09:15-10:45 session extreme is in the 10:30-10:45 reference candles. "
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


def evaluate_session(session: NormalizedSession) -> Evaluation:
    """Evaluate one normalized session: data validity, qualification, breakout, entry."""
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

    # 1. Coverage of 09:15 through 10:45 comes before any qualification decision.
    missing = [slot for slot in QUALIFICATION_SLOTS if slot not in candles]
    gaps = [slot for slot in missing if is_gap(slot)]
    if gaps:
        consequences = []
        if any(slot in EARLIER_SLOTS for slot in gaps):
            consequences.append("an earlier morning extreme cannot be ruled out")
        if any(slot in REFERENCE_SLOTS for slot in gaps):
            consequences.append("the range cannot be formed from fewer than four reference candles")
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
    if missing or any(not closed(candles[slot]) for slot in QUALIFICATION_SLOTS):
        return Evaluation(
            state=ResultState.WAITING_FOR_REFERENCE,
            reason=(
                "The 10:30-10:45 reference candles have not all closed yet "
                f"({as_of_text}). The range becomes final when the 10:45 candle closes at 10:50."
            ),
            **common,
        )

    earlier = [candles[slot] for slot in EARLIER_SLOTS]
    reference = [candles[slot] for slot in REFERENCE_SLOTS]
    q = assess_qualification(earlier, reference)
    rng = q.reference
    base = {"qualification": q, "reference_candles": tuple(reference), **common}

    if q.decision is QualificationDecision.NOT_QUALIFIED:
        return Evaluation(state=ResultState.NOT_QUALIFIED, reason=_not_qualified_text(q), **base)
    if q.decision is QualificationDecision.NEEDS_RULE_DECISION:
        return Evaluation(
            state=ResultState.NEEDS_RULE_DECISION,
            reason=_tie_text(q),
            rule_decision=RuleDecisionCode.EQUAL_REPEATED_EXTREME,
            **base,
        )

    qualified = _qualified_text(q)
    notes: list[str] = []
    if ExtremeStatus.EQUAL_TO_EARLIER in (q.high.status, q.low.status):
        notes.append(
            "One side only equals an earlier morning extreme; the other side is a strictly new extreme, "
            "so the confirmed qualification condition is met without a tie policy."
        )

    # 2. Contiguous closed candles after the reference group, in order.
    run: list[Candle] = []
    stop_kind: Literal["missing", "forming", "end"] = "end"
    stop_slot: time | None = None
    for slot in POST_REFERENCE_SLOTS:
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
            post_gaps = [s for s in POST_REFERENCE_SLOTS if s not in candles and is_gap(s)]
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
                f"{qualified} No candle from 10:50 to 15:25 closed strictly outside the range; "
                "wick-only crossings and closes on a boundary do not count. No entry."
            ),
            notes=tuple(notes),
            **base,
        )

    breakout_text = _breakout_text(breakout)
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
        return Evaluation(
            state=ResultState.AWAITING_ENTRY,
            reason=(
                f"{qualified} {breakout_text} Entry is the open of the {hhmm(entry_slot)} candle, "
                f"which is not available yet ({as_of_text})."
            ),
            notes=tuple(notes),
            breakout=breakout,
            entry=entry_from_next_candle(breakout, None),
            **base,
        )

    entry = entry_from_next_candle(breakout, entry_candle)
    return Evaluation(
        state=ResultState.ENTRY_IDENTIFIED,
        reason=(
            f"{qualified} {breakout_text} {breakout.signal.value.capitalize()} entry reference: open of the "
            f"{hhmm(entry_candle.start)} candle, {format_price(entry_candle.open)}."
        ),
        notes=tuple(notes),
        breakout=breakout,
        entry=entry,
        **base,
    )
