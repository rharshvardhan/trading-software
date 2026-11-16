"""Builders for clearly labeled SYNTHETIC sessions (EXAMPLES.md section 5).

Used only by tests and by ``scripts/generate_synthetic_fixtures.py``. The strategy,
service, and providers never call this module, so synthetic prices cannot leak into a
Dhan request. Every synthetic instrument uses a fictional ``SYN-`` symbol.

Baseline session (fixed range 100.00 to 110.00, as in EXAMPLES.md):

* Earlier morning (09:15 to 10:25): highs at most 108.00 (09:50), low 99.50 (09:20).
* Reference: 10:30 makes the new session high 110.00; 10:40 has the reference low
  100.00, which is *not* a session low because 09:20 traded at 99.50.
* After 10:45: candles stay inside the range unless a scenario changes them.

So the baseline is a **high-qualified SHORT setup** (REVERSAL_DIRECTION_SPEC.md):
only a close below 100.00 may produce an entry. ``low_qualified()`` gives the mirror
LONG setup: an earlier 111.00 high and an earlier 101.00 low.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Self

from trading_scanner.market import (
    EARLIER_SLOTS,
    IST,
    POST_REFERENCE_SLOTS,
    SESSION_SLOTS,
    THREE_CANDLE_0945,
    TWO_CANDLE_1050,
    at,
)
from trading_scanner.models import RawCandle

SYNTHETIC_LABEL = "SYNTHETIC: invented prices for offline testing and demonstration; not market data."
SYNTHETIC_DATE = date(2026, 11, 13)
SYNTHETIC_VOLUME = 1000

Row = tuple[str, str, str, str]

BASELINE_REFERENCE: dict[time, Row] = {
    time(10, 30): ("105.00", "110.00", "104.80", "109.00"),
    time(10, 35): ("109.00", "109.50", "103.00", "103.50"),
    time(10, 40): ("103.50", "104.00", "100.00", "101.00"),
    time(10, 45): ("101.00", "103.00", "100.50", "102.50"),
}
MORNING_ROW: Row = ("104.00", "105.00", "103.00", "104.50")
LATER_ROW: Row = ("105.00", "106.00", "104.00", "105.00")


def _slot(hhmm: str) -> time:
    hours, minutes = hhmm.split(":")
    return time(int(hours), int(minutes))


class SyntheticSession:
    """A mutable synthetic five-minute session on a given date."""

    def __init__(self, trading_date: date = SYNTHETIC_DATE) -> None:
        self.trading_date = trading_date
        self._rows: dict[time, Row] = {}
        for slot in EARLIER_SLOTS:
            self._rows[slot] = MORNING_ROW
        self._rows[time(9, 20)] = ("103.00", "104.00", "99.50", "101.00")
        self._rows[time(9, 50)] = ("105.00", "108.00", "104.50", "107.00")
        self._rows.update(BASELINE_REFERENCE)
        for slot in POST_REFERENCE_SLOTS:
            self._rows[slot] = LATER_ROW

    def set(self, hhmm: str, open_: str, high: str, low: str, close: str) -> Self:
        slot = _slot(hhmm)
        if slot not in SESSION_SLOTS:
            raise ValueError(f"{hhmm} is not a session slot")
        self._rows[slot] = (open_, high, low, close)
        return self

    def drop(self, *labels: str) -> Self:
        for hhmm in labels:
            self._rows.pop(_slot(hhmm), None)
        return self

    def row(self, hhmm: str) -> Row:
        return self._rows[_slot(hhmm)]

    def _selected(self, through: str | None) -> list[time]:
        limit = _slot(through) if through else None
        return [s for s in sorted(self._rows) if limit is None or s <= limit]

    def raw_candles(self, through: str | None = None) -> list[RawCandle]:
        return [
            RawCandle(at(self.trading_date, slot), *self._rows[slot], SYNTHETIC_VOLUME)
            for slot in self._selected(through)
        ]

    def json_rows(self, through: str | None = None) -> list[list[Any]]:
        return [
            [at(self.trading_date, slot).isoformat(), *self._rows[slot], SYNTHETIC_VOLUME]
            for slot in self._selected(through)
        ]


def low_qualified(trading_date: date = SYNTHETIC_DATE) -> SyntheticSession:
    """Mirror of the baseline: the reference low 100.00 is the new morning low (LONG setup)."""
    return (
        SyntheticSession(trading_date)
        .set("09:50", "105.00", "111.00", "104.50", "107.00")
        .set("09:20", "103.00", "104.00", "101.00", "101.50")
    )


THREE_CANDLE_REFERENCE: dict[time, Row] = {
    time(9, 45): ("105.00", "110.00", "104.80", "109.00"),
    time(9, 50): ("109.00", "109.50", "103.00", "103.50"),
    time(9, 55): ("103.50", "104.00", "100.00", "101.00"),
}


def three_candle_session(side: str = "short", trading_date: date = SYNTHETIC_DATE) -> SyntheticSession:
    """09:45 window (THREE_CANDLE_0945_REVERSAL_SPEC.md section 10): reference range 100.00 to 110.00.

    ``side="short"``: earlier high 108.00 and low 95.00, so only the high is new (SHORT setup).
    ``side="long"``: earlier high 115.00 and low 103.00, so only the low is new (LONG setup).
    Every candle from 10:00 onward stays inside the range unless a test changes it.
    """
    session = SyntheticSession(trading_date)
    for slot in SESSION_SLOTS:
        session._rows[slot] = LATER_ROW
    for slot in THREE_CANDLE_0945.earlier_slots:
        session._rows[slot] = MORNING_ROW  # high 105.00, low 103.00
    session._rows.update(THREE_CANDLE_REFERENCE)
    if side == "short":
        session.set("09:30", "105.00", "108.00", "104.50", "107.00").set("09:20", "97.00", "98.00", "95.00", "96.50")
    elif side == "long":
        session.set("09:30", "105.00", "115.00", "104.50", "107.00")
    else:
        raise ValueError("side must be 'short' or 'long'")
    return session


TWO_CANDLE_REFERENCE: dict[time, Row] = {
    time(10, 50): ("105.00", "110.00", "104.80", "109.00"),
    time(10, 55): ("109.00", "109.50", "100.00", "101.00"),
}


def two_candle_session(side: str = "short", trading_date: date = SYNTHETIC_DATE) -> SyntheticSession:
    """10:50 window (TWO_CANDLE_1050_REVERSAL_SPEC.md section 10): reference range 100.00 to 110.00.

    ``side="short"``: the nineteen earlier candles (09:15-10:45) have high 108.00 and low 95.00,
    so only the high is new (SHORT setup). ``side="long"``: earlier high 115.00 and low 103.00,
    so only the low is new (LONG setup). Every candle from 11:00 onward stays inside the range
    unless a test changes it.
    """
    session = SyntheticSession(trading_date)
    for slot in SESSION_SLOTS:
        session._rows[slot] = LATER_ROW
    for slot in TWO_CANDLE_1050.earlier_slots:
        session._rows[slot] = MORNING_ROW  # high 105.00, low 103.00
    session._rows.update(TWO_CANDLE_REFERENCE)
    if side == "short":
        session.set("10:00", "105.00", "108.00", "104.50", "107.00").set("09:20", "97.00", "98.00", "95.00", "96.50")
    elif side == "long":
        session.set("10:00", "105.00", "115.00", "104.50", "107.00")
    else:
        raise ValueError("side must be 'short' or 'long'")
    return session


def as_of(hhmm: str, trading_date: date = SYNTHETIC_DATE) -> datetime:
    return datetime.combine(trading_date, _slot(hhmm), tzinfo=IST)


@dataclass(frozen=True)
class Scenario:
    symbol: str
    name: str
    description: str
    session: SyntheticSession
    as_of: str = "15:30"
    through: str | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    window: str = "1030_four_candle"  # the strategy window the expected result applies to

    def document(self) -> dict[str, Any]:
        return {
            "fixture_format": 1,
            "kind": "synthetic",
            "label": SYNTHETIC_LABEL,
            "instrument": {"symbol": self.symbol, "name": self.name, "exchange": "NSE", "segment": "cash_equity"},
            "trading_date": self.session.trading_date.isoformat(),
            "timezone": "Asia/Kolkata",
            "interval_minutes": 5,
            "as_of": as_of(self.as_of, self.session.trading_date).isoformat(),
            "source": "Generated by scripts/generate_synthetic_fixtures.py from trading_scanner.synthetic",
            "notes": [self.description],
            "expected": {**self.expected, "strategy_window": self.window},
            "candles": self.session.json_rows(self.through),
        }


def demo_scenarios() -> list[Scenario]:
    """The synthetic demonstration fixtures served by the fixture provider."""
    return [
        Scenario(
            "SYN-LONG",
            "Synthetic long reversal",
            "DIR-03: the reference group makes the new morning low only (LONG setup); the 11:15 candle closes "
            "at 111.00 above 110.00 and the 11:20 candle opens at 111.20.",
            low_qualified()
            .set("11:15", "108.00", "111.50", "107.80", "111.00")
            .set("11:20", "111.20", "111.90", "110.60", "111.40"),
            expected={"state": "entry_identified", "signal": "long", "breakout": "11:15", "entry": "11:20",
                      "entry_price": "111.20"},
        ),
        Scenario(
            "SYN-SHORT",
            "Synthetic short reversal",
            "DIR-01: the reference group makes the new morning high only (SHORT setup); the 10:50 candle closes "
            "at 99.00 below 100.00 and the 10:55 candle opens at 98.80.",
            SyntheticSession()
            .set("10:50", "101.00", "101.50", "98.50", "99.00")
            .set("10:55", "98.80", "99.20", "98.10", "98.40"),
            expected={"state": "entry_identified", "signal": "short", "breakout": "10:50", "entry": "10:55",
                      "entry_price": "98.80"},
        ),
        Scenario(
            "SYN-DELAYED",
            "Synthetic delayed short reversal",
            "DIR-06/07/09: SHORT setup with wick-only crossings at 11:00 and 11:30 and boundary closes at 11:10 "
            "and 11:40; the first close outside is 12:00 (99.10), entry at the 12:05 open 99.00; a later reversal "
            "and new high at 13:00 do not change the result.",
            SyntheticSession()
            .set("11:00", "108.00", "111.00", "107.50", "109.00")
            .set("11:10", "108.50", "110.40", "108.00", "110.00")
            .set("11:30", "102.00", "102.50", "99.00", "101.00")
            .set("11:40", "101.50", "101.80", "99.80", "100.00")
            .set("12:00", "101.00", "101.20", "98.60", "99.10")
            .set("12:05", "99.00", "99.40", "98.20", "98.50")
            .set("13:00", "108.00", "112.00", "107.50", "111.50"),
            expected={"state": "entry_identified", "signal": "short", "breakout": "12:00", "entry": "12:05",
                      "entry_price": "99.00"},
        ),
        Scenario(
            "SYN-WRONGWAY",
            "Synthetic wrong-direction close",
            "CAN-02/CAN-07: SHORT setup (new morning high), but the first close outside is the 11:15 candle at "
            "111.00, above the range, so the setup is cancelled at 11:20. The later 12:00 close below 100.00 does not "
            "revive it.",
            SyntheticSession()
            .set("11:15", "108.00", "111.50", "107.80", "111.00")
            .set("12:00", "101.00", "101.20", "98.60", "99.10"),
            expected={"state": "setup_cancelled", "cancelled": "11:15"},
        ),
        Scenario(
            "SYN-BOTHSIDES",
            "Synthetic setup with both extremes",
            "The reference group makes both the new morning high (110.00) and the new morning low (100.00); "
            "direction priority is an open rule.",
            SyntheticSession().set("09:20", "103.00", "104.00", "101.00", "101.50"),
            expected={"state": "needs_rule_decision", "rule_decision": "both_sides_qualified"},
        ),
        Scenario(
            "SYN-NOTQUAL",
            "Synthetic setup that does not qualify",
            "A03/DIR-05: an earlier 112.00 high (09:50) and 98.00 low (09:20) lie outside the reference group; the "
            "later 11:00 close above the range is not a strategy entry.",
            SyntheticSession()
            .set("09:50", "105.00", "112.00", "104.50", "107.00")
            .set("09:20", "103.00", "104.00", "98.00", "101.00")
            .set("11:00", "108.00", "111.50", "107.80", "111.00"),
            expected={"state": "not_qualified"},
        ),
        Scenario(
            "SYN-TIE",
            "Synthetic repeated equal high",
            "A20: the reference high 110.00 only equals the earlier 09:50 high and no new low is made.",
            SyntheticSession().set("09:50", "105.00", "110.00", "104.50", "107.00"),
            expected={"state": "needs_rule_decision", "rule_decision": "equal_repeated_extreme"},
        ),
        Scenario(
            "SYN-GAP",
            "Synthetic gap beyond the range",
            "A21: SHORT setup; the 11:00 candle opens at 99.50 and stays entirely below 100.00 (high 99.80).",
            SyntheticSession()
            .set("11:00", "99.50", "99.80", "98.90", "99.00")
            .set("11:05", "98.90", "99.10", "98.40", "98.60"),
            expected={"state": "needs_rule_decision", "rule_decision": "gap_beyond_range"},
        ),
        Scenario(
            "SYN-NOBREAK",
            "Synthetic session without a breakout",
            "A24: the session qualifies, but every later close stays inside or on the range, including a wick to "
            "111.00 at 12:30 and a close exactly on 100.00 at 14:00.",
            SyntheticSession()
            .set("12:30", "108.00", "111.00", "107.50", "109.50")
            .set("14:00", "101.00", "101.50", "99.40", "100.00"),
            expected={"state": "no_breakout"},
        ),
        Scenario(
            "SYN-LASTCANDLE",
            "Synthetic breakout on the last candle",
            "A22: SHORT setup; the first close outside is the 15:25 candle (99.00); no same-session candle follows.",
            SyntheticSession().set("15:25", "101.00", "101.20", "98.80", "99.00"),
            expected={"state": "entry_unavailable_session_end", "signal": "short", "breakout": "15:25"},
        ),
        Scenario(
            "SYN-MISSING",
            "Synthetic session missing a morning candle",
            "A13: the 10:00 candle is absent, so an earlier extreme cannot be ruled out.",
            SyntheticSession().drop("10:00"),
            expected={"state": "invalid_data", "missing": ["10:00"]},
        ),
        Scenario(
            "SYN-AWAITENTRY",
            "Synthetic in-session snapshot awaiting entry",
            "A11: snapshot at 11:05:00; SHORT setup; the 11:00 candle closed at 99.00 below 100.00 and the 11:05 "
            "entry candle has not been delivered yet.",
            SyntheticSession().set("11:00", "101.00", "101.40", "98.70", "99.00"),
            as_of="11:05",
            through="11:00",
            expected={"state": "awaiting_entry", "signal": "short", "breakout": "11:00", "expected_entry": "11:05"},
        ),
        Scenario(
            "SYN-FORMING",
            "Synthetic in-session snapshot with a forming candle",
            "A10/DIR-08: snapshot at 11:03; the 11:00 candle trades below 100.00 but is still forming.",
            SyntheticSession().set("11:00", "101.00", "101.20", "98.90", "99.00"),
            as_of="11:03",
            through="11:00",
            expected={"state": "waiting_for_breakout"},
        ),
        Scenario(
            "SYN-0945-SHORT",
            "Synthetic 09:45 short reversal",
            "09:45 SHORT: 10:00 first break, 10:05 later confirmation close below 100.00, "
            "then entry at the 10:10 open 98.80 (THREE_CANDLE_0945_CONFIRMATION_SPEC.md).",
            three_candle_session("short")
            .set("10:00", "101.00", "101.50", "98.50", "99.00")
            .set("10:05", "98.80", "99.20", "98.10", "98.40")
            .set("10:10", "98.80", "99.20", "98.10", "98.40"),
            expected={"state": "entry_identified", "signal": "short", "breakout": "10:05", "entry": "10:10",
                      "entry_price": "98.80"},
            window="0945_three_candle",
        ),
        Scenario(
            "SYN-0945-LONG",
            "Synthetic 09:45 long reversal",
            "09:45 LONG: new morning low only; 10:00 first break above 110.00, 10:05 later confirmation close "
            "above 110.00, then entry at the 10:10 open 111.20 (THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md).",
            three_candle_session("long")
            .set("10:00", "108.00", "111.50", "107.80", "111.00")
            .set("10:05", "111.20", "111.90", "110.60", "111.40")
            .set("10:10", "111.20", "111.90", "110.60", "111.40"),
            expected={"state": "entry_identified", "signal": "long", "breakout": "10:05", "entry": "10:10",
                      "entry_price": "111.20"},
            window="0945_three_candle",
        ),
        Scenario(
            "SYN-0945-CANCEL",
            "Synthetic 09:45 cancelled long setup",
            "09:45 LONG third point: the 10:00 candle's lower wick reaches 99.50, below the reference low 100.00, "
            "and closes back inside at 100.50; a wick is sufficient, so the setup is cancelled before entry. The "
            "later 11:00 close above 110.00 does not revive it (THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md).",
            three_candle_session("long")
            .set("10:00", "101.00", "101.50", "99.50", "100.50")
            .set("11:00", "108.00", "111.50", "107.80", "111.00"),
            expected={"state": "setup_cancelled", "cancelled": "10:00"},
            window="0945_three_candle",
        ),
        Scenario(
            "SYN-1050-SHORT",
            "Synthetic 10:50 short reversal",
            "10:50 window P03: new morning high only (SHORT setup); the 11:00 candle closes at 99.00 below 100.00 "
            "and the 11:05 candle opens at 98.80.",
            two_candle_session("short")
            .set("11:00", "101.00", "101.50", "98.50", "99.00")
            .set("11:05", "98.80", "99.20", "98.10", "98.40"),
            expected={"state": "entry_identified", "signal": "short", "breakout": "11:00", "entry": "11:05",
                      "entry_price": "98.80"},
            window="1050_two_candle",
        ),
        Scenario(
            "SYN-1050-LONG",
            "Synthetic 10:50 long reversal",
            "10:50 window P04: new morning low only (LONG setup); the 11:00 candle closes at 111.00 above 110.00 "
            "and the 11:05 candle opens at 111.20.",
            two_candle_session("long")
            .set("11:00", "108.00", "111.50", "107.80", "111.00")
            .set("11:05", "111.20", "111.90", "110.60", "111.40"),
            expected={"state": "entry_identified", "signal": "long", "breakout": "11:00", "entry": "11:05",
                      "entry_price": "111.20"},
            window="1050_two_candle",
        ),
        Scenario(
            "SYN-1050-CANCEL",
            "Synthetic 10:50 cancelled short setup",
            "10:50 window P07/P08: SHORT setup; the 11:00 candle closes at 111.00 above 110.00, cancelling the "
            "setup at 11:05; the later 12:00 close below 100.00 does not revive it.",
            two_candle_session("short")
            .set("11:00", "108.00", "111.50", "107.80", "111.00")
            .set("12:00", "101.00", "101.50", "98.50", "99.00"),
            expected={"state": "setup_cancelled", "cancelled": "11:00"},
            window="1050_two_candle",
        ),
        Scenario(
            "SYN-EARLY",
            "Synthetic in-session snapshot before the range is final",
            "Snapshot at 10:42; the 10:40 candle is still forming and 10:45 has not started.",
            SyntheticSession(),
            as_of="10:42",
            through="10:40",
            expected={"state": "waiting_for_reference"},
        ),
    ]
