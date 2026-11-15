"""Dhan Data API provider (SPEC.md section 13).

Contract, from Dhan's v2 documentation and confirmed with a live response on 15 November 2026:

* Instruments come from Dhan's public compact scrip master CSV. Only NSE cash equities
  qualify (``SEM_EXM_EXCH_ID=NSE``, ``SEM_SEGMENT=E``, ``SEM_INSTRUMENT_NAME=EQUITY``),
  so a future or option can never stand in for a stock.
* Candles come from ``POST /v2/charts/intraday`` with ``interval`` 5. The response holds
  parallel arrays (``open``, ``high``, ``low``, ``close``, ``volume``, ``timestamp``).
* Timestamps are epoch seconds marking the candle **start**. A live HCLTECH response for
  13 Nov 2026 matched the chart's opens and highs at the same start labels.
* ``fromDate`` is exclusive, so requests start at 09:00. The live intraday responses
  ended at the 15:10 candle; later candles are reported as missing, never invented.

Prices are parsed as decimals, never binary floats. Credentials are sent only as request
headers and never appear in errors, logs, or results. Fixture data is never substituted.
"""

from __future__ import annotations

import csv
import json
import time as time_module
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from trading_scanner.config import Settings
from trading_scanner.market import IST, LAST_CANDLE, SESSION_OPEN, hhmm, ist_now, session_close
from trading_scanner.models import Instrument, InstrumentSuggestion, ProviderCandles, RawCandle
from trading_scanner.providers.base import (
    CandleProvider,
    NoSessionError,
    ProviderError,
    SymbolResolutionError,
    alias_key,
    match_rank,
)

INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
MIN_REQUEST_INTERVAL = 0.25  # seconds; Dhan documents a limit of 5 Data API requests per second
NOT_SUBSTITUTED = "No fixture or synthetic data was substituted."

REQUIRED_COLUMNS = (
    "SEM_EXM_EXCH_ID",
    "SEM_SEGMENT",
    "SEM_SMST_SECURITY_ID",
    "SEM_INSTRUMENT_NAME",
    "SEM_TRADING_SYMBOL",
)

# Names the user taught with (SPEC.md D10) that differ from Dhan's display names.
CURATED_ALIASES = {
    "HCL Technologies": "HCLTECH",
    "Sun Pharma": "SUNPHARMA",
    "Asian Paints": "ASIANPAINT",
    "L&T": "LT",
    "Larsen & Toubro": "LT",
}

_AUTH_CODES = {"DH-901", "807", "808", "809", "810"}
_SUBSCRIPTION_CODES = {"DH-902", "806"}
_RATE_CODES = {"DH-904", "805"}
_INPUT_CODES = {"DH-905", "811", "812", "813", "814"}
_NO_DATA_CODES = {"DH-907"}
_KIND_ORDER = {"stock": 0, "index": 1, "future": 2}
FUTURE_NOTE = "Futures are not scanned: this strategy analyzes NSE cash stocks only."
INDEX_NOTE = "Indices are not scanned. To scan an index, add its stocks (for example the Nifty 50 preset)."


def _company_key(name: str) -> str:
    key = alias_key(name).rstrip(".")
    for suffix in (" limited", " ltd"):
        if key.endswith(suffix):
            return key[: -len(suffix)].rstrip(" .")
    return key


@dataclass(frozen=True)
class DhanInstrument:
    symbol: str
    security_id: str
    display_name: str
    company_name: str
    series: str
    instrument_type: str = ""


@dataclass(frozen=True)
class _SearchEntry:
    suggestion: InstrumentSuggestion
    symbol_key: str
    name_key: str


def _parse_expiry(text: str) -> date | None:
    try:
        return date.fromisoformat((text or "")[:10])
    except ValueError:
        return None


