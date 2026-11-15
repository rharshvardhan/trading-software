"""The shared analysis service used by both the terminal runner and FastAPI.

Flow per distinct stock: resolve the instrument, retrieve candles from the explicitly
selected provider, normalize them, evaluate the strategy, and build a result. A failure
for one stock never removes the results of the others.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from trading_scanner import STRATEGY_VERSION
from trading_scanner.config import Settings
from trading_scanner.market import INTERVAL_LABEL, IST, TIMEZONE_NAME, hhmm, ist_now, session_close
from trading_scanner.models import (
    BreakoutOut,
    CandleOut,
    DataCoverage,
    EntryOut,
    Instrument,
    InstrumentSearchResponse,
    ProviderCandles,
    ProviderName,
    QualificationOut,
    ReferenceOut,
    ResultState,
    RiskOut,
    RuleDecisionOut,
    ScanRequest,
    ScanResponse,
    SideEvidence,
    StockResult,
)
from trading_scanner.normalize import normalize_candles
from trading_scanner.providers import (
    CandleProvider,
    NoSessionError,
    ProviderError,
    SymbolResolutionError,
    build_provider,
)
from trading_scanner.providers.base import alias_key
from trading_scanner.strategy import RULE_QUESTIONS, Evaluation, SideAssessment, evaluate_session

ENTRY_PRICE_BASIS = (
    "Open of the candle immediately after the breakout candle; a reference price, not an executed fill."
)


class InputError(ValueError):
    """A structurally valid request that cannot be scanned, such as a future date."""

    def __init__(self, field_name: str, message: str) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.message = message


def unique_names(names: list[str]) -> list[str]:
    """Trim names and drop repeats (case- and spacing-insensitive), keeping input order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in names:
        name = " ".join(raw.split())
        key = alias_key(name)
        if name and key not in seen:
            seen.add(key)
            ordered.append(name)
    return ordered


@dataclass
class _Entry:
    names: list[str]
    instrument: Instrument | None = None
    error: StockResult | None = None
    notes: list[str] = field(default_factory=list)


