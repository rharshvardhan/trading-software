# 09:45 Three Candle Reversal Specification

**Current 09:45 requirements:** [SHORT entry spec](THREE_CANDLE_0945_CONFIRMATION_SPEC.md) and [LONG entry spec](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md) define first break, a different later confirming close, next-open entry and reference-extreme stops. The user has now explicitly supplied the **third point**: before entry, **SHORT high > group high cancels; LONG low < group low cancels; a wick is sufficient**. Both directions are implemented: revised SHORT earlier, revised LONG on 16 November 2026 (LONG spec section 12). Historical one-close/close-only expectations below (for example T04, T06 and T10) are superseded for this window by the later specs.

**Date:** 15 November 2026  
**Scope:** The user's additional reversal window, and its implementation record (section 13).  
**Source:** The user requested the same rules as the 10:30 four-candle reversal, changing only the reference group to **09:45, 09:50 and 09:55**.  
**Implementation authorization:** **Given by the user on 16 November 2026** ("implemet it"); implemented the same day (section 13).

**Later stop-loss teaching:** The user has since defined this variant's initial SHORT stop as the three-candle highest high and LONG stop as the three-candle lowest low, including wicks/body extremes. See [THREE_CANDLE_0945_STOP_LOSS_SPEC.md](THREE_CANDLE_0945_STOP_LOSS_SPEC.md). That addition is **specification only; implementation is not authorized yet**. The earlier setup-and-entry implementation approval does not cover it.

## 1 Relationship to the existing strategy

Apply the rules in [SPEC.md](SPEC.md) together with the direction and cancellation corrections in [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md). This document changes only the reference candle times, the number of reference candles, and the timing/coverage values that follow directly from that change.

The new reference group has **three candles**, not four. Every reference to the group high, group low, qualification period, window completion, and subsequent candles must use the new group for this variant. Do not keep a four-candle requirement or use any 10:30-window candle to evaluate this setup.

This is an additional strategy specification. It does not replace the existing 10:30, 10:35, 10:40, 10:45 specification. When written it authorized no code; the later implementation (section 13) adds the window to the shared engine, and every scan evaluates both windows.

## 2 The timing change

All times are Asia/Kolkata (IST). Candle labels are their start times.

| Item | Existing four-candle variant | This three-candle variant |
|---|---|---|
| Candle interval | Five minutes | Five minutes |
| Reference starts | 10:30, 10:35, 10:40, 10:45 | **09:45, 09:50, 09:55** |
| Reference candle count | Four | **Three** |
| Earlier comparison candles | 09:15 through 10:25 | **09:15 through 09:40** |
| Complete qualification window | 09:15 through the 10:45 candle | **09:15 through the 09:55 candle** |
| Qualification coverage | Nineteen candles | **Nine candles: six earlier + three reference** |
| Reference group fully closes | 10:50 | **10:00** |
| First possible later breakout/cancellation candle | 10:50 | **10:00** |
| Earliest possible entry | 10:55 open | **10:05 open**, if the 10:00 candle confirms a permitted breakout |

| Reference label | Candle interval | Fully closed at |
|---|---|---|
| 09:45 | 09:45 to 09:50 | 09:50 |
| 09:50 | 09:50 to 09:55 | 09:55 |
| 09:55 | 09:55 to 10:00 | **10:00** |

The 09:55 candle belongs to the reference group. It cannot also be the later breakout candle. Do not confirm this setup or enter before all three reference candles have finished.

## 3 Market and price data

- Use five-minute NSE cash-equity candles for the requested stock and trading date.
- Keep market open at **09:15** and the normal session boundaries from the original spec. Moving the reference window does not change exchange hours.
- Use actual candle highs and lows, including wicks, to calculate extremes and the reference range. Candle color is not a condition.
- Use source decimal precision. Do not round values into a qualification, breakout, or cancellation.
- Use only data available as of the scan. A candle is closed once the data as-of time reaches its start plus five minutes.
- Preserve the existing instrument resolution, explicit data provenance, date validation, normalization and provider error handling. Do not substitute futures, another stock, or synthetic data for actual Dhan data.

