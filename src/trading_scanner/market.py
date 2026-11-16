"""NSE cash-session calendar constants for the five-minute strategy (SPEC.md R01, D02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TIMEZONE_NAME = "Asia/Kolkata"
INTERVAL = timedelta(minutes=5)
INTERVAL_LABEL = "5m"

SESSION_OPEN = time(9, 15)
LAST_CANDLE = time(15, 25)
SESSION_CLOSE = time(15, 30)


def hhmm(value: time | datetime) -> str:
    return value.strftime("%H:%M")


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


@dataclass(frozen=True)
class ReferenceWindow:
    """One reference-group variant. Every other strategy rule is shared between variants."""

    key: str
    label: str
    count_word: str
    reference_slots: tuple[time, ...]
    earlier_slots: tuple[time, ...]
    post_slots: tuple[time, ...]
    initial_stop_rule: str | None = None
    """How this window's initial stop-loss level is set, or None while the user has not taught it."""
    entry_rule: str = "single_close"
    """"break_then_confirm" (09:45 window, SHORT and LONG): first break, later confirmation, then next-open entry."""

    @property
    def qualification_slots(self) -> tuple[time, ...]:
        return self.earlier_slots + self.reference_slots

    @property
    def range_final_at(self) -> time:
        """When the last reference candle closes; the first later candle starts then."""
        return self.post_slots[0]

    @property
    def reference_text(self) -> str:
        return f"{hhmm(self.reference_slots[0])}-{hhmm(self.reference_slots[-1])}"

    @property
    def qualification_text(self) -> str:
        return f"{hhmm(self.earlier_slots[0])}-{hhmm(self.reference_slots[-1])}"


FOUR_CANDLE_1030 = ReferenceWindow(
    key="1030_four_candle",
    label="10:30 four-candle",
    count_word="four",
    reference_slots=REFERENCE_SLOTS,
    earlier_slots=EARLIER_SLOTS,
    post_slots=POST_REFERENCE_SLOTS,
)
"""The original window (SPEC.md R02/R03): 10:30-10:45, compared with 09:15-10:25, final at 10:50."""

THREE_CANDLE_0945 = ReferenceWindow(
    key="0945_three_candle",
    label="09:45 three-candle",
    count_word="three",
    reference_slots=(time(9, 45), time(9, 50), time(9, 55)),
    earlier_slots=_slots(time(9, 15), time(9, 40)),
    post_slots=_slots(time(10, 0), LAST_CANDLE),
    initial_stop_rule="reference_extreme",  # THREE_CANDLE_0945_STOP_LOSS_SPEC.md
    entry_rule="break_then_confirm",  # THREE_CANDLE_0945_CONFIRMATION_SPEC.md + ..._LONG_CONFIRMATION_SPEC.md
)
"""THREE_CANDLE_0945_REVERSAL_SPEC.md: 09:45-09:55, compared with 09:15-09:40, final at 10:00."""

TWO_CANDLE_1050 = ReferenceWindow(
    key="1050_two_candle",
    label="10:50 two-candle",
    count_word="two",
    reference_slots=(time(10, 50), time(10, 55)),
    earlier_slots=_slots(time(9, 15), time(10, 45)),
    post_slots=_slots(time(11, 0), LAST_CANDLE),
)
"""TWO_CANDLE_1050_REVERSAL_SPEC.md: 10:50-10:55, compared with 09:15-10:45, final at 11:00."""

WINDOWS = {window.key: window for window in (THREE_CANDLE_0945, FOUR_CANDLE_1030, TWO_CANDLE_1050)}
"""Every scan evaluates all windows, reported in this chronological order."""

assert len(THREE_CANDLE_0945.earlier_slots) == 6 and len(THREE_CANDLE_0945.qualification_slots) == 9
assert THREE_CANDLE_0945.range_final_at == time(10, 0) and FOUR_CANDLE_1030.range_final_at == time(10, 50)
assert len(TWO_CANDLE_1050.earlier_slots) == 19 and len(TWO_CANDLE_1050.qualification_slots) == 21
assert TWO_CANDLE_1050.range_final_at == time(11, 0)


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
