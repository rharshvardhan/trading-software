# Four Candle Reversal Scanner Specification

**Version:** 0.2.0 (adds section 12, proposed implementation decisions; trading rules R01 to R10 unchanged from 0.1.0)  
**Date:** 15 November 2026  
**Status:** Approved by the user for the setup-and-entry implementation scope (15 November 2026)  
**Strategy source:** The user's explanations and confirmations in this chat, including the confirmed HCL Technologies entry example.  
**Implementation authorization:** Given by the user on 15 November 2026 for setup and entry only. See section 11.

## 1 Purpose and delivery stages

The scanner will accept stock names or symbols and a trading date, evaluate the user's four candle reversal conditions against candle data, and report which stocks qualify and the corresponding entry details. It will use Python, expose a FastAPI backend, and support direct terminal interaction without a custom frontend.

The user will supply Dhan API details later. Stop-loss and exit conditions will also be taught later. Those missing rules do not change the setup and entry conditions already confirmed.

| Stage | Deliverable | Current authorization |
|---|---|---|
| Specification and foundation | This specification, example cases, setup plan, metadata, blank configuration, and empty source and test folders | Authorized now |
| Setup and entry implementation | Shared strategy engine, terminal runner, FastAPI interface, and meaningful acceptance tests using candle fixtures | Only after explicit user approval of this spec |
| Dhan integration | Instrument resolution, data retrieval, normalization, and provider error handling | After spec approval and receipt of the necessary Dhan details |
| Risk and exits | Stop-loss, targets, exit prices, and outcome calculations | After the user supplies and approves those rules |

Creating this draft does not authorize application coding. The current foundation deliberately has no executable application. A runnable scanner is an implementation deliverable, not a claim about the present workspace.

## 2 Product workflow

The primary workflow is a terminal session. The user starts the future runner, enters one or more stock symbols, supplies a trading date, and presses Enter. The runner performs one scan of available data and prints one result per distinct stock, including stocks that do not qualify and stocks whose data could not be evaluated.

The terminal runner and HTTP API will call the same analysis service. The terminal runner will work directly with that service, so the user will not need a separate web server running just to scan stocks. FastAPI provides an additional programmatic entry point.

### Required inputs

| Input | Requirement |
|---|---|
| Stocks | One or more stock names or exchange symbols; a comma-separated list is the proposed terminal format |
| Trading date | An explicit calendar date, displayed with its year; the proposed machine input is `YYYY-MM-DD` |
| Market | NSE cash equities for the initial scope, matching the taught stock examples |
| Candle interval | Exactly five minutes for this strategy version |
| Timezone | `Asia/Kolkata`; all times in this specification are Indian market time |
| Data source | Recorded candle fixtures initially; Dhan after integration |

Names such as L&T and HCL Technologies must resolve to the intended cash-equity instruments. A futures contract must not silently substitute for a cash stock. Ambiguous or unknown names require a useful result explaining the problem.

### Required output

The result must explain the decision, not just print a list of symbols. Each row must distinguish setup qualification, breakout confirmation, entry availability, and trade outcome. Stop-loss and exit columns remain visible but unavailable until their rules are defined.

For historical examples, entry price means the next candle's observed open. It is not an executed order fill. No brokerage order placement is part of this scope.

## 3 Confirmed trading rules

### R01 Candle interval and candle labels

Use five-minute OHLC candles. OHLC means open, high, low, and close. A candle's label is its **start time**, not its closing time.

| Label | Interval | Fully closed at |
|---|---|---|
| 10:30 | 10:30 to 10:35 | 10:35 |
| 10:35 | 10:35 to 10:40 | 10:40 |
| 10:40 | 10:40 to 10:45 | 10:45 |
| 10:45 | 10:45 to 10:50 | 10:50 |
| 11:00 | 11:00 to 11:05 | 11:05 |

The reference range is final only when all four reference candles have closed. With these labels, that is 10:50. A later breakout candle is not one of the four reference candles.

### R02 Reference candles

The reference group consists of exactly these four candles on the requested trading date:

1. 10:30
2. 10:35
3. 10:40
4. 10:45

