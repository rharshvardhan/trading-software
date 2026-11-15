"""Validated candle, instrument, request, and result models (SPEC.md sections 5 and 7).

Prices are ``Decimal`` values parsed from source text so decisions never depend on
binary floating-point rounding. JSON output renders prices as decimal strings and
unavailable values as ``null``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from trading_scanner.market import INTERVAL, IST

# --------------------------------------------------------------------------- enums


class ResultState(StrEnum):
    """Per-stock result states (SPEC.md section 4)."""

    WAITING_FOR_REFERENCE = "waiting_for_reference"
    INVALID_DATA = "invalid_data"
    NOT_QUALIFIED = "not_qualified"
    NEEDS_RULE_DECISION = "needs_rule_decision"
    WAITING_FOR_BREAKOUT = "waiting_for_breakout"
    NO_BREAKOUT = "no_breakout"
    AWAITING_ENTRY = "awaiting_entry"
    ENTRY_IDENTIFIED = "entry_identified"
    ENTRY_UNAVAILABLE_SESSION_END = "entry_unavailable_session_end"
    NO_SESSION = "no_session"
    SYMBOL_ERROR = "symbol_error"
    PROVIDER_ERROR = "provider_error"


class ExtremeStatus(StrEnum):
    """How one side of the reference group compares with the earlier morning (D04)."""

    NEW_EXTREME = "new_extreme"
    EQUAL_TO_EARLIER = "equal_to_earlier"
    NOT_EXTREME = "not_extreme"


class QualificationDecision(StrEnum):
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    NEEDS_RULE_DECISION = "needs_rule_decision"


class BreakoutSide(StrEnum):
    ABOVE = "above"
    BELOW = "below"


class Signal(StrEnum):
    LONG = "long"
    SHORT = "short"


class RuleDecisionCode(StrEnum):
    """Open rule questions (SPEC.md section 10) that a result can depend on."""

    EQUAL_REPEATED_EXTREME = "equal_repeated_extreme"
    GAP_BEYOND_RANGE = "gap_beyond_range"


# ------------------------------------------------------------------ value parsing


def parse_price(value: Any) -> Decimal:
    """Parse a price without binary floating-point drift.

    Floats are converted through their shortest round-trip text, which preserves the
    digits a provider printed in JSON (``1384.9`` stays ``1384.9``).
    """
    if isinstance(value, bool):
        raise ValueError("price must be a number, not a boolean")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(repr(value))
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError(f"price {value!r} is not a decimal number") from exc
    else:
        raise ValueError(f"price has unsupported type {type(value).__name__}")
    if not result.is_finite():
        raise ValueError("price must be finite")
    if result <= 0:
        raise ValueError(f"price {result} must be positive")
    return result


def parse_timestamp(value: Any) -> datetime:
    """Parse a provider timestamp and normalize it to Asia/Kolkata.

    Accepts timezone-aware datetimes, ISO 8601 strings with an offset, or epoch
    seconds (interpreted as UTC). Timezone-naive values are rejected because their
    market time would be a guess.
    """
    if isinstance(value, bool):
        raise ValueError("timestamp must not be a boolean")
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError(f"epoch timestamp {value!r} is out of range") from exc
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(f"timestamp {value!r} is not ISO 8601") from exc
    else:
        raise ValueError(f"timestamp has unsupported type {type(value).__name__}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp {value!r} has no timezone; provider timestamps must be timezone-aware")
    return parsed.astimezone(IST)


# ---------------------------------------------------------------- domain models


class Candle(BaseModel):
    """One validated five-minute OHLC candle labeled by its start time (SPEC.md R01)."""

    model_config = ConfigDict(frozen=True)

    start: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None

    @field_validator("start", mode="before")
    @classmethod
    def _start(cls, value: Any) -> datetime:
        return parse_timestamp(value)

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def _price(cls, value: Any) -> Decimal:
        return parse_price(value)

    @field_validator("volume", mode="before")
    @classmethod
    def _volume(cls, value: Any) -> Decimal | None:
        """Volume is informational only (never a trading condition); it must be nonnegative."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            raise ValueError("volume must be a number")
        try:
            number = value if isinstance(value, Decimal) else Decimal(repr(value) if isinstance(value, float) else str(value).strip())
        except InvalidOperation as exc:
            raise ValueError(f"volume {value!r} is not a number") from exc
        if not number.is_finite() or number < 0:
            raise ValueError(f"volume {value!r} must be a finite nonnegative number")
        return number

    @model_validator(mode="after")
    def _ohlc_relationships(self) -> Candle:
        problems = []
        if self.high < self.low:
            problems.append(f"high {self.high} is below low {self.low}")
        if self.high < self.open:
            problems.append(f"high {self.high} is below open {self.open}")
        if self.high < self.close:
            problems.append(f"high {self.high} is below close {self.close}")
        if self.low > self.open:
            problems.append(f"low {self.low} is above open {self.open}")
        if self.low > self.close:
            problems.append(f"low {self.low} is above close {self.close}")
        if problems:
            raise ValueError("OHLC relationships violated: " + "; ".join(problems))
        return self

    @property
    def end(self) -> datetime:
        """When the candle is fully closed: start plus five minutes."""
        return self.start + INTERVAL


