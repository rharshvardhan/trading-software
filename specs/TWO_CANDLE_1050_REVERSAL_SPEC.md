# 10:50 Two Candle Reversal Specification

**Latest cancellation amendment, 16 November 2026:** [WICK_CANCELLATION_SPEC.md](WICK_CANCELLATION_SPEC.md) supersedes close-only cancellation wording and acceptance expectations below. Before entry, a SHORT candidate cancels when a later high exceeds the group high; a LONG candidate cancels when a later low falls below the group low, including wicks. Entry still requires a permitted close. This amendment is specification only; no coding authorization has been given for it.

**Strategy:** The user's third reversal window.  
**Reference group:** **10:50 and 10:55**, on a five-minute chart.  
**Scope:** Apply all previously taught qualification, direction, breakout, entry, and cancellation rules to this two-candle group.  
**Status:** **Implemented on 16 November 2026** after the user wrote "code it" (section 13).

**Later target teaching, documentation only:** [HIGHEST_HIGH_60_PERCENT_TARGET_SPEC.md](HIGHEST_HIGH_60_PERCENT_TARGET_SPEC.md) records both target directions and the CG Power example in this window's context. The user confirmed a **09:15** morning start, SHORT target = High - 60% of (High - Low), and LONG target = Low + that same distance. This addition is **not implemented or authorized for coding**; the measurement end cutoff and target execution still need clarification. Existing entry-direction rules are unchanged.

## 1 Relationship to the existing strategies

This variant follows [SPEC.md](SPEC.md), the direction and candle-close cancellation rules in [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md), and the same shared-rule approach as [the 09:45 three-candle variant](THREE_CANDLE_0945_REVERSAL_SPEC.md).

Only the reference candle times and candle count change. All derived comparison periods, coverage counts, range-completion times, and first possible breakout/entry times must follow the new group. Other trading conditions remain the same.

This is the **third** window, alongside the existing 09:45 and 10:30 windows. It does not replace either window. Writing this specification changed no code; the later implementation is recorded in section 13.

## 2 Timing and candle coverage

All times are Asia/Kolkata (IST). Candles are labeled by their start times.

| Item | This variant |
|---|---|
| Chart interval | Five minutes |
| Reference starts | **10:50, 10:55** |
| Reference candle count | **Two** |
| Earlier comparison candles | **09:15 through 10:45**, inclusive: nineteen candles |
| Qualification comparison | **09:15 through the completed 10:55 candle** |
| Total qualification coverage | **Twenty-one candles: nineteen earlier + two reference** |
| Reference group final | **11:00**, when the 10:55 candle closes |
| First later candle to evaluate | Candle starting at **11:00** |
| Earliest possible entry | **11:05 open**, if the 11:00 candle confirms a permitted breakout |

| Reference label | Candle interval | Fully closed at |
|---|---|---|
| 10:50 | 10:50 to 10:55 | 10:55 |
| 10:55 | 10:55 to 11:00 | **11:00** |

The 10:55 candle belongs to the reference group and cannot also be a later breakout or cancelling candle for this variant. Do not confirm qualification or entry before both reference candles finish.

Market open stays **09:15**. The normal market session and session-end rules do not move with the reference window.

## 3 Morning extreme qualification

Compare the two reference candles against **every earlier five-minute candle from 09:15 through 10:45**, not just the single 09:15 candle or the other strategies' reference groups.

| Quantity | Definition |
|---|---|
| Reference high | Maximum of the 10:50 and 10:55 candle highs, including wicks |
| Reference low | Minimum of the 10:50 and 10:55 candle lows, including wicks |
| Earlier morning high | Highest high from 09:15 through 10:45 |
| Earlier morning low | Lowest low from 09:15 through 10:45 |
| Session high at qualification | Highest high from 09:15 through the 10:55 candle |
| Session low at qualification | Lowest low from 09:15 through the 10:55 candle |

- A reference high **strictly above** every earlier high is a new morning high.
- A reference low **strictly below** every earlier low is a new morning low.
- At least one side must qualify; both extremes are not required.
- If the earlier high is above the reference high and the earlier low is below the reference low, the setup is **`not_qualified`**. Later range crossings cannot create a strategy entry for it.
- Equal earlier extremes retain the existing unresolved tie policy. Do not silently accept or reject a tie as a new extreme.
- Both sides qualifying, or one new side with a tie on the other side, retain the existing unresolved direction/tie treatment. Do not invent direction priority.

Use only information available when the group finishes at **11:00**. Do not compare qualification with the eventual full-day high/low or recalculate it from later candles.

The 09:45 and 10:30 strategy groups are part of this variant's earlier morning comparison. Their qualification, entry, or cancellation results do not automatically determine this variant's result.

## 4 Fixed two-candle range

