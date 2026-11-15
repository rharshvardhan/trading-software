"""Explicit offline fixture provider (SPEC.md D08 to D10).

Serves recorded JSON files only. Each file declares its kind:

* ``synthetic``: invented prices for offline tests and demonstrations, on fictional
  ``SYN-`` instruments. Always flagged ``synthetic``.
* ``chart_observation``: chart-displayed readings from the teaching session. These are
  partial; only candles whose full OHLC was read are served, and nothing is filled in.
* ``provider_recording``: reserved for complete, reviewed provider exports.

A missing recording is reported as a provider error. Nothing is ever substituted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from trading_scanner.models import Instrument, InstrumentSuggestion, ProviderCandles, RawCandle
from trading_scanner.providers.base import (
    CandleProvider,
    NoSessionError,
    ProviderError,
    SymbolResolutionError,
    alias_key,
    match_rank,
)


class FixtureFormatError(Exception):
    """A fixture file is structurally malformed. This is a developer error, raised at load."""


class FixtureInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    exchange: Literal["NSE"] = "NSE"
    segment: Literal["cash_equity"] = "cash_equity"
    aliases: list[str] = Field(default_factory=list)


class FixtureFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_format: Literal[1]
    kind: Literal["synthetic", "chart_observation", "provider_recording"]
    label: str = Field(min_length=1)
    instrument: FixtureInstrument
    trading_date: date
    timezone: Literal["Asia/Kolkata"]
    interval_minutes: Literal[5]
    session: Literal["open", "closed"] = "open"
    as_of: datetime
    source: str = Field(min_length=1)
    user_label: str | None = None
    notes: list[str] = Field(default_factory=list)
    candles: list[list[Any]] = Field(default_factory=list)
    partial_readings: list[dict[str, str]] = Field(default_factory=list)
    expected: dict[str, Any] = Field(default_factory=dict)

    @field_validator("as_of")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must include a timezone offset")
        return value

    @field_validator("candles")
    @classmethod
    def _rows(cls, rows: list[list[Any]]) -> list[list[Any]]:
        for index, row in enumerate(rows):
            if len(row) not in (5, 6):
                raise ValueError(f"candle row {index} must be [start, open, high, low, close, volume?]")
        return rows


@dataclass(frozen=True)
class _Recording:
    path: str
    fixture: FixtureFile


class FixtureProvider(CandleProvider):
    name = "fixture"

    def __init__(self, fixture_dir: Path) -> None:
        self._dir = fixture_dir
        self._instruments: dict[str, Instrument] = {}
        self._aliases: dict[str, set[str]] = {}
        self._recordings: dict[tuple[str, date], _Recording] = {}
        self._load()

    @property
    def fixture_dir(self) -> Path:
        return self._dir

    def _load(self) -> None:
        if not self._dir.is_dir():
            raise FixtureFormatError(f"Fixture directory does not exist: {self._dir}")
        for path in sorted(self._dir.rglob("*.json")):
            relative = path.relative_to(self._dir).as_posix()
            try:
                document = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
                fixture = FixtureFile.model_validate(document)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise FixtureFormatError(f"Malformed fixture {relative}: {exc}") from exc
            if fixture.session == "closed" and fixture.candles:
                raise FixtureFormatError(f"Fixture {relative} declares a closed session but contains candles")
            spec = fixture.instrument
            symbol = spec.symbol.upper()
            synthetic = fixture.kind == "synthetic"
            if synthetic and not symbol.startswith("SYN-"):
                raise FixtureFormatError(f"Synthetic fixture {relative} must use a SYN- symbol, not {symbol}")
            if not synthetic and symbol.startswith("SYN-"):
                raise FixtureFormatError(f"Fixture {relative} uses a SYN- symbol but is not synthetic")
            instrument = Instrument(symbol=symbol, name=spec.name, synthetic=synthetic)
            existing = self._instruments.get(symbol)
            if existing is not None and existing != instrument:
                raise FixtureFormatError(f"Fixture {relative} describes {symbol} inconsistently with another file")
            self._instruments[symbol] = instrument
            for alias in {symbol, spec.name, *spec.aliases}:
                self._aliases.setdefault(alias_key(alias), set()).add(symbol)
            key = (symbol, fixture.trading_date)
            if key in self._recordings:
                raise FixtureFormatError(f"Two fixtures record {symbol} on {fixture.trading_date}")
            self._recordings[key] = _Recording(relative, fixture)

    def known_symbols(self) -> list[str]:
        return sorted(self._instruments)

    def recordings(self) -> list[tuple[str, date, str]]:
        """(symbol, date, kind) for every recording, for listing in help output."""
        return sorted((s, d, r.fixture.kind) for (s, d), r in self._recordings.items())

    def resolve(self, stock_name: str) -> Instrument:
        matches = self._aliases.get(alias_key(stock_name), set())
        if not matches:
            raise SymbolResolutionError(
                f"'{stock_name}' is not a known instrument for the fixture provider. "
                f"Known fixture instruments: {', '.join(self.known_symbols())}."
            )
        if len(matches) > 1:
            raise SymbolResolutionError(
                f"'{stock_name}' is ambiguous; it matches {', '.join(sorted(matches))}. Use the exact symbol."
            )
        return self._instruments[next(iter(matches))]

    def search(self, query: str, limit: int = 12) -> list[InstrumentSuggestion]:
        ranked = []
        for symbol, instrument in self._instruments.items():
            names = [instrument.name] + [a for a, symbols in self._aliases.items() if symbol in symbols]
            ranks = [r for n in names if (r := match_rank(query, symbol, n)) is not None]
            if ranks:
                ranked.append((min(ranks), symbol, instrument))
        return [
            InstrumentSuggestion(
                symbol=symbol,
                name=instrument.name,
                kind="stock",
                scannable=True,
                synthetic=instrument.synthetic,
                note=(
                    "Synthetic test instrument (invented prices)."
                    if instrument.synthetic
                    else "Fixture holds partial chart readings only."
                ),
            )
            for _, symbol, instrument in sorted(ranked)[:limit]
        ]

    def fetch_candles(self, instrument: Instrument, trading_date: date) -> ProviderCandles:
        recording = self._recordings.get((instrument.symbol, trading_date))
        if recording is None:
            dates = sorted(d.isoformat() for (s, d) in self._recordings if s == instrument.symbol)
            raise ProviderError(
                f"No fixture is recorded for {instrument.symbol} on {trading_date.isoformat()} "
                f"(recorded dates: {', '.join(dates) or 'none'}). The fixture provider serves recorded files "
                "only; nothing was substituted."
            )
        fixture = recording.fixture
        if fixture.session == "closed":
            raise NoSessionError(
                f"The fixture records no trading session for {trading_date.isoformat()} ({fixture.label})."
            )
        raw = tuple(RawCandle(*row) for row in fixture.candles)
        notes = list(fixture.notes)
        if fixture.user_label:
            notes.append(f"User-supplied teaching label: {fixture.user_label} (a label, not a computed outcome).")
        provenance = {
            "kind": fixture.kind,
            "file": recording.path,
            "source": fixture.source,
            "recorded_as_of": fixture.as_of.isoformat(),
        }
        if fixture.user_label:
            provenance["user_label"] = fixture.user_label
        return ProviderCandles(
            instrument=instrument,
            trading_date=trading_date,
            candles=raw,
            as_of=fixture.as_of,
            source=f"fixture:{recording.path}",
            synthetic=fixture.kind == "synthetic",
            data_label=fixture.label,
            provenance=provenance,
            notes=tuple(notes),
        )
