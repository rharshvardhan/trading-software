"""Shared test helpers. All prices here are SYNTHETIC unless loaded from an observation file."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from trading_scanner.config import PACKAGED_FIXTURE_DIR
from trading_scanner.market import IST
from trading_scanner.models import Candle, Instrument, ProviderCandles, ProviderName, RawCandle
from trading_scanner.normalize import normalize_candles
from trading_scanner.providers import CandleProvider, ProviderError, SymbolResolutionError
from trading_scanner.providers.fixture import FixtureFile
from trading_scanner.service import ScanService
from trading_scanner.strategy import Evaluation, evaluate_session
from trading_scanner.synthetic import SyntheticSession, as_of

FIXED_NOW = datetime(2026, 11, 15, 12, 0, tzinfo=IST)
OBSERVATIONS = PACKAGED_FIXTURE_DIR / "observations"


def fixed_clock() -> datetime:
    return FIXED_NOW


def make_service(provider_factory: Callable[[ProviderName], CandleProvider] | None = None) -> ScanService:
    return ScanService(provider_factory=provider_factory, clock=fixed_clock)


def evaluate(session: SyntheticSession, at: str = "15:30", through: str | None = None) -> Evaluation:
    """Normalize and evaluate a synthetic session as of a market time on its date."""
    normalization = normalize_candles(session.raw_candles(through), session.trading_date, as_of(at, session.trading_date))
    assert normalization.session is not None, normalization.problems
    return evaluate_session(normalization.session)


def load_observation(filename: str) -> FixtureFile:
    return FixtureFile.model_validate(json.loads((OBSERVATIONS / filename).read_text()))


def observed_candles(fixture: FixtureFile) -> dict[str, Candle]:
    """Observed candles keyed by HH:MM, built only from recorded rows."""
    out = {}
    for row in fixture.candles:
        candle = Candle(start=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5])
        out[candle.start.strftime("%H:%M")] = candle
    return out


class InMemoryProvider(CandleProvider):
    """A test provider with explicit per-symbol behavior (synthetic sessions or errors)."""

    name = "fixture"

    def __init__(
        self,
        sessions: dict[str, tuple[SyntheticSession, str, str | None]] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.sessions = sessions or {}
        self.errors = errors or {}

    def resolve(self, stock_name: str) -> Instrument:
        symbol = stock_name.strip().upper()
        if symbol not in self.sessions and symbol not in self.errors:
            raise SymbolResolutionError(f"'{stock_name}' is unknown")
        return Instrument(symbol=symbol, name=symbol, synthetic=True)

    def fetch_candles(self, instrument: Instrument, trading_date: date) -> ProviderCandles:
        if instrument.symbol in self.errors:
            raise self.errors[instrument.symbol]
        session, at, through = self.sessions[instrument.symbol]
        return ProviderCandles(
            instrument=instrument,
            trading_date=trading_date,
            candles=tuple(session.raw_candles(through)),
            as_of=as_of(at, session.trading_date),
            source="fixture:in-memory",
            synthetic=True,
            data_label="SYNTHETIC test data",
        )


def raw(start: str, o: str, h: str, l: str, c: str, v: int | None = 1000) -> RawCandle:
    return RawCandle(start, o, h, l, c, v)


def write_fixture(directory: Path, name: str, document: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(document))


__all__ = ["ProviderError"]