Once both reference candles close, fix the group's highest high and lowest low. Use the **whole two-candle group**, even if its high and low occur in different candles.

Use those same two levels for both permitted breakout confirmation and wrong-direction cancellation. Do not use only the candle that made the extreme, the 09:15 candle's range, either earlier strategy's range, or a later consolidation range.

Do not expand, trail, reset, or recalculate the fixed levels after the group is complete. Candle color is not a condition; wicks are included when calculating the levels.

## 5 Permitted direction and breakout confirmation

| Unambiguous qualification | Setup | Required later close for entry confirmation |
|---|---|---|
| Two-candle group makes a new morning high only | **SHORT** | Candle close strictly **below the two-candle reference low** |
| Two-candle group makes a new morning low only | **LONG** | Candle close strictly **above the two-candle reference high** |

Starting with the candle labeled **11:00**, inspect completed candles chronologically. The first completed close strictly outside the fixed range determines a permitted breakout or a cancellation under section 7.

- **Candle close is required. Wick alone does not confirm entry.**
- A close exactly on a boundary is not outside the range.
- A still-forming candle cannot confirm a breakout.
- A breakout may occur at 11:00, 11:30, 12:00, or later in the same session. Those are examples, not fixed trigger times.
- While closes remain inside or on the range, continue waiting. Do not introduce a maximum consolidation length or an earlier deadline.
- No minimum breakout distance, body size, volume, color, indicator, or extra confirmation filter is added.
- The existing unresolved permitted-gap policy remains applicable when a permitted breakout candle lies entirely beyond its boundary without trading at or through it.

## 6 Entry on the immediately following candle

A permitted breakout candle must **finish** before entry. The entry reference is the **open of the immediately following five-minute candle**.

Do not enter during the breakout candle, substitute its close for the next open, wait for the entry candle to close, or require the entry candle to make another break. A missing immediate next candle cannot be replaced by a later candle.

| Breakout candle start | Breakout completion | Entry candle start/open |
|---|---|---|
| **11:00** | **11:05** | **11:05** |
| 11:30 | 11:35 | 11:35 |
| 12:00 | 12:05 | 12:05 |

These are timing examples only. Entry at 11:00 would be too early for an 11:00 breakout candle. Waiting until the 11:05 entry candle closes at 11:10 would be too late under the taught entry rule.

## 7 Wrong-direction close cancels the setup

Apply the already-confirmed cancellation rule using the **two-candle** boundaries:

| Setup | Cancelling close before entry |
|---|---|
| LONG after the group makes a new morning low | A completed candle closes strictly **below the two-candle reference low** before a permitted upward breakout |
| SHORT after the group makes a new morning high | A completed candle closes strictly **above the two-candle reference high** before a permitted downward breakout |

- The required result is **`setup_cancelled`**, with the cancelling candle and its confirmation time as evidence; no entry is reported.
- **Use candle close, not wick alone.** A wick beyond the prohibited boundary with a close inside/on the range does not cancel. A close exactly on the boundary or a forming candle does not cancel.
- Once cancelled, do not wait for a later permitted reversal under the same setup on that date. Do not revive it, reset the reference levels, re-search, or manufacture re-entry.
- A first prohibited-side outside close cancels even if the candle lies entirely beyond that boundary. The permitted-breakout gap question is not asked for that cancellation.
- Qualification can remain true even though the setup is cancelled before entry. This is distinct from `not_qualified`, a stop-loss hit, or a calculated loss.
- If a permitted breakout and entry occur first, later adverse movement or an opposite close must not retroactively cancel or erase that entry. Stop-loss and exit rules remain undefined.
- Cancelling this window does not cancel either other window's independently evaluated setup.

## 8 Data, waiting and session-end rules

All original data safeguards carry over, using this variant's times:

1. Require all **twenty-one candles from 09:15 through 10:55** to be present and closed before qualification.
2. Require continuous scheduled coverage from **11:00 through the first decisive outside close**. A missing candle could hide an earlier permitted breakout or cancellation.
3. Require the immediately following scheduled candle to report an entry open. Never skip an absent candle or invent an open.
4. Before the two reference candles close, report `waiting_for_reference`. After qualification but before a decisive outside close, report `waiting_for_breakout`. A confirmed permitted breakout without an available next open is `awaiting_entry`.
5. A completed historical session with missing required data is `invalid_data`. Retain the original distinction between an internal gap and an undelivered tail in an incomplete current session.
6. `no_breakout` requires sufficient coverage through the session end, with no permitted breakout and no cancellation. A cancelled setup is reported as `setup_cancelled`.
7. A permitted breakout on the final session candle has no next same-session entry candle. Keep the existing `entry_unavailable_session_end` handling; do not substitute the next trading day's open.
8. Preserve provider provenance and actual precision. Do not fill missing Dhan candles or change session end to accommodate a truncated response. Session-tail observations remain date-specific.
9. Sort/isolate the selected stock and trading date; validate OHLC and the five-minute grid; reject conflicting duplicates and contradictory future data. Identical duplicates may be removed with a note. Exclude other dates, pre-market data and after-session candles.
10. Keep the existing market, symbol, provider and date validation. Resolve NSE cash equities rather than silently substituting futures, indices, another stock or fixture data.

