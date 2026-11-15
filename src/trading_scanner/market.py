"""NSE cash-session calendar constants for the five-minute strategy (SPEC.md R01, D02)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TIMEZONE_NAME = "Asia/Kolkata"
INTERVAL = timedelta(minutes=5)
INTERVAL_LABEL = "5m"

SESSION_OPEN = time(9, 15)
LAST_CANDLE = time(15, 25)
SESSION_CLOSE = time(15, 30)


def _slots(first: time, last: time) -> tuple[time, ...]:
    out: list[time] = []
    cursor = datetime.combine(date(2000, 1, 1), first)
    end = datetime.combine(date(2000, 1, 1), last)
    while cursor <= end:
        out.append(cursor.time())
        cursor += INTERVAL
    return tuple(out)


SESSION_SLOTS = _slots(SESSION_OPEN, LAST_CANDLE)
"""All 75 candle start labels of a normal session, 09:15 through 15:25."""

EARLIER_SLOTS = _slots(time(9, 15), time(10, 25))
"""The 15 morning candles before the reference group."""

REFERENCE_SLOTS = (time(10, 30), time(10, 35), time(10, 40), time(10, 45))
"""The four reference candles (SPEC.md R02)."""

QUALIFICATION_SLOTS = EARLIER_SLOTS + REFERENCE_SLOTS
"""The 19 candles from 09:15 through 10:45 used for qualification (SPEC.md R03)."""

POST_REFERENCE_SLOTS = _slots(time(10, 50), LAST_CANDLE)
"""Candles that may confirm a breakout, 10:50 through 15:25 (SPEC.md R05)."""

assert len(SESSION_SLOTS) == 75 and len(EARLIER_SLOTS) == 15 and len(QUALIFICATION_SLOTS) == 19


def ist_now() -> datetime:
    """The current time in Indian market time."""
    return datetime.now(IST)


def at(trading_date: date, slot: time) -> datetime:
    """Timezone-aware Indian market time for a slot on a date."""
    return datetime.combine(trading_date, slot, tzinfo=IST)


def next_slot(slot: time) -> time | None:
    """The immediately following scheduled slot in the same session, or None after 15:25."""
    index = SESSION_SLOTS.index(slot)
    return SESSION_SLOTS[index + 1] if index + 1 < len(SESSION_SLOTS) else None


def session_close(trading_date: date) -> datetime:
    return at(trading_date, SESSION_CLOSE)


def hhmm(value: time | datetime) -> str:
    return value.strftime("%H:%M")


def describe_slots(slots: list[time] | tuple[time, ...]) -> str:
    """Compress slot labels into readable runs, e.g. '09:15-10:25 (15 candles), 11:00'."""
    if not slots:
        return ""
    ordered = sorted(slots)
    runs: list[list[time]] = [[ordered[0]]]
    for slot in ordered[1:]:
        previous = runs[-1][-1]
        if SESSION_SLOTS.index(slot) == SESSION_SLOTS.index(previous) + 1:
            runs[-1].append(slot)
        else:
            runs.append([slot])
    parts = []
    for run in runs:
        if len(run) == 1:
            parts.append(hhmm(run[0]))
        else:
            parts.append(f"{hhmm(run[0])}-{hhmm(run[-1])} ({len(run)} candles)")
    return ", ".join(parts)