## 4 Morning extreme qualification

Compare all three reference candles with the **six earlier candles: 09:15, 09:20, 09:25, 09:30, 09:35 and 09:40**.

Define:

| Quantity | Definition |
|---|---|
| Reference high | Highest high of the 09:45, 09:50 and 09:55 candles |
| Reference low | Lowest low of the 09:45, 09:50 and 09:55 candles |
| Earlier high | Highest high from 09:15 through the 09:40 candle |
| Earlier low | Lowest low from 09:15 through the 09:40 candle |
| Morning/session high at qualification | Highest high from 09:15 through the 09:55 candle |
| Morning/session low at qualification | Lowest low from 09:15 through the 09:55 candle |

- A reference high **strictly above** the earlier high is a new morning high.
- A reference low **strictly below** the earlier low is a new morning low.
- At least one side must qualify; both are not required.
- If the reference high is below the earlier high and the reference low is above the earlier low, reject the setup as `not_qualified`. A later range crossing cannot create an entry for a rejected setup.
- A group that only equals an earlier extreme remains subject to the existing tie policy. Do not silently treat an equal value as a new extreme.
- If both sides make new extremes, direction remains an open rule. If one side makes a new extreme and the other equals an earlier extreme, the existing open tie/direction treatment also applies.

Qualification is fixed using information available when the 09:55 candle finishes at **10:00**. A later session high or low must not retroactively change that qualification. Compare against all required morning candles, not just the single 09:15 candle or the eventual full-day extremes.

## 5 Fix the three-candle range

Once the three candles are complete, fix their reference high and reference low. These two levels are used for both breakout confirmation and cancellation.

The range belongs to the **entire three-candle group**. Do not use just the candle that formed the extreme, the 09:15 candle's range, or a later consolidation range. Do not expand, trail, or recalculate the levels later.

## 6 Direction and entry conditions

| Unambiguous qualification | Setup direction | Required breakout close | Entry reference |
|---|---|---|---|
| New morning high only | **SHORT** | A later candle closes strictly **below the three-candle reference low** | Immediately following candle's open |
| New morning low only | **LONG** | A later candle closes strictly **above the three-candle reference high** | Immediately following candle's open |

After **10:00**, observe subsequent candles chronologically. The first candle to evaluate is the one **starting at 10:00**.

- A wick crossing alone does not confirm entry.
- A close exactly on a boundary is not outside the range.
- A still-forming candle cannot confirm entry.
- Wait for the breakout candle to finish, then use the **next candle's open**. Do not enter during the breakout candle or use the breakout close as the entry price.
- Do not wait for the entry candle to close or require another high/low break in the entry candle.
- A breakout can be delayed to 10:30, 11:00, 12:00 or later within the session. Do not introduce a deadline or reject the setup because the 10:00 candle stays inside the range.
- No candle-body, candle-color, minimum-distance, volume, indicator or additional confirmation filter is added.

For example, if the candle starting at **10:00** makes the permitted outside close, it finishes at **10:05**. Entry is at the **10:05 candle open**. If the breakout candle instead starts at **11:00**, entry is at the **11:05 open**. These are examples, not mandatory breakout times.

## 7 Wrong-direction close cancels the setup

Apply the cancellation rule already confirmed for the original strategy, using the **three-candle** boundaries:

| Setup | Cancelling condition before entry |
|---|---|
| LONG after a new morning low | A completed candle closes strictly **below the three-candle reference low** before a permitted upward breakout |
| SHORT after a new morning high | A completed candle closes strictly **above the three-candle reference high** before a permitted downward breakout |

- Evaluate the first completed candle whose close is strictly outside the fixed range. A close on the permitted side confirms a breakout, subject to the existing gap policy. A close on the prohibited side gives **`setup_cancelled`**.
- **Candle close is mandatory for cancellation. Wick alone does not cancel.** A boundary close or still-forming candle also does not cancel.
- After cancellation, do not keep waiting for a later permitted reversal under that setup on the same date. Do not revive it, reset the reference levels, or search for a second entry.
- A prohibited-side outside close cancels even if the candle lies entirely beyond the range; the unresolved gap question applies to a permitted breakout, as in the original strategy.
- Preserve the setup qualification and cancellation evidence. Cancellation before entry is distinct from failing qualification and from a loss after entry.
- If a permitted breakout and its next-candle entry occurred first, a later opposite close must not erase the entry or invent a stop-loss or exit. Later trade management still awaits the user's rules.

