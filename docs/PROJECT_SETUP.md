# Python Project Setup

## Current state

The setup-and-entry scope of [SPEC.md](../SPEC.md) version 0.2.0 is implemented, along with the user-requested Dhan adapter and minimal web UI (section 13). The terminal runner, the FastAPI interface, and the web UI all go through one shared service and one strategy engine. Risk and exit rules are a later milestone.

## Technology

| Component | Choice | Locked version |
|---|---|---|
| Runtime | Python 3.12 or newer (`python3.12` here; the default `python3` is 3.9) | 3.12.13 used |
| HTTP backend | FastAPI | 0.163.0 |
| Validation | Pydantic v2 and pydantic-settings | 2.14.3 / 2.16.3 |
| ASGI server | Uvicorn (`[standard]`) | 0.54.0 |
| External HTTP | HTTPX (reserved for the Dhan adapter; also used by the test client) | 0.28.1 |
| Tests | pytest | 9.2.0 |
| Web UI | React, Vite, Tailwind CSS, concurrently; pnpm 11 (`frontend/package.json`, `frontend/pnpm-lock.yaml`) | 19.3.1 / 8.3.8 / 4.3.5 / 10.0.7 |
| Storage | None (Dhan's daily instrument list is cached in the git-ignored `data/`) | |

`requirements.lock` pins every direct and transitive dependency. `pyproject.toml` declares the compatible ranges.

## Environment and dependency workflow

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
```

To change dependencies, edit `pyproject.toml`, then regenerate the lock and reinstall:

```sh
uv pip compile pyproject.toml --extra dev --python-version 3.12 -o requirements.lock
python -m pip install -r requirements.lock
```

## Running

| Purpose | Command |
|---|---|
| Install UI dependencies (first time) | `pnpm ui:install` (from the project root) |
| **Backend and UI together** | `pnpm dev`, then open http://localhost:5173 (Ctrl+C stops both) |
| Build the UI for FastAPI to serve | `pnpm build`, then `python -m uvicorn trading_scanner.api:app --host 127.0.0.1 --port 8000` and open http://127.0.0.1:8000 |
| Interactive terminal scanner | `python -m trading_scanner.cli --provider dhan` (or `fixture`) |
| Single scan | `python -m trading_scanner.cli --provider fixture --date 2026-11-13 --stocks SYN-LONG LT` |
| Detailed or JSON output | add `--details` or `--json` |
| List fixture recordings | `python -m trading_scanner.cli --provider fixture --list-fixtures` |
| Tests | `python -m pytest` |
| Regenerate synthetic fixtures | `python scripts/generate_synthetic_fixtures.py` (`--check` verifies) |
| Compare teaching charts with Dhan | `python scripts/reconcile_teaching_examples.py` (needs `.env` credentials) |

`python -m trading_scanner` and the installed `four-candle-scan` command are shortcuts for the terminal runner. In the interactive runner, a blank date or `q` quits.

## Source layout

```text
src/trading_scanner/
  __init__.py          strategy version
  market.py            NSE session slots (09:15-15:25), Asia/Kolkata helpers
  models.py            Candle, Instrument, ScanRequest, and result models (decimal prices)
  normalize.py         timezone normalization, ordering, duplicates, grid, and as-of checks
  strategy.py          pure engine: qualification, fixed range, first breakout, next-candle entry
  service.py           shared ScanService used by cli.py and api.py
  cli.py               terminal prompts, table, explanations, --details, --json
  api.py               GET /health, POST /v1/scans
  config.py            environment settings (.env is git-ignored)
  formatting.py        Indian-grouped INR display without rounding
  synthetic.py         SYNTHETIC session builder for tests and demo fixtures only
  providers/
    base.py            provider interface and errors
    fixture.py         explicit offline fixture provider
    dhan.py            Dhan Data API adapter: instrument list, intraday candles, safeguards
  fixture_data/
    synthetic/         generated SYN- scenarios
    observations/      partial chart readings from the teaching session
package.json           pnpm entry point: `pnpm dev` / `pnpm build` forward to frontend/
frontend/              bare-minimum React + Tailwind page (src/App.jsx); `dev` runs API + UI via concurrently
scripts/               synthetic fixture generator; chart-vs-Dhan reconciliation
tests/                 acceptance, interface, and mocked-Dhan tests (no real network)
```

The engine has no network, file, terminal, or clock access. Providers return raw candles plus an as-of time. `normalize.py` validates them identically for every provider, and `strategy.py` evaluates them.

## Dhan integration

SPEC.md section 13 records the contract, confirmed with a live response on 15 November 2026. In short:

- Instruments come from Dhan's public compact scrip master, downloaded at most once per day into `data/dhan/`, and filtered to NSE cash equities.
- Candles come from `POST https://api.dhan.co/v2/charts/intraday` with interval 5. Timestamps are epoch seconds marking candle starts.
- Credentials are read from `.env`. Tokens expire: update `DHAN_ACCESS_TOKEN` and restart the server.
- Data API requests are spaced at least 0.25 s apart.
- Dhan's intraday data ends with the 15:10 candle; see SPEC.md U5.

## Remaining milestones

1. Stop loss, targets, exits, and outcomes, after the user supplies and approves those rules.
2. Decisions on the open rules: equal repeated extremes, gaps, re-entry, and the Dhan 15:10 cut-off (U5).