Use candle highs and lows, including wicks. Candle color is not a qualification condition. No rule requires the first reference candle to be red or green.

### R03 Session extreme qualification

Compare the four reference candles with **all candles from 09:15 through the completed 10:45 candle**, on the same date.

At least one of the four reference candles must contain the highest high or lowest low seen in that comparison period. The high and low do not both have to be session extremes. A high formed earlier in the morning must not be ignored merely because the four reference candles have a high among themselves.

Define these quantities:

| Quantity | Meaning |
|---|---|
| Reference high | Maximum high of the four reference candles |
| Reference low | Minimum low of the four reference candles |
| Session high at qualification | Maximum high from 09:15 through the 10:45 candle |
| Session low at qualification | Minimum low from 09:15 through the 10:45 candle |

A reference high strictly above all earlier morning highs is an unambiguous high-side qualification. A reference low strictly below all earlier morning lows is an unambiguous low-side qualification. If both morning extremes occurred before the four-candle window and neither is matched or exceeded in that window, the setup does not qualify.

**Equal repeated session extremes remain a decision for the user:** the conversation did not settle whether matching an earlier high or low qualifies, or whether the four candles must create a strictly new extreme. Do not silently choose a tie policy. The observed qualifying examples do not rely on a tie with an earlier candle.

This comparison uses information available when the reference window completes. A new high or low later in the day must not retroactively invalidate an earlier qualification. It is not a comparison with the eventual full-day high or low.

### R04 Fixed breakout range

After qualification, fix the reference high and reference low of the **whole four-candle group**. These are the breakout levels.

The breakout reference is not the 09:15 candle's range and not automatically the range of only the candle that created the session extreme. Consolidation after the reference group does not expand, move, or recalculate these two levels.

### R05 Wait without a fixed breakout time

After the reference candles finish, evaluate subsequent candles chronologically. The breakout can occur at 10:50, 11:00, 12:00, or later in the trading session. No specific breakout time is mandatory.

Price may consolidate inside the range for many candles. Do not reject the setup just because the first candle after the reference group does not break out. Do not add a midday deadline or a maximum consolidation length that the user has not supplied.

### R06 Break and close outside

A candle confirms an upward breakout when its **close is strictly above the reference high**. It confirms a downward breakout when its **close is strictly below the reference low**.

- A wick that crosses a boundary but closes inside the range does not confirm a breakout.
- A close exactly on a boundary is not outside the range.
- A candle that is still forming cannot confirm a breakout.
- The first later candle satisfying the closing condition is the confirmed breakout candle.
- After an unsuccessful wick excursion, continue waiting for a qualifying close.

No minimum breakout distance, candle body percentage, volume filter, indicator, or extra confirmation candle has been taught. Do not add one.

### R07 Entry on the next candle

Do not enter during the breakout candle. Wait for it to close, then use the **immediately following candle's open** as the entry reference.

The breakout candle is the first candle in this two-candle sequence. The entry candle is the second. This does not mean waiting two additional candles after the breakout.

For a close above the reference high, report a long signal. For a close below the reference low, report a short signal. The confirmed description permits either range boundary to trigger after qualification; it does not add a separate rule restricting direction according to which session extreme qualified.

Do not wait for the entry candle to close. Do not require the entry candle to make another high or low before entry.

### R08 Precise timing example

In the confirmed HCL Technologies example, the candle **starting at 11:00** breaks below the reference low and closes at **11:05**. Entry is at the open of the candle **starting at 11:05**, which runs until 11:10.

It is not entry at 11:00, not waiting until 11:10, and not waiting for the 11:05 candle to close. These times describe that example, not a fixed-time entry rule for other stocks.

### R09 Qualification and outcome are different

A qualifying setup and valid entry can subsequently fail. Asian Paints is the user's example of this. L&T is a separate example where the setup never qualifies.

The scanner must not turn a later reversal into a new entry filter or label a setup invalid just because its later price movement was unfavorable. It must not claim a causal explanation for failure from candle movement alone.

The scanner can report setup and entry status now. Automated profit, loss, stop-out, success, or failure evaluation requires the future stop-loss and exit rules. The user's labels for teaching examples are retained as labels supplied by the user, not as computed outcomes.