## 8 Coverage, waiting and session boundaries

Apply the original data-validity and coverage rules with the new reference window:

1. All **nine** morning candles from **09:15 through 09:55** must be present and closed to decide qualification.
2. Every scheduled candle from **10:00 through the first decisive outside close** must be present. Missing data could conceal an earlier breakout or cancellation.
3. Entry requires the immediately following scheduled candle. Never skip an absent candle and substitute a later open.
4. A current session with a not-yet-complete reference group is `waiting_for_reference`. A qualified active setup without a decisive outside close is `waiting_for_breakout`. A confirmed breakout without an available next-candle open is `awaiting_entry`.
5. In a completed historical session, missing required coverage is `invalid_data`; do not invent candles. Preserve the original treatment of gaps versus an undelivered tail in an incomplete current session.
6. Declaring `no_breakout` requires valid coverage through the session end, with neither a permitted breakout nor a cancelling close. A cancelled setup is `setup_cancelled`, not `no_breakout`.
7. Use the original same-date session-end handling. A permitted breakout on the final session candle has no same-session next candle; do not substitute the following day's open.
8. The provider session-tail issue remains date-specific. Moving the reference window does not authorize redefining session end or filling missing Dhan candles.

Keep the original normalization requirements: sort timestamps, isolate the selected instrument and date, reject invalid OHLC/off-grid/conflicting duplicate data, deduplicate identical rows with a note, and exclude other sessions or dates.

## 9 Outputs and boundaries

The intended scan result retains the original meanings: qualification evidence, the three reference candles, fixed high/low, permitted direction, confirmed breakout or cancellation, and next-candle entry time/open if available. Unresolved rules remain explicit rule decisions, and provider, symbol and data failures retain their distinct explanations.

Only the first outcome for this setup is reported: a permitted breakout with its entry, a cancellation, or the applicable waiting/data/session status. Do not add re-entry, opposite trades or multiple trades.

The implemented setup-and-entry release leaves risk fields **unavailable (`null`)**. The later [stop-loss level specification](THREE_CANDLE_0945_STOP_LOSS_SPEC.md) now defines this variant's initial price: **SHORT = group highest high; LONG = group lowest low, including wicks**. That stop-loss addition was authorized and implemented on 16 November 2026 (its section 10). Target, stop-hit/exit execution, exit time/price, computed profit/loss and computed outcome remain undefined; do not invent them. A valid setup and entry can subsequently fail without retroactively losing its qualification.

The scanner reports signals and observed reference prices. No order placement is authorized. The data/provider boundary and shared backend behavior for terminal, API and UI remain the original project design, subject to a later implementation request for this variant.

## 10 Illustrative passing and failure conditions

All prices in this section are **synthetic examples**, not actual stock data or claimed historical results. Unless stated otherwise, assume complete valid data, a fixed three-candle range of **100.00 to 110.00**, no ties or unresolved permitted-breakout gap, and an available next candle.

### Passing SHORT example

The earlier six candles have a highest high of **108.00** and a lowest low of **95.00**. The three reference candles have a highest high of **110.00** and a lowest low of **100.00**. Only the high side makes a new extreme, so this is a SHORT setup.

The **10:00** candle closes at **99.00**, below the reference low. It finishes at **10:05**. The next **10:05** candle opens at **98.80**. Report SHORT entry at **10:05**, reference price **98.80**.

### Passing LONG example

The earlier six candles have a highest high of **115.00** and a lowest low of **103.00**. The reference group is still **100.00 to 110.00**. Only the low side makes a new extreme, so this is a LONG setup.

The **10:00** candle closes at **111.00**, above the reference high. It finishes at **10:05**. The next **10:05** candle opens at **111.20**. Report LONG entry at **10:05**, reference price **111.20**.