## 9 Outputs and shared workflow

Retain the existing per-window result meanings: stock/date, window identity, qualification evidence, the **two** reference candles, fixed range, permitted direction, breakout or cancellation evidence, entry time and next-candle open when available, plus coverage/provenance and a readable reason.

Only the first outcome for this setup is reported: a permitted breakout with its entry, cancellation, or the applicable waiting/data/session status. No extra trade, opposite entry or re-entry is introduced.

The implementation (section 13) preserves the existing all-windows scan workflow: it fetches a stock's data once and evaluates this third window independently alongside the existing two, with a result for each stock and window. The windows' results must not be combined, ranked, deduplicated into one trade, or allowed to override one another without an additional user rule.

The implemented scanner keeps stop loss, target, exit time, exit price, profit/loss and computed trade outcome **unavailable (`null`)** for this window. The later [highest-high target specification](HIGHEST_HIGH_60_PERCENT_TARGET_SPEC.md) now records a target formula and supplied example, but that addition has not been authorized for coding or implemented. Do not invent an opposite-boundary stop, a different target, or an exit based on a later range crossing. A valid entry can subsequently fail without becoming an invalid setup retrospectively.

The scanner continues to report signals and observed reference prices only. No order placement is included. Terminal, FastAPI and UI behavior must continue to use the same backend strategy rules when the new variant is eventually implemented.

## 10 Synthetic passing and cancellation examples

These are invented prices for explaining the rule, **not historical stock data**. Assume complete valid data, no ties or unresolved permitted-breakout gap, and a fixed two-candle range of **100.00 to 110.00**.

### SHORT pass

The earlier nineteen candles have high **108.00** and low **95.00**. The two reference candles have high **110.00** and low **100.00**. Only the high side makes a new extreme -> SHORT setup.

The **11:00** candle closes at **99.00**, below the reference low, at **11:05**. The next candle opens at **98.80**. Entry is **SHORT at the 11:05 open, 98.80**.

### LONG pass

The earlier nineteen candles have high **115.00** and low **103.00**. The two reference candles have high **110.00** and low **100.00**. Only the low side makes a new extreme -> LONG setup.

The **11:00** candle closes at **111.00**, above the reference high, at **11:05**. The next candle opens at **111.20**. Entry is **LONG at the 11:05 open, 111.20**.

### Cancellation

- A LONG setup's first outside close is **99.00**, below **100.00** -> **cancel**, no entry and no later revival.
- A SHORT setup's first outside close is **111.00**, above **110.00** -> **cancel**, no entry and no later revival.
- A wick crosses those cancelling levels but closes back inside the range -> **not cancelled**; continue waiting.

## 11 Acceptance cases for later implementation

These were written as requirements first; `tests/test_two_candle.py` now covers them (section 13). Assume the synthetic range above where applicable.

