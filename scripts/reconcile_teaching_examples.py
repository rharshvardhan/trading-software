"""Compare the teaching-session chart readings with Dhan's candles (EXAMPLES.md section 6).

Requires DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env. Makes one Dhan request per example
and prints, for every recorded chart value, the matching Dhan value. Nothing is written.

    python scripts/reconcile_teaching_examples.py
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal

from trading_scanner.config import PACKAGED_FIXTURE_DIR, Settings
from trading_scanner.market import hhmm
from trading_scanner.normalize import normalize_candles
from trading_scanner.providers import ProviderError, SymbolResolutionError
from trading_scanner.providers.dhan import DhanProvider
from trading_scanner.providers.fixture import FixtureFile

FILES = ["hcltech-2026-11-13.json", "sunpharma-2026-11-13.json", "asianpaint-2026-11-06.json", "lt-2026-11-13.json"]
FIELDS = ("open", "high", "low", "close")


def main() -> int:
    settings = Settings()
    if not settings.dhan_configured:
        print("Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env first.")
        return 1
    provider = DhanProvider(settings)
    mismatches = 0
    for name in FILES:
        fixture = FixtureFile.model_validate(json.loads((PACKAGED_FIXTURE_DIR / "observations" / name).read_text()))
        try:
            instrument = provider.resolve(fixture.instrument.symbol)
            response = provider.fetch_candles(instrument, fixture.trading_date)
        except (ProviderError, SymbolResolutionError) as exc:
            print(f"{fixture.instrument.symbol}: {exc}")
            return 1
        session = normalize_candles(response.candles, fixture.trading_date, response.as_of).session
        dhan = {hhmm(slot): candle for slot, candle in session.candles.items()}
        print(f"\n{instrument.symbol} {fixture.trading_date} (Dhan security {instrument.provider_id})")
        readings = [(row[0][11:16], dict(zip(FIELDS, row[1:5]))) for row in fixture.candles]
        readings += [
            (r["candle"], {k: r[k] for k in ("high", "low") if k in r}) for r in fixture.partial_readings if "candle" in r
            and any(k in r for k in ("high", "low")) and "observation" not in r
        ]
        for label, values in readings:
            candle = dhan.get(label)
            for field, chart_value in values.items():
                dhan_value = getattr(candle, field) if candle else None
                same = dhan_value is not None and Decimal(str(chart_value)) == dhan_value
                mismatches += not same
                print(f"  {label} {field:5}  chart {chart_value:>9}  dhan {str(dhan_value):>9}  {'same' if same else 'DIFFERENT'}")
    print(f"\n{mismatches} recorded chart value(s) differ from Dhan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