### Acceptance cases

| Case | Conditions | Expected behavior |
|---|---|---|
| T01 Correct group | Reference data contains 09:45, 09:50 and 09:55 | Exactly these three candles define the range; no fourth candle required |
| T02 Reference forming | As-of is before 10:00; the 09:55 candle has not finished | `waiting_for_reference`; no final qualification or entry |
| T03 SHORT pass | High-only setup; first outside close is 99.00 at the 10:00 candle; next open is 98.80 | SHORT at 10:05 open, 98.80 |
| T04 LONG pass | Low-only setup; first outside close is 111.00 at the 10:00 candle; next open is 111.20 | LONG at 10:05 open, 111.20 |
| T05 Setup rejection | Earlier high 115.00 exceeds 110.00 and earlier low 95.00 is below 100.00 | `not_qualified`, even if price later crosses the range |
| T06 LONG cancelled | Low-only setup; first outside close is 99.00 | `setup_cancelled`; no SHORT and no later LONG under this setup |
| T07 SHORT cancelled | High-only setup; first outside close is 111.00 | `setup_cancelled`; no LONG and no later SHORT under this setup |
| T08 No revival | T06 or T07 is followed by a later permitted reversal | Preserve cancellation; no entry |
| T09 Wick beyond entry side | SHORT trades below 100.00 but closes at 101.00, or LONG trades above 110.00 but closes at 109.00 | No confirmed entry; keep waiting |
| T10 Wick beyond cancelling side | LONG trades below 100.00 but closes at 101.00, or SHORT trades above 110.00 but closes at 109.00 | No cancellation; keep waiting |
| T11 Boundary close | A close is exactly 100.00 or 110.00 | Neither breakout nor cancellation from that close |
| T12 Forming later candle | Current candle trades outside but is not finished | No confirmed breakout or cancellation yet |
| T13 Delayed reversal | Inside-range closes persist; 12:00 makes the first permitted outside close | Entry at the 12:05 open; no fixed-time rejection |
| T14 Missing earlier candle | A required candle from 09:15 through 09:40 is absent in a completed session | `invalid_data`; an earlier extreme cannot be excluded |
| T15 Missing reference candle | 09:50 is absent in a completed session | `invalid_data`; do not use only two reference candles |
| T16 Missing later candle | A scheduled candle between 10:00 and a proposed later breakout/cancellation is absent | Cannot establish the first decisive outside close; `invalid_data` |
| T17 Missing next open | Permitted breakout exists; immediate next historical candle is absent | Entry unavailable/invalid data under the existing coverage rule; never skip to another candle |
| T18 Entry candle changes later | Valid entry candle opens, then later closes back inside the range | Preserve the entry open; do not add an entry-close filter |
| T19 Later new extreme | A later candle creates another session high/low | Do not retroactively recompute qualification; a first prohibited-side outside close still cancels before entry |
| T20 Both sides or earlier tie | Both sides make new extremes, or eligibility/direction depends on a tie | Existing `needs_rule_decision` treatment; no invented direction priority or tie policy |
| T21 Entire permitted gap | The first outside close is permitted but its entire candle lies beyond the boundary | Preserve the original unresolved gap policy |
| T22 Entire prohibited gap | The first outside close is prohibited and its entire candle lies beyond that boundary | `setup_cancelled`; do not ask the permitted-breakout gap question |
| T23 Complete day inside range | Valid qualifying session; all later closes remain inside/on the range | `no_breakout`, subject to complete coverage |
| T24 Last-candle breakout | Permitted breakout confirms on the final session candle | Same-session entry unavailable; no next-day substitution |
| T25 Later adverse move | Entry is valid, then the market moves against it | Preserve setup/entry; no computed loss or invented stop without exit rules |
| T26 Risk fields | Original setup-and-entry release, before the later stop-loss addition | Implemented risk fields remain unavailable. The later initial stop-loss requirements are in THREE_CANDLE_0945_STOP_LOSS_SPEC.md and await coding authorization; target and exit rules remain undefined |