### R10 Stop loss and exits remain undefined

The following have not been taught: initial stop-loss price, stop-loss trigger type, profit targets, trailing rules, time exit, position size, partial exits, re-entry, and treatment of simultaneous intrabar target and stop touches.

Until those rules are approved, return `null` for stop loss, target, exit time, exit price, and computed profit or loss, with a readable explanation such as **Rules not yet defined**. Do not use zero as a substitute. Do not assume the opposite range boundary is a stop loss or choose a risk-to-reward target.

## 4 Evaluation sequence and result states

The following state names are a proposed interface design. They describe the confirmed logic without changing its trading conditions.

| State | Meaning |
|---|---|
| `waiting_for_reference` | The requested current session has not yet produced all four closed reference candles |
| `invalid_data` | Required candle coverage is missing or contradictory, so a reliable decision cannot be made |
| `not_qualified` | Valid reference data exists but the session-extreme requirement fails |
| `needs_rule_decision` | A case depends on an unresolved rule such as an equal repeated extreme |
| `waiting_for_breakout` | The setup qualifies; no later closed candle is outside the range as of the scan |
| `no_breakout` | A completed historical session qualifies but has no confirmed breakout |
| `awaiting_entry` | A breakout is confirmed but the immediately following candle's open is not yet available |
| `entry_identified` | Qualification, breakout, next candle, and its opening reference price are available |
| `entry_unavailable_session_end` | Proposed in 0.2.0: a breakout is confirmed on the last candle of a completed session, so no same-session next candle exists (see D07) |
| `no_session` | The requested date has no supported trading session |
| `symbol_error` | The stock could not be resolved unambiguously |
| `provider_error` | Candle retrieval failed; include a sanitized, actionable reason |

Evaluate data validity before setup qualification. Once a setup is known not to qualify, do not present a later range crossing as an entry under this strategy.

For the initial scanner, the proposed output is the first confirmed breakout and its next-candle entry for each stock and date. Multiple signals and re-entry are decisions listed below; the implementation must not fabricate additional trades.

## 5 Candle data contract and validation

Both fixture data and Dhan data must normalize to the same internal candle representation before strategy evaluation.

| Field | Requirement |
|---|---|
| Symbol and instrument identity | Resolved cash-equity symbol, exchange segment, and provider identifier when applicable |
| Candle start | Timezone-aware timestamp normalized to Indian market time |
| Interval | Five minutes |
| Open, high, low, close | Positive finite decimal prices, retained at source precision |
| Volume | Nonnegative when supplied; not a trading condition |
| Candle completion | Explicitly known or reliably derived from the scan time and data contract |
| Provenance | Provider or fixture name, retrieval time, and coverage or as-of time |

### Coverage

All 19 five-minute candles from 09:15 through 10:45 are needed for an ordinary session's qualification check. All four reference candles are mandatory. Missing morning data can conceal an earlier extreme and cannot be ignored.

To identify the **first** later breakout, coverage must also be continuous from 10:50 through the reported breakout. To report its entry open, the immediately following scheduled candle must exist. Do not jump over a missing candle and call a later candle the next one.

For a completed historical session, check the session's full relevant coverage before declaring that no breakout occurred. For the current date, report the as-of time and use only closed candles for qualification and breakout confirmation.

### Normalization

- Sort candles chronologically and isolate the requested symbol and Indian trading date.
- Validate that high is at least open, close, and low, and low is at most open, close, and high.
- Reject conflicting duplicate timestamps; identical duplicates may be removed with a data-quality note.
- Do not fill absent candles with invented flat OHLC values or forward-filled prices.
- Do not mix pre-market, previous-day, futures, or after-session data into the morning comparison.
- Use decimal comparisons at provider precision; avoid changing decisions through binary floating-point rounding.
- Preserve raw provider provenance so chart and Dhan discrepancies can be reconciled.

The initial provider contract is five-minute candles. If a provider response requires aggregation from one-minute data, that aggregation and its bucket alignment need an explicit reviewed contract before use.

### Session boundaries