class InstrumentIndex:
    """NSE cash-equity lookup built from Dhan's compact scrip master."""

    def __init__(
        self,
        instruments: dict[str, DhanInstrument],
        keys: dict[str, set[str]],
        ambiguous: dict[str, int],
        search_entries: list[_SearchEntry] | None = None,
    ):
        self._instruments = instruments
        self._keys = keys
        self._ambiguous = ambiguous
        self._search = search_entries or []

    def __len__(self) -> int:
        return len(self._instruments)

    @classmethod
    def from_csv(cls, lines: Iterable[str], today: date | None = None) -> InstrumentIndex:
        reader = csv.DictReader(lines)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ProviderError(
                "Dhan's instrument list format has changed (missing columns: " + ", ".join(missing) + "). "
                + NOT_SUBSTITUTED
            )
        grouped: dict[str, list[DhanInstrument]] = {}
        futures: dict[str, list[InstrumentSuggestion]] = {}
        indices: list[InstrumentSuggestion] = []
        for row in reader:
            kind = (row["SEM_EXM_EXCH_ID"], row["SEM_SEGMENT"], row["SEM_INSTRUMENT_NAME"])
            if kind in (("NSE", "D", "FUTSTK"), ("NSE", "D", "FUTIDX")):
                expiry = _parse_expiry(row.get("SEM_EXPIRY_DATE", ""))
                symbol = row["SEM_TRADING_SYMBOL"].strip()
                if expiry is None or (today is not None and expiry < today) or symbol.count("-") < 2:
                    continue
                underlying = symbol.rsplit("-", 2)[0].upper()
                try:
                    lot = int(float(row.get("SEM_LOT_UNITS") or 0)) or None
                except ValueError:
                    lot = None
                futures.setdefault(underlying, []).append(
                    InstrumentSuggestion(
                        symbol=symbol, name=(row.get("SEM_CUSTOM_SYMBOL") or symbol).strip(), kind="future",
                        underlying=underlying, expiry=expiry, lot_size=lot, scannable=False, note=FUTURE_NOTE,
                    )
                )
                continue
            if kind == ("NSE", "I", "INDEX"):
                symbol = row["SEM_TRADING_SYMBOL"].strip()
                indices.append(
                    InstrumentSuggestion(
                        symbol=symbol, name=(row.get("SEM_CUSTOM_SYMBOL") or symbol).strip(), kind="index",
                        scannable=False, note=INDEX_NOTE,
                    )
                )
                continue
            if kind != ("NSE", "E", "EQUITY"):
                continue
            symbol = row["SEM_TRADING_SYMBOL"].strip().upper()
            if not symbol:
                continue
            grouped.setdefault(symbol, []).append(
                DhanInstrument(
                    symbol=symbol,
                    security_id=row["SEM_SMST_SECURITY_ID"].strip(),
                    display_name=(row.get("SEM_CUSTOM_SYMBOL") or "").strip(),
                    company_name=(row.get("SM_SYMBOL_NAME") or "").strip(),
                    series=(row.get("SEM_SERIES") or "").strip().upper(),
                    instrument_type=(row.get("SEM_EXCH_INSTRUMENT_TYPE") or "").strip().upper(),
                )
            )
        instruments: dict[str, DhanInstrument] = {}
        ambiguous: dict[str, int] = {}
        for symbol, rows in grouped.items():
            if len(rows) > 1:
                rows = [r for r in rows if r.series == "EQ"] or rows
            if len(rows) == 1:
                instruments[symbol] = rows[0]
            else:
                ambiguous[symbol] = len(rows)
        keys: dict[str, set[str]] = {}

        def add(name: str, symbol: str) -> None:
            if name:
                keys.setdefault(alias_key(name), set()).add(symbol)
                keys.setdefault(_company_key(name), set()).add(symbol)

        for symbol, item in instruments.items():
            add(symbol, symbol)
            add(item.display_name, symbol)
            add(item.company_name, symbol)
        for alias, symbol in CURATED_ALIASES.items():
            if symbol in instruments:
                keys[alias_key(alias)] = {symbol}

        entries: list[_SearchEntry] = []
        for symbol, item in instruments.items():
            if item.instrument_type and item.instrument_type != "ES":
                continue  # bonds, ETFs and other cash instruments stay resolvable but are not suggested
            name = item.display_name or item.company_name or symbol
            entries.append(_SearchEntry(
                InstrumentSuggestion(symbol=symbol, name=name, kind="stock", scannable=True),
                symbol, f"{name} {item.company_name}",
            ))
        for underlying, contracts in futures.items():
            stock_name = instruments[underlying].display_name if underlying in instruments else ""
            for contract in sorted(contracts, key=lambda c: c.expiry or date.max)[:3]:
                entries.append(_SearchEntry(contract, underlying, f"{stock_name} {contract.name}"))
        for index in indices:
            entries.append(_SearchEntry(index, index.symbol, index.name))
        return cls(instruments, keys, ambiguous, entries)

    def search(self, query: str, limit: int = 12) -> list[InstrumentSuggestion]:
        # Exact symbol, display name, company name, or taught alias ("L&T", "Sun Pharma") ranks first.
        exact = self._keys.get(alias_key(query)) or self._keys.get(_company_key(query)) or set()
        ranked = []
        for entry in self._search:
            s = entry.suggestion
            if (s.underlying or s.symbol) in exact and s.kind != "index":
                rank = -1
            else:
                rank = match_rank(query, entry.symbol_key, entry.name_key)
            if rank is not None:
                ranked.append((rank, len(entry.symbol_key), _KIND_ORDER[s.kind], s.expiry or date.min, s.symbol, s))
        ranked.sort(key=lambda item: item[:5])
        return [item[5] for item in ranked[:limit]]

    def resolve(self, name: str) -> DhanInstrument:
        symbol_guess = name.strip().upper()
        if symbol_guess in self._ambiguous:
            raise SymbolResolutionError(
                f"'{name}' matches {self._ambiguous[symbol_guess]} NSE equity listings in Dhan's instrument list; "
                "it cannot be resolved to one cash stock."
            )
        if symbol_guess in self._instruments:
            return self._instruments[symbol_guess]
        matches = self._keys.get(alias_key(name)) or self._keys.get(_company_key(name)) or set()
        if not matches:
            raise SymbolResolutionError(
                f"'{name}' did not match any NSE cash-equity symbol or company name in Dhan's instrument list. "
                "Use the NSE symbol, for example HCLTECH."
            )
        if len(matches) > 1:
            raise SymbolResolutionError(
                f"'{name}' is ambiguous; it matches {', '.join(sorted(matches))}. Use the exact NSE symbol."
            )
        return self._instruments[next(iter(matches))]


