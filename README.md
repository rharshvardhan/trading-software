# Four Candle Reversal Scanner

A Python backend with a terminal interface, a FastAPI interface, and a bare-minimum React and Tailwind web page. It checks stocks against the user's four candle reversal strategy using Dhan Data API candles, and reports setup qualification, the breakout, and the next-candle entry reference price. It does not place orders.

**Current stage:** setup and entry are implemented to [SPEC.md](SPEC.md) version 0.2.0, which the user approved on 15 November 2026. The Dhan integration and web UI follow the user's later request (SPEC.md section 13). Stop-loss, target, and exit rules have not been supplied, so those fields stay `null`.

## Quick start

Requires Python 3.12 or newer. On this machine, `python3` is 3.9, so use `python3.12`.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock      # exact locked versions
python -m pip install -e . --no-deps            # this project
```

Dhan credentials go in `.env` (copy `.env.example`, fill in `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN`). Dhan access tokens expire, so paste in a new one when Dhan rejects the old one, and restart the server.

**Web UI and backend together** (needs [pnpm](https://pnpm.io)). From the project root:

```sh
pnpm ui:install     # first time only
pnpm dev            # starts FastAPI on :8000 and the UI on :5173
```

Open http://localhost:5173. Type a stock name or symbol to get suggestions labeled Stock, Future, or Index. Only stocks can be added; "+ Nifty 50 stocks" adds all 50 constituents. After a scan, the tiles summarize the outcomes and filter the table, and clicking a row shows the four-step reasoning and a candle chart with the range, breakout, and entry. Ctrl+C stops both. The backend reloads when Python code changes; restart `pnpm dev` after editing `.env`.

To run without the dev server, build the UI once with `pnpm build`. Then `python -m uvicorn trading_scanner.api:app --host 127.0.0.1 --port 8000` serves the UI and the API at http://127.0.0.1:8000.

Interactive terminal scanner. Enter a date, enter stocks separated by commas, then press Enter to scan:

```sh
python -m trading_scanner.cli --provider dhan      # or --provider fixture for offline test data
```

Single scan, optionally with `--details` or `--json`:

```sh
python -m trading_scanner.cli --provider fixture --date 2026-11-13 --stocks SYN-LONG SYN-DELAYED "HCL Technologies" L&T
```

HTTP API, served by the same server as the web UI and bound to the local machine only:

```sh
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/v1/scans -H 'content-type: application/json' \
  -d '{"trading_date": "2026-11-13", "stocks": ["SYN-LONG", "LT"], "provider": "fixture"}'
```

Interactive API documentation is at `http://127.0.0.1:8000/docs` while the server runs.

To run the tests:

```sh
python -m pytest
```

## Data providers

You must name a provider every time. There is no default and no fallback.

| Provider | What it serves |
|---|---|
| `fixture` | Recorded offline files in `src/trading_scanner/fixture_data/`. `SYN-` instruments contain **synthetic** prices, invented for demonstrations and tests. `HCLTECH`, `SUNPHARMA`, `ASIANPAINT`, and `LT` contain only the **partial chart readings** from the teaching session, so a full scan of them reports `invalid_data` and lists the candles that were never recorded. |
| `dhan` | Live 5-minute NSE cash-equity candles from Dhan's Data API, for today or past dates. Any NSE symbol or company name resolves through Dhan's instrument list. If Dhan fails, the stock reports `provider_error`, and fixture data is never substituted. |

Run `python -m trading_scanner.cli --provider fixture --list-fixtures` to list every recording. The synthetic scenarios cover a long breakout, a short breakout, a delayed breakout with wick-only and boundary closes, a setup that does not qualify, an equal-extreme tie, a gap, no breakout, a breakout on the last candle, missing data, and in-session snapshots. All of them are dated 2026-11-13.

## Strategy summary

- Five-minute candles in Asia/Kolkata, each labeled by its start time.
- **Qualification:** at least one of the 10:30, 10:35, 10:40, or 10:45 candles must hold the session high or session low measured from 09:15 through 10:45. If a reference candle only equals an earlier extreme, the result is `needs_rule_decision`.
- **Range:** the highest high and lowest low of the whole four-candle group, fixed once set.
- **Breakout:** the first later candle that **closes** strictly outside the range, at any time of day. Wick-only crossings and closes exactly on a boundary do not count. If that candle lies entirely beyond the range, the result is `needs_rule_decision`, because the gap policy is open.
- **Entry:** the open of the immediately following candle. A close above the range is a long signal; a close below is a short signal. Only the first signal is reported.

See [SPEC.md](SPEC.md) for the full contract, including result states, coverage rules, and decisions D01 to D14. See [docs/EXAMPLES.md](docs/EXAMPLES.md) for the teaching examples and acceptance cases, and [docs/PROJECT_SETUP.md](docs/PROJECT_SETUP.md) for the layout and dependency workflow.

## Remaining limitations

- Dhan's intraday data ends with the 15:10 candle. Missing 15:15-15:25 candles are not invented, so "no breakout all day" and 15:10 breakouts show `invalid_data` until the user decides how to treat that cut-off (SPEC.md U5).
- The teaching charts and Dhan differ by up to 0.90 on some values; every decision is the same (EXAMPLES.md section 7).
- Each scan is a single check. There is no continuous live monitoring or alerting.
- Stop loss, targets, exits, outcomes, and profit or loss wait for the user's rules.
- Open rules (equal repeated extremes, gaps beyond the range, re-entry) are reported as `needs_rule_decision`, or only the first signal is reported. They are never resolved with a default.