The initial supported session is a normal NSE cash-equity day beginning at 09:15. Holidays and exceptional schedules require calendar or provider validation; a special session without the taught reference times cannot be forced into this strategy.

The proposed initial behavior is to keep every scan within the selected trading date. If the last breakout has no next same-session candle, leave entry unavailable rather than substituting the following trading day's open. This session-boundary choice needs approval with the project spec.

## 6 Dhan integration boundary

Dhan's published historical-data interface includes five-minute intraday candles with OHLC, volume, and timestamps. Its intraday response is represented by aligned arrays. The adapter must preserve alignment and validate lengths before constructing candle records. See [Dhan historical data documentation](https://dhanhq.co/docs/v2/historical-data/).

The user will provide the actual API details and sample data later. Before integration, confirm credentials and access requirements, instrument lookup, request date semantics, timestamp units and timezone, candle start labeling, partial-candle behavior, data adjustment policy, and applicable request limits against the current official contract and a sample response.

The core strategy must not know Dhan request headers or response array shapes. The provider adapter handles those details and supplies normalized candles. Do not hard-code security identifiers from the examples.

Credentials belong in local environment configuration, not scan inputs, terminal command history, fixtures, source files, logs, or API responses. `.env.example` is blank; `.env` is excluded from Git. API calls and dependency installation are deferred in this stage.

## 7 Terminal and HTTP interfaces

### Terminal behavior

Proposed prompt sequence:

```text
Trading date [YYYY-MM-DD]: 2026-11-13
Stocks [comma separated]: HCLTECH, LT, SUNPHARMA
```

Pressing Enter after the stock list performs one scan. The terminal prints a summary table and concise explanations. It should allow another request without requiring source-code edits. Empty input, malformed dates, unknown symbols, and provider errors should produce useful messages rather than unexplained tracebacks.

Normalize case and surrounding whitespace, remove duplicate symbols while preserving input order, and show which names were resolved. Do not exclude nonqualifying or errored stocks from the report. A problem with one stock should not erase successful results for other stocks.

The default view can be compact, with an optional detailed view exposing the four candle values and qualification evidence. Machine-readable JSON output is proposed for later automation.

The intended terminal presentation for the observed 13 November examples is illustrated below. This is a design example, not output from an implemented scanner; the chart-to-provider reconciliation in `EXAMPLES.md` still applies.

| Stock | Setup | Direction | Breakout candle | Entry candle | Entry open | Stop loss | Exit |
|---|---|---|---|---|---:|---|---|
| HCLTECH | Qualified | Short | 11:00 | 11:05 | 1,384.90 | Not defined | Not defined |
| LT | Not qualified | — | — | — | — | Not defined | Not defined |
| SUNPHARMA | Qualified | Short | 10:50 | 10:55 | 1,906.60 | Not defined | Not defined |

Price values in the JSON interface are proposed as decimal strings so source precision can be preserved; missing values are `null`. Human-readable output may format those values as INR amounts without rounding them before strategy comparisons.

### Result fields

| Group | Fields |
|---|---|
| Request identity | Input name, resolved symbol and instrument, date, timezone, interval, strategy version |
| Data coverage | Source, retrieved-at time, as-of time, last closed candle, completeness notes |
| Decision | State, setup qualified or unknown, readable reason |
| Qualification evidence | Morning session high and low, which reference candle or candles supplied the qualifying extreme |
| Reference range | All four candle records, reference high and low |
| Breakout | Direction, candle start, candle end, close, and confirmation time |
| Entry | Expected next start time, observed entry time when available, next-candle open, price basis |
| Future risk and exits | Stop loss, targets, exit time and price, outcome, and profit or loss; unavailable until defined |

When a result does not qualify, there is no strategy entry price. When a breakout is confirmed but the next open is absent, its expected time may be known while the entry price remains unavailable. Current-price quotes must not replace a missing historical entry open.

### Proposed FastAPI endpoints

| Method and route | Responsibility |
|---|---|
| `GET /health` | Report that the local process is running, without placing a provider request |
| `POST /v1/scans` | Validate a stock list and date, then return the same per-stock analysis available in the terminal |