These acceptance cases were written as requirements first; section 13 records the tests that now cover them. The historical Sun Pharma, Axis Bank, HCL and Asian Paints examples belong to the original reference window; their recorded entry times and prices are not asserted as results of this new variant.

## 11 Inherited unresolved rules

The timing change does not settle ties with earlier morning extremes, a reference group that qualifies on both sides, permitted breakout gaps, re-entry, or exit rules. Carry their existing open treatment forward. The initial stop-loss price was taught later and is now recorded in [the stop-loss specification](THREE_CANDLE_0945_STOP_LOSS_SPEC.md); stop-hit and execution rules remain open, and coding the addition is not authorized yet. Wrong-direction-first cancellation is already resolved and must not be asked as an open rule for this variant.

The user's request defines this new window only. It does not define how to combine, rank or deduplicate simultaneous signals from the old and new variants. Do not add a cross-variant trade policy as part of this document.

## 12 Scope and authorization record

| Item | Status |
|---|---|
| User requested 09:45, 09:50 and 09:55 as a three-candle reference group | Yes |
| User requested all other taught rules to carry over | Yes, including candle-close cancellation |
| User requested the complete rules to be written and shown | Yes |
| Specification stored with the other specs | Yes, in `specs/` |
| Coding of this additional variant authorized | **Yes**, on 16 November 2026: "implemet it" |
| Application, API, UI, test or fixture code changed | **Yes**, see section 13 |

The user explicitly requested implementation on 16 November 2026; earlier approvals for the original strategy were not treated as that authorization.

## 13 Implementation record

**Authorization:** in chat on 16 November 2026, the user referred to this file and wrote "implemet it".

| ID | Implemented behavior |
|---|---|
| W1 One engine, two windows | A `ReferenceWindow` definition holds the reference, earlier, and later candle slots. `1030_four_candle` is the original window (10:30-10:45, compared with 09:15-10:25, final at 10:50). `0945_three_candle` is this variant (09:45-09:55, compared with 09:15-09:40, nine-candle qualification, final at 10:00, later candles from 10:00). The engine uses the selected window for coverage, qualification, the fixed range, direction, breakout or cancellation, entry, and every explanation. All other rules are shared code, so they carry over unchanged. |
| W2 Both windows in every scan | Changed on 16 November 2026 at the user's request ("i dont want option, i need both to run simultaneously"): there is no window choice. Every scan fetches each stock's candles once and evaluates both windows, so each stock gets one result per window. Since the third window (TWO_CANDLE_1050_REVERSAL_SPEC.md) was added, results are reported in chronological order: 09:45, 10:30, 10:50. The terminal and the web UI show a row for each window under each stock. The earlier `strategy_window` request field, `--window` option, and UI switch were removed. |
| W3 No cross-variant policy (section 11) | The two windows' results are reported side by side and independently. They are never combined, ranked, or deduplicated, and neither window overrides the other. The UI summary counts simply add results across windows, with a per-window breakdown. |
| W4 Output | Each result carries `strategy_window`, and `qualification.window` shows its qualification span (09:15-09:55 for this variant). The scan response lists both windows in `windows` (key, label, reference candles, earlier window, qualification window, range-final time). A stock-level failure (unknown symbol, provider error, no session) is reported for each window and shown once in the UI as "Both windows". The UI checklist, chart shading, and legend follow each row's window. |
| W5 Inherited open rules | Ties, both sides qualifying, and permitted-breakout gaps remain `needs_rule_decision`, and a wrong-direction close gives `setup_cancelled`, exactly as in the original window. |

**Verification:** 254 automated tests pass after the both-windows change. `tests/test_three_candle.py` covers T01 to T24 and T26 with this section's synthetic values; T25 is the inherited "later adverse move" behavior, already tested for the original window. The synthetic demos `SYN-0945-SHORT`, `SYN-0945-LONG`, and `SYN-0945-CANCEL` match T03, T04, and T06/T08. A live Dhan scan with this window on 13 November 2026 returned results without errors, including an L&T SHORT entry at the 10:20 open (4,172.00) and HCL Technologies and Sun Pharma SHORT setups cancelled by upward closes. As section 10 requires, these live results are not asserted as historical teaching results.

