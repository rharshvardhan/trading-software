"""The normalized candle provider boundary (SPEC.md sections 5 and 6).

The strategy never sees provider request details or response shapes. A provider
resolves names to cash-equity instruments and returns raw candles plus provenance;
``normalize.py`` validates them identically for every provider.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date

from trading_scanner.models import Instrument, InstrumentSuggestion, ProviderCandles


def alias_key(name: str) -> str:
    """Case-insensitive, whitespace-tolerant lookup key ("l & t" and "L&T" match)."""
    key = " ".join(name.split()).casefold()
    return re.sub(r"\s*&\s*", "&", key)


def match_rank(query: str, symbol: str, name: str) -> int | None:
    """Lower is better: exact symbol, symbol prefix, name prefix, word prefix, substring."""
    q, s, n = alias_key(query), alias_key(symbol), alias_key(name)
    if not q:
        return None
    if s == q:
        return 0
    if s.startswith(q):
        return 1
    if n.startswith(q):
        return 2
    if any(word.startswith(q) for word in n.split()):
        return 3
    if q in s or q in n:
        return 4
    return None


class ProviderError(Exception):
    """Candle retrieval failed. The message must be sanitized and actionable (no secrets)."""


class SymbolResolutionError(Exception):
    """A stock name is unknown or ambiguous for this provider."""


class NoSessionError(Exception):
    """The provider affirmatively reports no trading session on the requested date."""


class CandleProvider(ABC):
    """Interface implemented by the fixture provider and the future Dhan adapter."""

    name: str

    @abstractmethod
    def resolve(self, stock_name: str) -> Instrument:
        """Resolve a user-supplied name to one NSE cash-equity instrument.

        Raises ``SymbolResolutionError`` for unknown or ambiguous names and
        ``ProviderError`` when the provider itself is unavailable.
        """

    def search(self, query: str, limit: int = 12) -> list[InstrumentSuggestion]:
        """Name or symbol suggestions, labeled stock, future, or index. Optional for providers."""
        return []

    @abstractmethod
    def fetch_candles(self, instrument: Instrument, trading_date: date) -> ProviderCandles:
        """Return five-minute candles for one instrument and date, with an as-of time.

        Raises ``NoSessionError`` or ``ProviderError``. Must never substitute data from
        another provider, date, exchange, or contract.
        """