Malformed request shapes return a validation error. A structurally valid batch returns per-stock result states, allowing mixed qualification and data errors. The exact request and response models will follow this contract after approval.

No dashboard, database, user-account system, queue, scheduler, continuous live monitor, or order-execution service is required for the first implementation. A bare-minimum web UI was later requested by the user (section 13, U1). A local server will bind to `127.0.0.1` by default.

## 8 Proposed implementation foundation

Use Python 3.12 or newer, FastAPI for the HTTP adapter, Pydantic for validation, Uvicorn for serving, HTTPX for external HTTP requests, and pytest for acceptance testing. Keep the engine independent of network and terminal operations.

The terminal is a thin interface over the analysis service, not a second copy of the strategy. Fixture and Dhan providers implement the same data boundary. Initial runs should not require a database.

See [PROJECT_SETUP.md](docs/PROJECT_SETUP.md) for the proposed module layout and future run commands. The dependency manifest is a foundation only; versions will be locked and installation verified during implementation.

## 9 Example cases and acceptance

The teaching examples, exact chart-displayed values that were read, and synthetic boundary cases are documented in [EXAMPLES.md](docs/EXAMPLES.md).

| Example | Expected setup result | Entry or outcome lesson |
|---|---|---|
| Sun Pharma, 13 November 2026 | Qualifies | Lower-range close followed by next-candle entry; user-designated success example |
| Asian Paints, 6 November 2026 | Qualifies | Same entry logic; user-designated failure after entry, not a qualification failure |
| L&T, 13 November 2026 | Does not qualify | Earlier morning extremes are outside the four-candle group; no strategy entry |
| HCL Technologies, 13 November 2026 | Qualifies | 11:00 breakout candle closes at 11:05; entry is the 11:05 candle open, 1,384.90 as displayed |

The future test suite must verify qualification separately from breakout and entry timing. Tests should cover the taught examples using complete approved fixtures and the edge conditions in the examples document. Repeating the same input and strategy version must produce the same result.

Chart observations are reference evidence, not a complete historical dataset. Before asserting numeric parity with Dhan, acquire complete candles and reconcile provider precision, instrument identity, date, and adjustment differences.

## 10 Decisions still open

| Decision | Current treatment |
|---|---|
| Stop loss, targets, exit, and profit or loss | Await the user's teaching; output unavailable |
| Equal repeated high or low matching an earlier morning extreme | Await the user's definition; mark affected cases as needing a rule decision |
| More than one valid breakout or a later opposite breakout | Proposed initial scan reports only the first signal; re-entry awaits a rule |
| Reference group containing both the session high and low | The confirmed qualification condition is satisfied; proposed first-signal handling still needs approval |
| Gap opening beyond a range boundary | Whether a gap must trade through the level before qualifying was not taught; flag such a case for a rule decision rather than inventing a filter |
| Entry unavailable at the session boundary | Proposed same-date-only treatment; no next-day substitution |
| Short deadline before market close | None taught; do not add one |
| Precise Dhan mapping and data conventions | Confirmed with a live response on 15 November 2026 (section 13) |
| Dhan intraday data ends with the 15:10 candle | Missing 15:15-15:25 candles are not invented, so `no_breakout` and 15:10 breakouts report `invalid_data`; whether to treat 15:10 as the session end for Dhan data is the user's decision (U5) |
| Chart readings versus Dhan values | 20 of 74 recorded chart values differ from Dhan by at most 0.90; no qualification, range, breakout, or entry-time decision changes (EXAMPLES.md section 7). Dhan is the data source going forward |

The core examples can be reviewed without resolving every future exit question. Any implementation approval should name its scope: setup and entry only, or the larger system after the remaining rules are supplied.

## 11 Approval record

| Item | Value |
|---|---|
| Draft version offered for review | 0.2.0 |
| Confirmed trading explanation in chat | Yes |
| User approval of this written project specification | Approved by the user in chat on 15 November 2026: "i have approved u start coding" |
| Authorized implementation scope | Setup and entry implementation (stage 2 in section 1) only. Dhan integration awaits the API details. Risk and exits await the user's rules. The open decisions in section 10 remain unresolved and are reported as `needs_rule_decision` or as unavailable, never as defaults. |
| Later user requests | 15 November 2026: the user asked for a bare-minimum React and Tailwind UI using Dhan Data API data, and supplied Dhan credentials (stored only in the local `.env`). Implemented as section 13. |
| Approval date or user message | 15 November 2026, the chat message quoted above. Note: section 12 was written into the draft during the same working turn in which this message arrived. The user may ask for any section 12 item to be revised; a revision is written here before the code changes. |