| Case | Conditions | Expected behavior |
|---|---|---|
| P01 Reference group | Both 10:50 and 10:55 candles exist | Use exactly these two candles, not the other windows' groups |
| P02 Reference still forming | As-of is before 11:00 and the 10:55 candle is not closed | `waiting_for_reference`; no final qualification or entry |
| P03 SHORT pass | High-only setup; first outside close is 99.00 on the 11:00 candle; next open is 98.80 | SHORT at 11:05 open, 98.80 |
| P04 LONG pass | Low-only setup; first outside close is 111.00 on the 11:00 candle; next open is 111.20 | LONG at 11:05 open, 111.20 |
| P05 Neither qualifies | Earlier high exceeds 110.00 and earlier low is below 100.00 | `not_qualified`, regardless of later range crossings |
| P06 LONG cancelled | First outside close is below 100.00 in a LONG setup | `setup_cancelled`; no SHORT or later LONG under this setup |
| P07 SHORT cancelled | First outside close is above 110.00 in a SHORT setup | `setup_cancelled`; no LONG or later SHORT under this setup |
| P08 No revival | A cancelling close is followed by a later permitted outside close | Keep cancellation; no entry |
| P09 Wick on permitted side | Wick crosses the entry boundary but close stays inside/on the range | No confirmed breakout |
| P10 Wick on prohibited side | Wick crosses the cancelling boundary but close stays inside/on the range | No cancellation |
| P11 Boundary close | Close equals 100.00 or 110.00 exactly | Neither breakout nor cancellation |
| P12 Forming later candle | Price is outside but its candle has not finished | No confirmed breakout/cancellation yet |
| P13 Delayed confirmation | First permitted outside close is on the 12:00 candle | Entry at 12:05 open; no fixed-time rejection |
| P14 Earlier data missing | Any required 09:15-10:45 candle is absent in a completed session | `invalid_data`; do not ignore an unknown earlier extreme |
| P15 Reference data missing | 10:50 or 10:55 is absent in a completed session | `invalid_data`; do not form the range from one candle |
| P16 Later coverage gap | Candle between 11:00 and a proposed decisive close is missing | Cannot establish the first decisive close; `invalid_data` |
| P17 Entry data missing | Permitted breakout exists but its immediate next historical candle is absent | Entry unavailable under the existing missing-data rule; do not substitute a later open |
| P18 Entry candle closes back | A valid entry candle later closes inside the range | Preserve its entry open; do not add a close filter |
| P19 Both sides/tie | Both sides qualify or eligibility/direction depends on an earlier tie | Existing `needs_rule_decision` treatment |
| P20 Entire permitted gap | First permitted outside close comes from a candle wholly beyond its boundary | Existing unresolved gap policy applies |
| P21 Entire prohibited gap | First prohibited outside close comes from a candle wholly beyond its boundary | Cancel; no permitted-gap rule question |
| P22 Day stays inside | Complete valid qualified session; all later closes are inside/on the range | `no_breakout` |
| P23 Final-session breakout | Permitted breakout is on the final session candle | Same-session entry unavailable; no next-day open |
| P24 Later adverse move | Valid entry is followed by movement against the trade | Preserve entry; no invented stop, exit or loss |
| P25 Risk fields | A valid entry exists | Stop loss, target, exit and computed outcome remain unavailable |
| P26 Independent windows | The same stock has different results in the three windows | Preserve each window's own range and outcome; no cross-window cancellation or priority |

## 12 Inherited open rules and authorization

The timing change does not resolve earlier ties, both sides qualifying, permitted-breakout gaps, re-entry, or stop-loss/exit rules. Preserve their existing open treatment. Wrong-direction-first cancellation is already resolved and must not be asked again as a rule question.

The original Sun Pharma, Axis Bank, HCL and Asian Paints observations belong to the previously taught reference window. Do not present their recorded entry times or prices as verified results for this two-candle variant without checking the required data for this window.

| Item | Status |
|---|---|
| User requested a third group containing 10:50 and 10:55 | Yes |
| User requested all earlier conditions to carry over | Yes, including direction and candle-close cancellation |
| New specification stored in the specs folder | Yes |
| Coding of this third window authorized | **Yes**, on 16 November 2026: "code it" |
| Application, API, UI, terminal, test or fixture code changed | **Yes**, see section 13 |

The user explicitly requested implementation on 16 November 2026; documenting the window alone was not treated as that authorization.

## 13 Implementation record

**Authorization:** in chat on 16 November 2026, the user referred to this file and wrote "code it".

| ID | Implemented behavior |
|---|---|
| X1 Window definition | A third `ReferenceWindow`, `1050_two_candle`: reference candles 10:50 and 10:55; earlier comparison 09:15-10:45 (nineteen candles); twenty-one-candle qualification; range final at 11:00; later candles from 11:00. Every other rule (qualification, ties, direction, close-only breakout, candle-close cancellation, gap policy, next-candle entry, coverage, session end, null risk fields) is the shared engine code, so it carries over unchanged. |
| X2 All windows in every scan | Every scan evaluates the 09:45, 10:30, and 10:50 windows from one data fetch per stock. Each stock gets one result per window, reported in chronological order (09:45, 10:30, 10:50); the order was made chronological when this third window was added. Results are never combined, ranked, or deduplicated, and cancelling one window does not affect another. |
| X3 Interfaces | The API's `windows` list and each result's `strategy_window` include `1050_two_candle`. The terminal table and explanations show a 10:50 row for every stock. The web UI shows three rows under each stock; the checklist, chart shading, and legend follow the 10:50-10:55 group; a stock-level error is shown once as "All windows". |
| X4 Synthetic demos | `SYN-1050-SHORT`, `SYN-1050-LONG`, and `SYN-1050-CANCEL` reproduce P03, P04, and P07/P08 with the section 10 values. |

**Verification:** `tests/test_two_candle.py` has 25 tests covering every section 11 acceptance case (P01-P26) with the section 10 synthetic values; the full suite of 282 tests passes. A live Dhan scan on 16 November 2026 of 31 stocks for 13 November 2026 returned results for all three windows without errors. For the 10:50 window it found MARUTI as a SHORT entry at the 11:10 open (12,923.00), ADANIPORTS and BHARTIARTL as cancelled setups, and the rest not qualified. As section 12 requires, these live results are not presented as verified teaching examples.