class Instrument(BaseModel):
    """A resolved NSE cash-equity instrument. Futures never substitute for a cash stock."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    exchange: Literal["NSE"] = "NSE"
    segment: Literal["cash_equity"] = "cash_equity"
    provider_id: str | None = None
    synthetic: bool = False


@dataclass(frozen=True)
class RawCandle:
    """A candle exactly as a provider supplied it, before validation and normalization."""

    start: Any
    open: Any
    high: Any
    low: Any
    close: Any
    volume: Any = None


@dataclass(frozen=True)
class ProviderCandles:
    """A provider's response for one instrument and date, prior to normalization."""

    instrument: Instrument
    trading_date: date
    candles: tuple[RawCandle, ...]
    as_of: datetime
    source: str
    synthetic: bool
    data_label: str
    provenance: dict[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


# ------------------------------------------------------------------ API request

StockName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
ProviderName = Literal["fixture", "dhan"]
MAX_STOCKS = 100
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_trading_date(value: Any) -> date:
    """Accept a ``date`` or a ``YYYY-MM-DD`` string naming a real calendar date."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and _DATE_PATTERN.match(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise ValueError("trading_date must be a real calendar date in YYYY-MM-DD format")


class ScanRequest(BaseModel):
    """A scan request shared by the terminal and HTTP interfaces (SPEC.md D11, D12)."""

    model_config = ConfigDict(extra="forbid")

    trading_date: date = Field(description="Trading date in YYYY-MM-DD (Asia/Kolkata calendar).")
    stocks: list[StockName] = Field(min_length=1, max_length=MAX_STOCKS)
    provider: ProviderName = Field(description="Explicit data provider; no default and no fallback.")

    @field_validator("trading_date", mode="before")
    @classmethod
    def _date_format(cls, value: Any) -> date:
        return parse_trading_date(value)


# ------------------------------------------------------------------ API results


class CandleOut(BaseModel):
    start: datetime
    end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None

    @classmethod
    def from_candle(cls, candle: Candle) -> CandleOut:
        return cls(
            start=candle.start,
            end=candle.end,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )


class DataCoverage(BaseModel):
    provider: str
    source: str
    synthetic: bool
    data_label: str
    retrieved_at: datetime
    as_of: datetime
    session_complete: bool | None
    last_closed_candle: str | None
    candles_received: int
    candles_in_session: int
    missing_candles: list[str]
    notes: list[str]
    provenance: dict[str, str]


class SideEvidence(BaseModel):
    status: ExtremeStatus
    reference_value: Decimal
    reference_candles: list[str]
    earlier_value: Decimal
    earlier_candles: list[str]


class QualificationOut(BaseModel):
    decision: QualificationDecision
    window: str = "09:15-10:45"
    session_high: Decimal
    session_high_candles: list[str]
    session_low: Decimal
    session_low_candles: list[str]
    high_side: SideEvidence
    low_side: SideEvidence
    qualifying_sides: list[Literal["high", "low"]]


class ReferenceOut(BaseModel):
    candles: list[CandleOut]
    high: Decimal
    low: Decimal
    high_candles: list[str]
    low_candles: list[str]


class BreakoutOut(BaseModel):
    side: BreakoutSide
    signal: Signal
    boundary_value: Decimal
    candle_start: datetime
    candle_end: datetime
    close: Decimal
    confirmed_at: datetime
    entirely_beyond_range: bool
    candle: CandleOut


class EntryOut(BaseModel):
    signal: Signal
    available: bool
    expected_time: datetime | None
    time: datetime | None
    price: Decimal | None
    price_basis: str


class RuleDecisionOut(BaseModel):
    code: RuleDecisionCode
    question: str


RISK_RULES_REASON = "Rules not yet defined"


class RiskOut(BaseModel):
    """Stop-loss, target, exit, and outcome stay null until the user supplies rules (R10)."""

    stop_loss: Decimal | None = None
    targets: list[Decimal] | None = None
    exit_time: datetime | None = None
    exit_price: Decimal | None = None
    outcome: str | None = None
    profit_loss: Decimal | None = None
    reason: str = RISK_RULES_REASON


class StockResult(BaseModel):
    input_name: str
    input_names: list[str]
    instrument: Instrument | None
    trading_date: date
    timezone: str
    interval: str
    strategy_version: str
    provider: str
    synthetic: bool
    state: ResultState
    setup_qualified: bool | None
    reason: str
    notes: list[str]
    rule_decision: RuleDecisionOut | None
    data: DataCoverage | None
    qualification: QualificationOut | None
    reference: ReferenceOut | None
    breakout: BreakoutOut | None
    entry: EntryOut | None
    risk: RiskOut
    candles: list[CandleOut] = Field(
        default_factory=list, description="Validated session candles used for the decision (for charts)."
    )


class InstrumentSuggestion(BaseModel):
    """A search suggestion. Only NSE cash stocks are scannable (SPEC.md section 13, U8)."""

    symbol: str
    name: str
    kind: Literal["stock", "future", "index"]
    exchange: Literal["NSE"] = "NSE"
    underlying: str | None = None
    expiry: date | None = None
    lot_size: int | None = None
    scannable: bool
    synthetic: bool = False
    note: str | None = None


class InstrumentSearchResponse(BaseModel):
    query: str
    provider: str
    results: list[InstrumentSuggestion]


class ScanResponse(BaseModel):
    trading_date: date
    provider: str
    scanned_at: datetime
    strategy_version: str
    timezone: str
    interval: str
    synthetic_data_present: bool
    results: list[StockResult]