Before coding, the user must explicitly approve this specification or an agreed revision. Record that decision and its scope here. Changes to trading behavior after approval must be written into the spec before they are implemented.

## 12 Proposed implementation decisions for the setup-and-entry release

**Status: written in 0.2.0 and covered by the 15 November 2026 approval (see the note in section 11).** These items make the "proposed" parts of sections 2 to 7 concrete. They do not change rules R01 to R10, and they do not settle any open decision in section 10. Each open decision is still reported as `needs_rule_decision` or as unavailable.

| ID | Decision |
|---|---|
| D01 Scope | Setup and entry only. The Dhan provider is a stub. It returns `provider_error` ("Dhan provider not configured") for every stock and never falls back to fixture data. Stop loss, target, exit, and outcome fields are `null` with the reason **Rules not yet defined**. |
| D02 Session window | Normal NSE cash session only: candle starts 09:15 through 15:25 (75 candles, last close 15:30), on the requested date. Candles from other dates or outside this window are dropped with a data-quality note. A timestamp not on the five-minute grid, a candle that violates the OHLC relationships, or a conflicting duplicate anywhere in the day's data makes the result `invalid_data`. Identical duplicates are removed with a note. |
| D03 Data as-of and closed candles | Every provider response carries a data as-of time. For Dhan this is the retrieval time. For a fixture it is the recorded snapshot time, and a completed-session fixture is recorded after 15:30. A candle is closed when as-of ≥ start + 5 minutes. Only closed candles count for qualification and breakout. The entry open is available once the entry candle is present and has started. A candle that starts after the as-of time is contradictory (`invalid_data`). A session is complete when as-of ≥ 15:30 on its date. A trading date later than today in Asia/Kolkata is rejected as an input error. |
| D04 Qualification and ties | Compare the reference group with the 15 earlier candles (09:15 to 10:25). Each side is either `new_extreme` (strictly beyond every earlier candle), `equal_to_earlier` (equal to the earlier extreme), or `not_extreme`. The setup qualifies if either side is `new_extreme`; a tie on the other side does not matter. Otherwise, if either side is `equal_to_earlier`, the result is `needs_rule_decision`. Otherwise it is `not_qualified`. The evidence names the reference candle or candles that hold each extreme and the earlier candle that beat or tied it. Equal values among the four reference candles themselves are not a tie problem. |
| D05 Gap flag | The first candle that closes outside the range may lie entirely beyond the boundary it closed beyond: for an upward break, its low is above the reference high; for a downward break, its high is below the reference low. That candle never traded at or through the level, and the open gap policy decides it. The result is then `needs_rule_decision`, the candle is shown as evidence, no entry is reported, and no later breakout is searched for. A breakout candle that opens beyond the boundary but trades back to or through it is an ordinary breakout. This is case A21 ("opens and remains beyond"). It keeps Asian Paints' 10:50 candle, whose high of 2,501.10 is above both the inspected 2,500.90 and the drawn 2,500.60 levels, as an ordinary breakout. |
| D06 First signal only | Report only the first confirmed breakout and its next-candle entry. The strategy uses no candle after the entry candle: no re-entry, no opposite signal, no outcome. |
| D07 Coverage | All 19 candles from 09:15 to 10:45 must be present and closed. Every candle from 10:50 through the breakout must be present. The entry candle is exactly breakout start + 5 minutes, and no slot is skipped. In a completed session, any missing required candle gives `invalid_data` naming the missing times. `no_breakout` requires every candle from 10:50 to 15:25. A breakout on the 15:25 candle gives `entry_unavailable_session_end`, with no next-day substitution. In an incomplete current session, a gap before the last returned candle gives `invalid_data`. Candles after the last returned candle are treated as not yet available, which gives `waiting_for_reference`, `waiting_for_breakout`, or `awaiting_entry`. |
| D08 Explicit provider | The provider is a required choice: `--provider fixture` or `--provider dhan` in the terminal, and a required `provider` field in the API. Every result names its provider and carries a `synthetic` flag. The terminal prints a SYNTHETIC DATA banner when one applies. |
| D09 Fixtures and teaching examples | Offline demonstrations and end-to-end tests use clearly labeled synthetic instruments (prefix `SYN`, `synthetic: true`) that carry no real stock names. The chart readings in `EXAMPLES.md` are stored as partial observations with chart-reading provenance. Tests run the engine's range, side-comparison, breakout, and entry steps on exactly those observed values. Examples: HCL breakout 11:00, entry 11:05 at 1,384.90; Sun Pharma entry 10:55 at 1,906.60; Asian Paints entry 10:55 at 2,495.70 under both candidate lows; L&T rejected on the 09:50 high and the 09:20 low. A full scan of those stocks through the fixture provider returns `invalid_data` listing the missing candles until complete provider data exists. No candle is filled in. The user's success and failure labels are kept as labels, never as computed outcomes. |
| D10 Fixture instruments | The fixture provider resolves names case-insensitively from a static alias table: HCLTECH or HCL Technologies; SUNPHARMA or Sun Pharma; ASIANPAINT or Asian Paints; LT, L&T, or Larsen & Toubro; plus the synthetic symbols. All are NSE cash equity, with no security identifiers. An unknown or ambiguous name gives `symbol_error`. Inputs are trimmed, and duplicates, including two names for the same instrument, are reported once in first-seen order. |
| D11 Terminal | `python -m trading_scanner.cli --provider fixture` prompts for the date and a comma-separated stock list, then scans when you press Enter. It prints a summary table and a one-line explanation for every stock, then asks for the next request; a blank date or `q` quits. `--date` with `--stocks` runs a single scan. `--details` shows the four reference candles and the evidence. `--json` prints the same JSON as the API. |
| D12 HTTP | `GET /health` returns process status without calling a provider. `POST /v1/scans` accepts `{"trading_date": "YYYY-MM-DD", "stocks": [...], "provider": "fixture"}` (1 to 100 stocks) and returns one result per distinct stock. A malformed shape, an empty list, an invalid date, or a future date returns HTTP 422. Prices are decimal strings, and unavailable values are `null`. The server binds to `127.0.0.1` by default. |
| D13 Determinism and versioning | Prices are parsed as decimals from source strings, never binary floats. The same candles, as-of time, and strategy version give the same result. Each result reports strategy version `0.2.0`. |
| D14 Environment | `.venv` is created with `python3.12`. Exact dependency versions are locked in `requirements.lock`, produced by `uv pip compile` in a pip-installable format. No database, frontend, order placement, indicators, or extra filters. |