def _error_details(response: httpx.Response, payload: Any) -> tuple[str, str]:
    """Extract (code, message) from Dhan's error shapes."""
    code = message = ""
    if isinstance(payload, dict):
        code = str(payload.get("errorCode") or "")
        message = str(payload.get("errorMessage") or payload.get("message") or "")
        remarks = payload.get("remarks")
        if isinstance(remarks, dict):
            code = code or str(remarks.get("error_code") or "")
            message = message or str(remarks.get("error_message") or "")
        data = payload.get("data")
        if not code and isinstance(data, dict) and len(data) == 1:
            key, value = next(iter(data.items()))
            if str(key).isdigit():
                code, message = str(key), str(value)
    return code, message


class DhanProvider(CandleProvider):
    name = "dhan"

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] = ist_now,
        sleep: Callable[[float], None] = time_module.sleep,
        monotonic: Callable[[], float] = time_module.monotonic,
    ) -> None:
        self._configured = settings.dhan_configured
        self._client_id = settings.dhan_client_id.get_secret_value() if settings.dhan_client_id else ""
        self._token = settings.dhan_access_token.get_secret_value() if settings.dhan_access_token else ""
        self._data_dir = settings.resolved_data_dir / "dhan"
        self._client = client
        self._clock = clock
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request: float | None = None
        self._index: InstrumentIndex | None = None

    # ------------------------------------------------------------------ plumbing

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30)
        return self._client

    def _require_configured(self) -> None:
        if not self._configured:
            raise ProviderError(
                "Dhan provider is not configured: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are not set in .env. "
                + NOT_SUBSTITUTED
            )

    def _sanitize(self, text: str) -> str:
        text = " ".join(str(text).split())[:200]
        for secret in (self._token, self._client_id):
            if secret:
                text = text.replace(secret, "***")
        return text

    def _throttle(self) -> None:
        now = self._monotonic()
        if self._last_request is not None:
            wait = MIN_REQUEST_INTERVAL - (now - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._monotonic()

    # -------------------------------------------------------------- instruments

    def _ensure_master(self) -> Path:
        today = self._clock().astimezone(IST).date()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._data_dir / f"api-scrip-master-{today.isoformat()}.csv"
        if path.exists():
            return path
        partial = path.with_suffix(".part")
        try:
            with self._http().stream("GET", SCRIP_MASTER_URL, timeout=120) as response:
                if response.status_code != 200:
                    raise ProviderError(
                        f"Could not download Dhan's instrument list (HTTP {response.status_code}). " + NOT_SUBSTITUTED
                    )
                with partial.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        except httpx.HTTPError as exc:
            partial.unlink(missing_ok=True)
            raise ProviderError(
                f"Could not download Dhan's instrument list ({type(exc).__name__}). " + NOT_SUBSTITUTED
            ) from exc
        partial.replace(path)
        for old in self._data_dir.glob("api-scrip-master-*.csv"):
            if old != path:
                old.unlink(missing_ok=True)
        return path

    def _instruments(self) -> InstrumentIndex:
        if self._index is None:
            today = self._clock().astimezone(IST).date()
            with self._ensure_master().open(newline="", encoding="utf-8") as handle:
                self._index = InstrumentIndex.from_csv(handle, today=today)
        return self._index

    def search(self, query: str, limit: int = 12) -> list[InstrumentSuggestion]:
        """Suggestions from Dhan's public instrument list (no credentials needed)."""
        return self._instruments().search(query, limit)

    def resolve(self, stock_name: str) -> Instrument:
        self._require_configured()
        item = self._instruments().resolve(stock_name)
        return Instrument(
            symbol=item.symbol,
            name=item.display_name or item.company_name or item.symbol,
            provider_id=item.security_id,
        )

    # ------------------------------------------------------------------ candles

    def _error_from(self, response: httpx.Response, payload: Any = None) -> ProviderError:
        if payload is None:
            try:
                payload = response.json()
            except ValueError:
                payload = None
        code, message = _error_details(response, payload)
        detail = self._sanitize(f"{code}: {message}" if code and message else code or message)
        status = response.status_code
        if status in (401, 403) or code in _AUTH_CODES:
            text = (
                "Dhan rejected the credentials (invalid or expired access token, or wrong client ID). "
                "Generate a new access token, update DHAN_ACCESS_TOKEN in .env, and restart."
            )
        elif code in _SUBSCRIPTION_CODES:
            text = "Dhan reports that this account has no Data API subscription."
        elif status == 429 or code in _RATE_CODES:
            text = "Dhan's rate limit was reached; wait a few seconds and scan again."
        elif code in _INPUT_CODES:
            text = f"Dhan rejected the request parameters ({detail})."
        elif code in _NO_DATA_CODES:
            text = f"Dhan has no data for this request ({detail})."
        else:
            text = f"Dhan request failed (HTTP {status}" + (f", {detail}" if detail else "") + ")."
        if detail and detail not in text:
            text += f" Dhan said: {detail}."
        return ProviderError(f"{text} {NOT_SUBSTITUTED}")

    def fetch_candles(self, instrument: Instrument, trading_date: date) -> ProviderCandles:
        self._require_configured()
        if not instrument.provider_id:
            raise ProviderError(f"{instrument.symbol} has no Dhan security ID. " + NOT_SUBSTITUTED)
        body = {
            "securityId": instrument.provider_id,
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": 5,
            "oi": False,
            "fromDate": f"{trading_date.isoformat()} 09:00:00",
            "toDate": f"{(trading_date + timedelta(days=1)).isoformat()} 00:00:00",
        }
        headers = {
            "access-token": self._token,
            "client-id": self._client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._throttle()
        try:
            response = self._http().post(INTRADAY_URL, json=body, headers=headers, timeout=30)
        except httpx.TimeoutException as exc:
            raise ProviderError("Dhan did not respond in time; scan again. " + NOT_SUBSTITUTED) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Could not reach Dhan ({type(exc).__name__}); check the internet connection. " + NOT_SUBSTITUTED
            ) from exc
        retrieved_at = self._clock().astimezone(IST)
        if response.status_code != 200:
            raise self._error_from(response)
        try:
            payload = json.loads(response.text, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise ProviderError("Dhan returned a response that is not JSON. " + NOT_SUBSTITUTED) from exc
        if not isinstance(payload, dict) or "errorCode" in payload or payload.get("status") in ("failure", "failed"):
            raise self._error_from(response, payload)

        candles, notes = self._candles(payload, trading_date, retrieved_at)
        return ProviderCandles(
            instrument=instrument,
            trading_date=trading_date,
            candles=tuple(candles),
            as_of=retrieved_at,
            source="dhan:/v2/charts/intraday",
            synthetic=False,
            data_label="Dhan Data API: 5-minute NSE cash-equity candles (provider data).",
            provenance={
                "endpoint": "POST /v2/charts/intraday",
                "security_id": instrument.provider_id,
                "exchange_segment": "NSE_EQ",
                "interval_minutes": "5",
                "retrieved_at": retrieved_at.isoformat(),
            },
            notes=tuple(notes),
        )

    def _candles(
        self, payload: dict[str, Any], trading_date: date, retrieved_at: datetime
    ) -> tuple[list[RawCandle], list[str]]:
        fields = ("open", "high", "low", "close", "timestamp")
        arrays = {name: payload.get(name) for name in (*fields, "volume")}
        if any(not isinstance(arrays[name], list) for name in fields):
            raise ProviderError("Dhan's response is missing candle arrays. " + NOT_SUBSTITUTED)
        volumes = arrays["volume"] if isinstance(arrays["volume"], list) else None
        lengths = {len(arrays[name]) for name in fields} | ({len(volumes)} if volumes is not None else set())
        if len(lengths) != 1:
            raise ProviderError("Dhan's candle arrays have unequal lengths; none were used. " + NOT_SUBSTITUTED)

        count = len(arrays["timestamp"])
        if count == 0:
            if trading_date == retrieved_at.date() and retrieved_at < session_close(trading_date):
                return [], ["Dhan has returned no candles for today's session yet."]
            raise NoSessionError(
                f"Dhan returned no candles for {trading_date.isoformat()} "
                "(weekend, market holiday, or no data available)."
            )

        starts: list[int] = []
        for raw in arrays["timestamp"]:
            try:
                value = Decimal(str(raw))
                if value != value.to_integral_value():
                    raise ValueError
                starts.append(int(value))
                datetime.fromtimestamp(starts[-1], UTC)
            except (ArithmeticError, ValueError, OverflowError, OSError) as exc:
                raise ProviderError(
                    "Dhan's timestamps are not whole epoch seconds; the contract may have changed. " + NOT_SUBSTITUTED
                ) from exc

        labels = [datetime.fromtimestamp(s, UTC).astimezone(IST) for s in starts]
        on_date = [label for label in labels if label.date() == trading_date]
        aligned = [
            label for label in on_date
            if SESSION_OPEN <= label.time().replace(tzinfo=None) <= LAST_CANDLE
            and label.minute % 5 == 0 and label.second == 0
        ]
        if not on_date or len(aligned) < 0.9 * len(on_date):
            raise ProviderError(
                "Dhan's candle timestamps do not line up with the 09:15-15:25 five-minute NSE session, so the "
                "candle-labeling convention may have changed. " + NOT_SUBSTITUTED
            )
        on_date_times = {label.time().replace(tzinfo=None) for label in on_date}
        if time(15, 30) in on_date_times and SESSION_OPEN not in on_date_times:
            raise ProviderError(
                "Dhan's candles appear to be labeled by end time; they must be labeled by start time. "
                + NOT_SUBSTITUTED
            )

        candles = [
            RawCandle(
                starts[i],
                arrays["open"][i],
                arrays["high"][i],
                arrays["low"][i],
                arrays["close"][i],
                volumes[i] if volumes is not None else None,
            )
            for i in range(count)
        ]
        notes: list[str] = []
        last = max(label for label in on_date).time().replace(tzinfo=None)
        if retrieved_at >= session_close(trading_date) and last < LAST_CANDLE:
            notes.append(
                f"Dhan's intraday data ended with the {hhmm(last)} candle; later session candles through 15:25 "
                "were not provided and are not filled in."
            )
        return candles, notes
