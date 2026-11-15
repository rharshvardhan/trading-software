"""Normalize provider candles into one validated session (SPEC.md section 5, D02, D03).

Nothing here invents data: absent candles stay absent, and contradictory input is
reported as a problem so the result becomes ``invalid_data``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time

from pydantic import ValidationError

from trading_scanner.market import IST, SESSION_SLOTS, hhmm
from trading_scanner.models import Candle, RawCandle, parse_timestamp


@dataclass(frozen=True)
class NormalizedSession:
    """Validated candles for one instrument and date, keyed by slot start label."""

    trading_date: date
    as_of: datetime
    candles: Mapping[time, Candle]
    received: int
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Normalization:
    session: NormalizedSession | None
    problems: tuple[str, ...]
    notes: tuple[str, ...]


def _validation_message(error: ValidationError) -> str:
    messages = []
    for item in error.errors():
        message = str(item.get("msg", "invalid value"))
        message = message.removeprefix("Value error, ")
        location = ".".join(str(part) for part in item.get("loc", ()) if part != "__root__")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages)


def normalize_candles(raw_candles: Sequence[RawCandle], trading_date: date, as_of: datetime) -> Normalization:
    """Validate, isolate, de-duplicate, and order candles for one trading date."""
    problems: list[str] = []
    notes: list[str] = []

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        return Normalization(None, ("Provider as-of time has no timezone.",), ())
    as_of = as_of.astimezone(IST)

    other_dates = 0
    outside_session = 0
    off_grid: list[str] = []
    by_slot: dict[time, Candle] = {}
    identical_duplicates: list[str] = []
    conflicting_duplicates: list[str] = []
    valid_slots = set(SESSION_SLOTS)

    for raw in raw_candles:
        try:
            start = parse_timestamp(raw.start)
        except (ValueError, ArithmeticError) as exc:
            problems.append(f"Unusable candle timestamp: {exc}")
            continue
        if start.date() != trading_date:
            other_dates += 1
            continue
        label = start.time().replace(tzinfo=None)
        if label < SESSION_SLOTS[0] or label > SESSION_SLOTS[-1]:
            outside_session += 1
            continue
        if label not in valid_slots:
            off_grid.append(start.strftime("%H:%M:%S"))
            continue
        try:
            candle = Candle(
                start=start, open=raw.open, high=raw.high, low=raw.low, close=raw.close, volume=raw.volume
            )
        except (ValidationError, ValueError, ArithmeticError) as exc:
            detail = _validation_message(exc) if isinstance(exc, ValidationError) else str(exc)
            problems.append(f"Candle at {hhmm(label)} is invalid: {detail}.")
            continue
        if candle.start > as_of:
            problems.append(
                f"Candle at {hhmm(label)} starts after the data as-of time {as_of.strftime('%H:%M')}, "
                "which is contradictory."
            )
            continue
        existing = by_slot.get(label)
        if existing is None:
            by_slot[label] = candle
        elif existing == candle:
            identical_duplicates.append(hhmm(label))
        else:
            conflicting_duplicates.append(hhmm(label))

    if off_grid:
        problems.append(
            "Candle timestamps not on the five-minute grid starting at 09:15: " + ", ".join(sorted(set(off_grid))) + "."
        )
    for label in sorted(set(conflicting_duplicates)):
        problems.append(f"Conflicting duplicate candles at {label}; the correct values cannot be chosen.")
    if other_dates:
        notes.append(f"Ignored {other_dates} candle(s) dated other than {trading_date.isoformat()}.")
    if outside_session:
        notes.append(f"Ignored {outside_session} candle(s) outside the 09:15-15:25 session (pre-market or after-session).")
    if identical_duplicates:
        notes.append("Removed identical duplicate candle(s) at " + ", ".join(sorted(set(identical_duplicates))) + ".")

    if problems:
        return Normalization(None, tuple(problems), tuple(notes))

    ordered = {slot: by_slot[slot] for slot in sorted(by_slot)}
    session = NormalizedSession(
        trading_date=trading_date,
        as_of=as_of,
        candles=ordered,
        received=len(raw_candles),
        notes=tuple(notes),
    )
    return Normalization(session, (), tuple(notes))
