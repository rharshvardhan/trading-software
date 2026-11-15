"""Provider registry. Selection is always explicit; there is no default or fallback."""

from __future__ import annotations

from functools import lru_cache

from trading_scanner.config import Settings
from trading_scanner.models import ProviderName
from trading_scanner.providers.base import (
    CandleProvider,
    NoSessionError,
    ProviderError,
    SymbolResolutionError,
)
from trading_scanner.providers.dhan import DhanProvider
from trading_scanner.providers.fixture import FixtureFormatError, FixtureProvider

PROVIDER_NAMES: tuple[ProviderName, ...] = ("fixture", "dhan")


@lru_cache(maxsize=8)
def _fixture_provider(path: str) -> FixtureProvider:
    from pathlib import Path

    return FixtureProvider(Path(path))


def build_provider(name: ProviderName, settings: Settings | None = None) -> CandleProvider:
    """Construct the explicitly requested provider."""
    settings = settings or Settings()
    if name == "fixture":
        return _fixture_provider(str(settings.resolved_fixture_dir))
    if name == "dhan":
        return DhanProvider(settings)
    raise ValueError(f"Unknown provider {name!r}; choose one of {', '.join(PROVIDER_NAMES)}")


__all__ = [
    "PROVIDER_NAMES",
    "CandleProvider",
    "DhanProvider",
    "FixtureFormatError",
    "FixtureProvider",
    "NoSessionError",
    "ProviderError",
    "SymbolResolutionError",
    "build_provider",
]
