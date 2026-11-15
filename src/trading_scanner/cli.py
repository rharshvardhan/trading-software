"""Terminal runner (SPEC.md section 7, D11). A thin interface over ``ScanService``.

Interactive:   python -m trading_scanner.cli --provider fixture
One scan:      python -m trading_scanner.cli --provider fixture --date 2026-11-13 --stocks HCLTECH LT SYN-LONG
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import TextIO

from pydantic import ValidationError

from trading_scanner import STRATEGY_VERSION
from trading_scanner.formatting import format_inr, format_price
from trading_scanner.market import hhmm
from trading_scanner.models import (
    RISK_RULES_REASON,
    ProviderName,
    ResultState,
    ScanRequest,
    ScanResponse,
    StockResult,
    parse_trading_date,
)
from trading_scanner.providers import PROVIDER_NAMES, FixtureFormatError, FixtureProvider
from trading_scanner.service import InputError, ScanService

SIGNAL_STATES = {
    ResultState.ENTRY_IDENTIFIED,
    ResultState.AWAITING_ENTRY,
    ResultState.ENTRY_UNAVAILABLE_SESSION_END,
}
PROVIDER_BANNERS = {
    "fixture": (
        "Fixture provider: recorded offline files only (never live market data). SYN- instruments are SYNTHETIC; "
        "HCLTECH, SUNPHARMA, ASIANPAINT and LT hold partial chart observations only."
    ),
    "dhan": "Dhan provider: integration pending; no fixture or synthetic data will be substituted.",
}


def split_stocks(values: list[str]) -> list[str]:
    """Split entries on commas; each token may itself be a multi-word name."""
    names: list[str] = []
    for value in values:
        names.extend(part.strip() for part in value.split(","))
    return [name for name in names if name]


def _validation_text(error: ValidationError) -> str:
    parts = []
    for item in error.errors():
        field = ".".join(str(p) for p in item.get("loc", ()))
        message = str(item.get("msg", "invalid value")).removeprefix("Value error, ")
        parts.append(f"{field}: {message}" if field else message)
    return "; ".join(parts)


# ----------------------------------------------------------------- rendering


def _setup_label(result: StockResult) -> str:
    if result.setup_qualified is True:
        return "Qualified"
    if result.setup_qualified is False:
        return "Not qualified"
    if result.state is ResultState.NEEDS_RULE_DECISION:
        return "Rule decision"
    return "Unknown"


def _row(result: StockResult) -> list[str]:
    symbol = result.instrument.symbol if result.instrument else result.input_name
    signal = breakout = entry_time = entry_price = "—"
    if result.state in SIGNAL_STATES and result.breakout is not None:
        signal = result.breakout.signal.value.capitalize()
    if result.breakout is not None:
        breakout = hhmm(result.breakout.candle_start)
    if result.entry is not None:
        if result.entry.time is not None:
            entry_time = hhmm(result.entry.time)
        elif result.entry.expected_time is not None:
            status = "pending" if result.state is ResultState.AWAITING_ENTRY else "missing"
            entry_time = f"{hhmm(result.entry.expected_time)} {status}"
        else:
            entry_time = "none"
        entry_price = format_inr(result.entry.price)
    return [symbol, result.state.value, _setup_label(result), signal, breakout, entry_time, entry_price,
            "Not defined", "Not defined"]


def render_table(results: list[StockResult]) -> str:
    header = ["Stock", "State", "Setup", "Signal", "Breakout", "Entry", "Entry open", "Stop loss", "Exit"]
    rows = [_row(r) for r in results]
    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    right = {6}

    def line(cells: list[str]) -> str:
        return "  ".join(c.rjust(w) if i in right else c.ljust(w) for i, (c, w) in enumerate(zip(cells, widths)))

    out = [line(header), line(["-" * w for w in widths])]
    out.extend(line(row) for row in rows)
    return "\n".join(line_.rstrip() for line_ in out)


def _candle_text(c) -> str:
    return (
        f"{hhmm(c.start)}  O {format_price(c.open)}  H {format_price(c.high)}  "
        f"L {format_price(c.low)}  C {format_price(c.close)}"
    )


def _details(result: StockResult) -> list[str]:
    lines: list[str] = []
    q = result.qualification
    if q is not None:
        lines.append(
            f"Qualification ({q.window}): {q.decision.value}; session high {format_price(q.session_high)} "
            f"({', '.join(q.session_high_candles)}), session low {format_price(q.session_low)} "
            f"({', '.join(q.session_low_candles)})"
        )
        for name, side in (("High", q.high_side), ("Low", q.low_side)):
            lines.append(
                f"  {name} side: {side.status.value}; reference {format_price(side.reference_value)} "
                f"({', '.join(side.reference_candles)}) vs earlier {format_price(side.earlier_value)} "
                f"({', '.join(side.earlier_candles)})"
            )
    if result.reference is not None:
        lines.append("Reference candles:")
        lines.extend(f"  {_candle_text(c)}" for c in result.reference.candles)
        lines.append(
            f"Reference range: {format_price(result.reference.low)} to {format_price(result.reference.high)}"
        )
    if result.breakout is not None:
        b = result.breakout
        lines.append(
            f"Breakout candle: {hhmm(b.candle_start)}-{hhmm(b.candle_end)}, close {format_price(b.close)} "
            f"{b.side.value} {format_price(b.boundary_value)}, confirmed {hhmm(b.confirmed_at)}"
            + ("; lies entirely beyond the range" if b.entirely_beyond_range else "")
        )
    if result.entry is not None:
        e = result.entry
        if e.available and e.time is not None:
            lines.append(f"Entry: {e.signal.value} at {hhmm(e.time)} open {format_inr(e.price)} ({e.price_basis})")
        elif e.expected_time is not None:
            lines.append(f"Entry: {e.signal.value}; expected at the {hhmm(e.expected_time)} open, not available yet")
        else:
            lines.append(f"Entry: {e.signal.value}; unavailable (no same-session candle follows)")
    if result.data is not None:
        d = result.data
        lines.append(
            f"Source: {d.source}; as of {d.as_of.strftime('%Y-%m-%d %H:%M %Z')}; session complete "
            f"{'yes' if d.session_complete else 'no'}; last closed candle {d.last_closed_candle or 'none'}; "
            f"{d.candles_received} received, {d.candles_in_session} in session"
        )
    return lines


def render_report(response: ScanResponse, details: bool = False) -> str:
    out = [
        f"Scan {response.trading_date.isoformat()} | provider {response.provider} | {response.timezone} "
        f"{response.interval} candles | strategy {response.strategy_version} | scanned "
        f"{response.scanned_at.strftime('%Y-%m-%d %H:%M %Z')}",
    ]
    synthetic = [r.instrument.symbol for r in response.results if r.instrument and r.instrument.synthetic]
    if synthetic:
        out.append(
            f"*** SYNTHETIC DATA: {', '.join(synthetic)} use invented prices for offline testing; not market data. ***"
        )
    out += ["", render_table(response.results), "", "Explanations"]
    for index, result in enumerate(response.results, start=1):
        title = result.instrument.symbol if result.instrument else result.input_name
        inputs = ", ".join(f'"{n}"' for n in result.input_names)
        tag = " [SYNTHETIC]" if result.data is not None and result.data.synthetic else ""
        out.append(f"{index}. {title} (input {inputs}): {result.state.value}{tag}")
        out.append(f"   {result.reason}")
        if result.rule_decision is not None:
            out.append(f"   Open rule question: {result.rule_decision.question}")
        if result.data is not None and not result.data.synthetic:
            out.append(f"   Data: {result.data.data_label}")
        for note in result.notes:
            out.append(f"   Note: {note}")
        if details:
            out.extend(f"   {line}" for line in _details(result))
            for note in result.data.notes if result.data else []:
                out.append(f"   Data note: {note}")
    out += ["", f"Stop loss, target, exit, and outcome: {RISK_RULES_REASON}. Entry prices are reference opens, "
            "not order fills; no orders are placed."]
    return "\n".join(out)


# ----------------------------------------------------------------- workflow


def _scan(service: ScanService, date_text: str, stocks: list[str], provider: ProviderName) -> ScanResponse:
    request = ScanRequest(trading_date=date_text, stocks=stocks, provider=provider)
    return service.scan(request)


def _emit(response: ScanResponse, args: argparse.Namespace, out: TextIO) -> None:
    if args.as_json:
        out.write(response.model_dump_json(indent=2) + "\n")
    else:
        out.write(render_report(response, details=args.details) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m trading_scanner.cli",
        description=f"Four Candle Reversal Scanner (setup and entry, strategy {STRATEGY_VERSION}).",
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=PROVIDER_NAMES,
        help="data provider, always explicit: 'fixture' (recorded offline files) or 'dhan' (integration pending)",
    )
    parser.add_argument("--date", help="trading date YYYY-MM-DD; with --stocks, runs one scan and exits")
    parser.add_argument(
        "--stocks",
        nargs="+",
        metavar="STOCK",
        help="stock names or symbols; separate with spaces or commas and quote multi-word names",
    )
    parser.add_argument("--details", action="store_true", help="show reference candles and qualification evidence")
    parser.add_argument("--json", dest="as_json", action="store_true", help="print the same JSON as POST /v1/scans")
    parser.add_argument("--list-fixtures", action="store_true", help="list the fixture recordings and exit")
    return parser


def _list_fixtures(service: ScanService, out: TextIO) -> int:
    provider = service.provider("fixture")
    assert isinstance(provider, FixtureProvider)
    out.write(f"Fixture recordings in {provider.fixture_dir}:\n")
    for symbol, day, kind in provider.recordings():
        out.write(f"  {symbol:16} {day.isoformat()}  {kind}\n")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    service: ScanService | None = None,
    input_fn: Callable[[str], str] = input,
    out: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    service = service or ScanService()
    provider: ProviderName = args.provider

    if (args.date is None) != (args.stocks is None):
        parser.error("--date and --stocks must be used together for a single scan")

    try:
        if args.list_fixtures:
            if provider != "fixture":
                parser.error("--list-fixtures requires --provider fixture")
            return _list_fixtures(service, out)
        service.provider(provider)
    except FixtureFormatError as exc:
        out.write(f"Fixture data could not be loaded: {exc}\n")
        return 1

    if args.date is not None:
        stocks = split_stocks(args.stocks)
        try:
            _emit(_scan(service, args.date, stocks, provider), args, out)
        except ValidationError as exc:
            out.write(f"Invalid request: {_validation_text(exc)}\n")
            return 1
        except InputError as exc:
            out.write(f"Invalid request: {exc.message}\n")
            return 1
        except Exception as exc:  # never show a raw traceback
            out.write(f"Scan failed unexpectedly ({type(exc).__name__}): {exc}\n")
            return 1
        return 0

    return _interactive(service, provider, args, input_fn, out)


def _interactive(
    service: ScanService,
    provider: ProviderName,
    args: argparse.Namespace,
    input_fn: Callable[[str], str],
    out: TextIO,
) -> int:
    out.write(f"Four Candle Reversal Scanner (strategy {STRATEGY_VERSION}), provider: {provider}\n")
    out.write(PROVIDER_BANNERS[provider] + "\n")
    out.write("Enter a trading date and comma-separated stocks; press Enter to scan. Blank date or q quits.\n")
    try:
        while True:
            out.write("\n")
            out.flush()
            date_text = input_fn("Trading date [YYYY-MM-DD]: ").strip()
            if date_text.lower() in ("", "q", "quit", "exit"):
                break
            try:
                service.validate_trading_date(parse_trading_date(date_text))
            except ValueError as exc:
                if isinstance(exc, InputError):
                    out.write(exc.message + "\n")
                else:
                    out.write(f"'{date_text}' is not a valid date; use YYYY-MM-DD, for example 2026-11-13.\n")
                continue
            stocks: list[str] = []
            while not stocks:
                stocks = split_stocks([input_fn("Stocks [comma separated]: ")])
                if not stocks:
                    out.write("Enter at least one stock name or symbol.\n")
            try:
                response = _scan(service, date_text, stocks, provider)
            except ValidationError as exc:
                out.write(f"Invalid request: {_validation_text(exc)}\n")
                continue
            except InputError as exc:
                out.write(exc.message + "\n")
                continue
            except Exception as exc:  # keep the session alive; never show a raw traceback
                out.write(f"Scan failed unexpectedly ({type(exc).__name__}): {exc}\n")
                continue
            out.write("\n")
            _emit(response, args, out)
    except (EOFError, KeyboardInterrupt):
        out.write("\n")
    out.write("Goodbye.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