class ScanService:
    def __init__(
        self,
        provider_factory: Callable[[ProviderName], CandleProvider] | None = None,
        clock: Callable[[], datetime] = ist_now,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings
        self._provider_factory = provider_factory or self._default_factory
        self._clock = clock
        self._providers: dict[str, CandleProvider] = {}

    def _default_factory(self, name: ProviderName) -> CandleProvider:
        return build_provider(name, self._settings or Settings())

    def provider(self, name: ProviderName) -> CandleProvider:
        """The explicitly selected provider, created once per service (surfaces load errors early)."""
        if name not in self._providers:
            self._providers[name] = self._provider_factory(name)
        return self._providers[name]

    def now(self) -> datetime:
        return self._clock().astimezone(IST)

    def search_instruments(self, provider: ProviderName, query: str, limit: int = 12) -> InstrumentSearchResponse:
        """Suggestions for the stock picker; futures and indices are labeled and not scannable."""
        results = self.provider(provider).search(query, limit) if query.strip() else []
        return InstrumentSearchResponse(query=query, provider=provider, results=results)

    def validate_trading_date(self, trading_date: date) -> None:
        today = self.now().date()
        if trading_date > today:
            raise InputError(
                "trading_date",
                f"Trading date {trading_date.isoformat()} is in the future "
                f"(today is {today.isoformat()} in {TIMEZONE_NAME}).",
            )

    def scan(self, request: ScanRequest) -> ScanResponse:
        self.validate_trading_date(request.trading_date)
        scanned_at = self.now()
        provider = self.provider(request.provider)

        entries: list[_Entry] = []
        by_symbol: dict[str, _Entry] = {}
        for name in unique_names(request.stocks):
            try:
                instrument = provider.resolve(name)
            except SymbolResolutionError as exc:
                entries.append(_Entry([name], error=self._error(name, request, ResultState.SYMBOL_ERROR, str(exc))))
                continue
            except ProviderError as exc:
                entries.append(_Entry([name], error=self._error(name, request, ResultState.PROVIDER_ERROR, str(exc))))
                continue
            existing = by_symbol.get(instrument.symbol)
            if existing is not None:
                existing.names.append(name)
                existing.notes.append(
                    f"'{name}' resolves to the same instrument ({instrument.symbol}); reported once."
                )
                continue
            entry = _Entry([name], instrument=instrument)
            by_symbol[instrument.symbol] = entry
            entries.append(entry)

        results = [
            entry.error if entry.error is not None else self._analyze(entry, request, provider)
            for entry in entries
        ]
        return ScanResponse(
            trading_date=request.trading_date,
            provider=request.provider,
            scanned_at=scanned_at,
            strategy_version=STRATEGY_VERSION,
            timezone=TIMEZONE_NAME,
            interval=INTERVAL_LABEL,
            synthetic_data_present=any(r.synthetic for r in results),
            results=results,
        )

    # ------------------------------------------------------------------ internals

    def _base(
        self, names: list[str], request: ScanRequest, instrument: Instrument | None, synthetic: bool | None = None
    ) -> dict:
        if synthetic is None:
            synthetic = bool(instrument is not None and instrument.synthetic)
        return {
            "provider": request.provider,
            "synthetic": synthetic,
            "input_name": names[0],
            "input_names": list(names),
            "instrument": instrument,
            "trading_date": request.trading_date,
            "timezone": TIMEZONE_NAME,
            "interval": INTERVAL_LABEL,
            "strategy_version": STRATEGY_VERSION,
            "risk": RiskOut(),
        }

    def _error(
        self,
        name: str,
        request: ScanRequest,
        state: ResultState,
        reason: str,
        instrument: Instrument | None = None,
        names: list[str] | None = None,
        notes: list[str] | None = None,
        data: DataCoverage | None = None,
    ) -> StockResult:
        return StockResult(
            **self._base(names or [name], request, instrument, data.synthetic if data else None),
            state=state,
            setup_qualified=None,
            reason=reason,
            notes=notes or [],
            rule_decision=None,
            data=data,
            qualification=None,
            reference=None,
            breakout=None,
            entry=None,
        )

    def _analyze(self, entry: _Entry, request: ScanRequest, provider: CandleProvider) -> StockResult:
        instrument = entry.instrument
        assert instrument is not None
        name = entry.names[0]
        try:
            response = provider.fetch_candles(instrument, request.trading_date)
        except NoSessionError as exc:
            return self._error(name, request, ResultState.NO_SESSION, str(exc), instrument, entry.names, entry.notes)
        except ProviderError as exc:
            return self._error(
                name, request, ResultState.PROVIDER_ERROR, str(exc), instrument, entry.names, entry.notes
            )
        retrieved_at = self.now()

        normalization = normalize_candles(response.candles, request.trading_date, response.as_of)
        if normalization.session is None:
            data = self._coverage(provider.name, response, retrieved_at, normalization.notes, None, 0, [])
            reason = "Candle data is contradictory, so no decision can be made: " + " ".join(normalization.problems)
            return self._error(
                name, request, ResultState.INVALID_DATA, reason, instrument, entry.names, entry.notes, data
            )

        evaluation = evaluate_session(normalization.session)
        data = self._coverage(
            provider.name,
            response,
            retrieved_at,
            normalization.notes,
            evaluation,
            len(normalization.session.candles),
            [hhmm(s) for s in evaluation.missing_slots],
        )
        candles = [CandleOut.from_candle(c) for c in normalization.session.candles.values()]
        return self._from_evaluation(entry, request, evaluation, data, candles)

    def _coverage(
        self,
        provider_name: str,
        response: ProviderCandles,
        retrieved_at: datetime,
        normalization_notes: tuple[str, ...],
        evaluation: Evaluation | None,
        in_session: int,
        missing: list[str],
    ) -> DataCoverage:
        aware = response.as_of.tzinfo is not None
        as_of = response.as_of.astimezone(IST) if aware else response.as_of
        if evaluation is not None:
            complete: bool | None = evaluation.session_complete
        else:
            complete = as_of >= session_close(response.trading_date) if aware else None
        last_closed = evaluation.last_closed_slot if evaluation else None
        return DataCoverage(
            provider=provider_name,
            source=response.source,
            synthetic=response.synthetic,
            data_label=response.data_label,
            retrieved_at=retrieved_at,
            as_of=as_of,
            session_complete=complete,
            last_closed_candle=hhmm(last_closed) if last_closed else None,
            candles_received=len(response.candles),
            candles_in_session=in_session,
            missing_candles=missing,
            notes=[*response.notes, *normalization_notes],
            provenance=dict(response.provenance),
        )

    @staticmethod
    def _side(side: SideAssessment) -> SideEvidence:
        return SideEvidence(
            status=side.status,
            reference_value=side.reference_value,
            reference_candles=[hhmm(s) for s in side.reference_slots],
            earlier_value=side.earlier_value,
            earlier_candles=[hhmm(s) for s in side.earlier_slots],
        )

    def _from_evaluation(
        self,
        entry: _Entry,
        request: ScanRequest,
        evaluation: Evaluation,
        data: DataCoverage,
        candles: list[CandleOut],
    ) -> StockResult:
        q = evaluation.qualification
        qualification = reference = breakout = entry_out = None
        if q is not None:
            qualification = QualificationOut(
                decision=q.decision,
                session_high=q.session_high,
                session_high_candles=[hhmm(s) for s in q.session_high_slots],
                session_low=q.session_low,
                session_low_candles=[hhmm(s) for s in q.session_low_slots],
                high_side=self._side(q.high),
                low_side=self._side(q.low),
                qualifying_sides=q.qualifying_sides,
            )
            reference = ReferenceOut(
                candles=[CandleOut.from_candle(c) for c in evaluation.reference_candles],
                high=q.reference.high,
                low=q.reference.low,
                high_candles=[hhmm(s) for s in q.reference.high_slots],
                low_candles=[hhmm(s) for s in q.reference.low_slots],
            )
        if evaluation.breakout is not None:
            b = evaluation.breakout
            breakout = BreakoutOut(
                side=b.side,
                signal=b.signal,
                boundary_value=b.boundary_value,
                candle_start=b.candle.start,
                candle_end=b.candle.end,
                close=b.candle.close,
                confirmed_at=b.confirmed_at,
                entirely_beyond_range=b.entirely_beyond,
                candle=CandleOut.from_candle(b.candle),
            )
        if evaluation.entry is not None:
            e = evaluation.entry
            entry_out = EntryOut(
                signal=e.signal,
                available=e.candle is not None,
                expected_time=e.expected_start,
                time=e.candle.start if e.candle is not None else None,
                price=e.price,
                price_basis=ENTRY_PRICE_BASIS,
            )
        rule = (
            RuleDecisionOut(code=evaluation.rule_decision, question=RULE_QUESTIONS[evaluation.rule_decision])
            if evaluation.rule_decision is not None
            else None
        )
        return StockResult(
            **self._base(entry.names, request, entry.instrument, data.synthetic),
            state=evaluation.state,
            setup_qualified=evaluation.setup_qualified,
            reason=evaluation.reason,
            notes=[*entry.notes, *evaluation.notes],
            rule_decision=rule,
            data=data,
            qualification=qualification,
            reference=reference,
            breakout=breakout,
            entry=entry_out,
            candles=candles,
        )