## 13 User-requested additions on 15 November 2026

**Request:** the user asked in chat for "a bare minimum UI for this backend where i give stocks multiple and get output using dhan api data api ... in react and styling use tailwind ... no design", and provided Dhan credentials. This adds a minimal UI to the "terminal and API" scope and replaces D01's Dhan placeholder with a working adapter. Rules R01 to R10 and decisions D02 to D14 are unchanged.

| ID | Decision |
|---|---|
| U1 Web UI | React 19 and Tailwind 4, built with Vite in `frontend/` and managed with pnpm. `pnpm dev` from the project root starts the FastAPI backend (port 8000, auto-reload) and the Vite dev server (port 5173, forwarding `/v1` and `/health` to the backend) together. `pnpm build` writes `frontend/dist`, which FastAPI serves at `http://127.0.0.1:8000/`. The page only calls `POST /v1/scans`; no trading logic runs in the browser. Inputs are the date and the stock list. At the user's request (15 November 2026) the page always sends `provider: "dhan"` and offers no test-data option; fixture data remains available through the terminal and API. Output is the same per-stock state, setup, signal, breakout, entry, entry open, stop loss and exit (Not defined), and reason, with expandable evidence. The layout is deliberately plain. |
| U2 Dhan instruments | Names resolve against Dhan's public compact scrip master (`https://images.dhan.co/api-data/api-scrip-master.csv`), downloaded at most once per day into the git-ignored `data/dhan/`. Only rows with `SEM_EXM_EXCH_ID=NSE`, `SEM_SEGMENT=E`, and `SEM_INSTRUMENT_NAME=EQUITY` qualify, preferring series `EQ`. A name matches the trading symbol, Dhan's display name, or the company name with a trailing Ltd or Limited removed, plus the D10 teaching aliases. Ambiguous or unknown names give `symbol_error`. Security IDs come only from this list and are never hard-coded. |
| U3 Dhan candles | `POST https://api.dhan.co/v2/charts/intraday` with headers `access-token` and `client-id`, and body `securityId`, `exchangeSegment: NSE_EQ`, `instrument: EQUITY`, `interval: 5`, and `oi: false`. `fromDate` is `<date> 09:00:00`, because Dhan treats `fromDate` as exclusive; `toDate` is `<next date> 00:00:00`. A live response on 15 November 2026 (HCLTECH, 13 November) confirmed parallel `open`, `high`, `low`, `close`, `volume`, and `timestamp` arrays, with epoch-second timestamps marking candle **start** times. JSON numbers are parsed as decimals. The data as-of time is the retrieval time. |
| U4 Dhan safeguards | The result is `provider_error` for unequal arrays, timestamps that are not whole epoch seconds, timestamps misaligned with the 09:15-15:25 five-minute grid, or apparent end-labeling. The error explains invalid or expired credentials, a missing Data API subscription, rate limits (DH-904 or 805), and bad parameters, without exposing secrets. An empty response is `no_session` for a past date, or not yet available for today before 15:30. Requests are spaced at least 0.25 s apart, below Dhan's documented 5 Data API requests per second. Fixture or synthetic data is never substituted. |
| U5 Dhan session tail | Dhan's intraday data observed for 11, 12, and 13 November 2026 ends with the 15:10 candle (1-minute data ends at 15:14). Following D07, the 15:15-15:25 candles are reported missing, never invented. A qualified setup with no breakout by 15:10 is `invalid_data`, not `no_breakout`, and a 15:10 breakout has a missing entry candle. **Open decision for the user:** whether Dhan data should treat 15:10 as the last candle of the session. |
| U6 Credentials | `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN` live only in the local, git-ignored `.env` (file mode 600). Dhan access tokens expire; the token supplied on 15 November 2026 is valid for 24 hours. Restart the server after updating `.env`. |
| U7 Readable UI | Requested 15 November 2026 ("it's looking too basic ... the user sees means you need to understand"). The header shows the Dhan connection state from `/health` (the four-step "how it works" strip was removed at the user's request). Below that are the stock picker (U8) and summary tiles (scanned, entries, waiting, needs attention, no trade) that filter the results. Results are sorted entries, then waiting, needs attention, and no trade. Status badges always pair color with an icon and a label. Each row expands to a four-step "why" checklist, the backend's reason, and a five-minute candle chart: reference window, fixed range band, breakout marker, entry marker, hover readout, and full candle table. Light and dark themes are supported, with a header toggle that starts from the system setting and remembers the choice in the browser (double-click to follow the system again). Up and down candles also differ by hollow or filled bodies. Scan results now include `candles`, the validated session candles behind each decision. The date defaults to the most recent weekday. |
| U8 Instrument search | Requested 15 November 2026 (suggestions while typing, showing stock versus future). `GET /v1/instruments?provider=...&query=...&limit=...` returns suggestions labeled `stock`, `future`, or `index`, from Dhan's instrument list (no credentials needed) or the fixture catalog. Exact symbols, names, and taught aliases rank first, and shorter symbols win ties. Futures show expiry and lot size, limited to the nearest three unexpired expiries per underlying. Only stocks are `scannable`; futures and indices are labeled and cannot be added, so a future never stands in for a cash stock. A "Nifty 50 stocks" button adds the 50 constituents from NSE Indices' list downloaded 15 November 2026 (`frontend/src/lib/presets.js`); refresh it when the index changes. |

