# Reversal Setup Cancellation on a Wrong-Direction Wick

**Latest 09:45 third point:** After briefly reserving cancellation for a separate explanation, the user explicitly taught it for SHORT and instructed the opposite LONG rule: before entry, **SHORT high > reference high cancels; LONG low < reference low cancels; a wick is sufficient and no outside close is needed**. The third point is no longer pending. See the [SHORT spec](THREE_CANDLE_0945_CONFIRMATION_SPEC.md), whose existing code matches it, and [LONG spec](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md), whose revised entry/cancellation was implemented on 16 November 2026 after separate authorization (its section 12). The 09:45 window therefore applies wick cancellation in both directions. Other windows retain their separately authorized implementation scope; this document's broader amendment is still not implemented for them.

**Date:** 16 November 2026  
**Status:** User-taught rule change; specification only.  
**Authorization:** The user requested this spec after the explanation below. Application, API, UI, terminal, test and fixture changes are **not authorized by that request**.  
**Scope:** Replace pre-entry close-only cancellation with cancellation on a prohibited-side price breach, including a wick. Entry still requires a permitted candle close and the immediately following candle's open.

## 1 Change and precedence

The earlier rule required a completed close beyond the prohibited boundary before cancelling a setup. While discussing ETERNAL's 12 November 2026 chart, the user corrected this: a wick beyond that boundary **before entry** already fails the setup. Waiting for a later cancelling close is incorrect under this revision.

This document supersedes conflicting cancellation wording and acceptance expectations in:

- [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md), especially sections 11 and 12.
- [THREE_CANDLE_0945_REVERSAL_SPEC.md](THREE_CANDLE_0945_REVERSAL_SPEC.md), especially section 7.
- [TWO_CANDLE_1050_REVERSAL_SPEC.md](TWO_CANDLE_1050_REVERSAL_SPEC.md), especially section 7.
- [SPEC.md](SPEC.md) and [EXAMPLES.md](EXAMPLES.md), wherever waiting after a wick would retain an already-cancelled setup.

The earlier implementation records remain historical records of close-only cancellation. They are not evidence that this revision has been implemented.

## 2 Windows and unchanged qualification

The same shared cancellation rule applies to each existing window, using that window's own fixed range:

| Window | Reference candle starts | Range final | First later candle |
|---|---|---|---|
| 09:45 | 09:45, 09:50, 09:55 | 10:00 | 10:00 |
| 10:30 | 10:30, 10:35, 10:40, 10:45 | 10:50 | 10:50 |
| 10:50 | 10:50, 10:55 | 11:00 | 11:00 |

All candles are five minutes, labeled by their start time in Asia/Kolkata. Finish the entire reference group before evaluating its later candles. A reference candle cannot cancel its own unfinished group.

Morning comparison continues to start at **09:15**, using all required candles through that window's completion. Qualification is evaluated with information available then, not with the eventual full-day extremes. The range remains the maximum high and minimum low of the whole reference group, including wicks; never expand it using later candles.

An unambiguous morning-high setup permits SHORT only. An unambiguous morning-low setup permits LONG only. This amendment does not redefine equal-extreme qualification or choose a direction when both sides qualify; see the ETERNAL explanation in section 6.

## 3 Cancellation versus entry confirmation

Let **H** be the fixed reference high and **L** the fixed reference low.

| Setup | Cancellation before entry | Permitted entry confirmation, only while the setup survives |
|---|---|---|
| SHORT after a morning high | A later candle's **high > H** | A completed candle's **close < L** |
| LONG after a morning low | A later candle's **low < L** | A completed candle's **close > H** |

- A prohibited-side wick is sufficient to cancel. The candle does not need to close outside the range, and a return inside does not undo cancellation.
- A prohibited-side body or close beyond the boundary also cancels: the rule covers any actual breach, not only candles with a visible wick.
- A permitted-side wick alone still **does not confirm entry**. Without cancellation, continue waiting for the permitted outside close.
- Comparisons remain strict. Merely reaching the boundary without going beyond it is not a breach. A permitted close exactly on the boundary does not confirm entry. Do not add buffers or round prices into a crossing.
- Once cancelled, do not revive, reset or search again for an entry under the same stock/date/window setup. A later permitted close cannot restore it.
- A cancelled setup has **no entry, stop-loss, target or exit trade values**. It is a failed candidate before entry, not a stop-loss hit or a calculated trading loss.

## 4 Evaluation order, timing and data

After valid reference data and an unambiguous direction are established, inspect subsequent candle data chronologically.

1. Check for a prohibited-side breach before accepting an entry-confirming close from that candle.
2. If that breach exists before entry, cancel and retain its evidence. Do not wait for a close to establish cancellation.
3. Otherwise, if the candle is complete and its close is beyond the permitted boundary, retain the existing breakout-gap policy and confirm entry where that policy permits it.
4. Entry remains the **immediately following candle's open**. Do not enter on a wick, enter at the breakout close, add another confirmation candle, or wait for the entry candle to finish.
5. If neither event has occurred, keep waiting within the same session. There is no new fixed breakout deadline.

### A candle crosses both boundaries before entry

If a pre-entry candle breaches the prohibited boundary and then has a permitted outside close, the setup is already cancelled. That candle's close cannot rescue it. With valid OHLC, this does not require guessing whether its high or low happened first: the prohibited breach occurred before or by the close, and entry would only occur at the next candle's open.

For example, with range 100.00–110.00, a SHORT candidate's candle with high 111.00 and close 99.00 cancels; it does not produce a SHORT entry at the next open. The symmetric LONG example has low 99.00 and close 111.00.

### Forming candles and timestamp precision

If the provider supplies reliable as-of high/low data for a started, forming post-reference candle, a prohibited breach is sufficient for cancellation without waiting for it to finish. Its forming close still cannot confirm entry. Do not use completed historical high/low values as though they had been known earlier in a live scan.

Historical five-minute OHLC identifies the cancelling **candle**, not the exact second of the breach. Report the candle start label and the observation time/as-of information that is actually known. Do not invent an intrabar timestamp, or say cancellation required the candle close. If the provider only delivers closed candles, the scanner can discover the breach only when those data arrive; this does not change the strategy trigger into a close-based one.

### Preserve coverage and the entry boundary

Continuous required data is still necessary to establish the first event. Missing morning/reference data, or a gap before the alleged cancellation/entry, retains the existing data-error handling. Do not skip missing candles or manufacture prices. A full post-reference session with no entry must also have **no prohibited breach**, rather than merely no outside close, to remain uncancelled.

A prohibited gap before entry cancels without needing a trade back through the boundary. The existing unresolved permitted-breakout gap policy is unchanged.

Once a valid next-candle open has established entry, later movement in that entry candle or subsequent candles cannot retroactively cancel it. Do not inspect the full entry candle's high/low as a pre-entry filter. This amendment defines no stop-hit or exit execution. A gap directly across the cancelling boundary at the intended entry open is not resolved by the wick example; do not invent entry-versus-cancellation priority for that simultaneous event.

## 5 Continue evaluating other windows

Cancellation is local to the stock, date and reference window. In the taught example, the 09:45 candidate fails, so continue to evaluate the 10:30 group when it completes, and the 10:50 group on its own terms.

Do not revive the 09:45 candidate using the 10:30 group's range. Do not discard a valid earlier entry merely because a later window makes a higher high or lower low. Do not pick a winner using the eventual full-day extreme or introduce ranking, deduplication, a one-trade-per-stock rule, or cross-window cancellation.

The explanation should clearly distinguish a failed candidate with no trade from the independently valid later setup. A failed window does not need hypothetical entry, stop-loss, target or exit values.

## 6 Teaching example: ETERNAL, 12 November 2026

**Evidence:** The user's screenshot and the Dhan-backed candle table inspected in the running local scanner during this conversation. These are recorded observations, not a complete historical fixture or a claim that the current implementation already applies this amendment. Prices are INR; times are IST candle starts.

### 09:45 group: no trade; wick invalidation is already visible at 10:00

| Item | Observed value |
|---|---|
| Reference group | 09:45, 09:50, 09:55 |
| Fixed range | **365.05–367.00** |
| Reference high holder | 09:55, high **367.00** |
| Earlier equal highs | 09:30 and 09:35, both **367.00** |
| First later candle, 10:00 | Open **366.70**, high **367.25**, low **366.60**, close **366.85** |
| Cancelling breach for the SHORT candidate | **367.25 > 367.00** |
| Required teaching explanation | The 09:45 candidate is already invalidated in the **10:00 candle**; no entry, stop loss, target or exit |

The 10:00 close is inside the range, but its upper wick has crossed the candidate's cancelling boundary. Under this amendment, waiting until the 10:35 outside close is too late to identify the failure. Waiting for a still-later downward close would incorrectly revive that failed candidate.

The earlier scanner displayed a tie question because 367.00 equals earlier morning highs. This amendment does **not** silently establish that equal highs qualify generally. For this specific example, accepting the equal-high candidate would still lead to cancellation at the 10:00 candle; rejecting equal-high qualification would also yield no trade. Explain the established no-trade conclusion and the wick evidence without presenting the candidate as a strictly new high or implying that a tie decision could make this an available trade. Preserve qualification uncertainty separately from cancellation evidence; do not manufacture `setup_qualified: true` for an unresolved tie.

### 10:30 group: evaluate independently

| Item | Observed value |
|---|---|
| Reference group | 10:30, 10:35, 10:40, 10:45 |
| Fixed range | **365.80–367.75** |
| New morning high | **367.75** in the **10:45** candle |
| Permitted direction | SHORT |
| Later candles before confirmation | No high above **367.75** from 10:50 through 11:40 in the inspected data |
| First permitted breakout close | **11:40** candle closes at **365.30**, below **365.80** |
| Confirmation and next entry candle | **11:45** |
| Entry reference | **SHORT at the 11:45 open, 365.25** |

The 09:45 candidate's cancellation does not block this later group. This is the valid entry to explain in this chart. Its stop-loss/exit values are not supplied by the 09:45-only stop specification, and no computed trade outcome is claimed. The separately inspected 10:50 group did not qualify; it is not a replacement for the 10:30 group.

## 7 Acceptance cases for a later authorized implementation

These are written requirements, **not executable tests added by this change**. Unless specified otherwise, use valid continuous data, an unambiguous setup, range **100.00–110.00**, and no unresolved permitted-breakout gap. Numbers other than section 6 are synthetic illustrations. Every passing-entry case assumes no earlier prohibited breach.

| Case | Conditions | Required behavior |
|---|---|---|
| WC01 SHORT wick cancellation | Before entry, high 111.00 and close 109.00 | Cancel SHORT immediately on the observed breach; no entry |
| WC02 LONG wick cancellation | Before entry, low 99.00 and close 101.00 | Cancel LONG immediately on the observed breach; no entry |
| WC03 Prohibited outside close | SHORT close 111.00, or LONG close 99.00 | Still cancels; a close also establishes a price breach |
| WC04 Permitted wick only | SHORT low 99.00, high 109.00, close 101.00; or LONG high 111.00, low 101.00, close 109.00 | No entry confirmation and no cancellation; keep waiting |
| WC05 Boundary touch | SHORT high exactly 110.00; or LONG low exactly 100.00; close inside | No cancellation from equality alone |
| WC06 Boundary entry close | SHORT closes exactly 100.00, or LONG exactly 110.00; no prohibited breach | No confirmed entry |
| WC07 Valid SHORT | High 109.00, low 98.50, close 99.00; next open 98.80 | SHORT at the immediate next open, 98.80 |
| WC08 Valid LONG | Low 101.00, high 111.50, close 111.00; next open 111.20 | LONG at the immediate next open, 111.20 |
| WC09 Both sides crossed | SHORT high 111.00, close 99.00; or LONG low 99.00, close 111.00 | Cancel; permitted close cannot rescue that candle |
| WC10 Forming breach | Reliable current candle high/low has crossed the prohibited boundary before close | Cancel as of the observed breach; no close requirement |
| WC11 Forming permitted break | Price crosses permitted boundary but candle unfinished and no prohibited breach | Wait; no entry confirmation |
| WC12 No revival | WC01 or WC02 followed by a later permitted close | Remain cancelled, with no later entry under that setup |
| WC13 Group incomplete | Last reference candle still forming | Retain `waiting_for_reference`; do not evaluate that candle as a later cancellation |
| WC14 Missing required coverage | An earlier required candle is absent before the proposed decisive event | Preserve data error/availability handling; do not establish the first event across the gap |
| WC15 Other window remains eligible | 09:45 candidate cancels; 10:30 group independently qualifies and confirms | No 09:45 trade; report the valid 10:30 entry |
| WC16 Existing entry | Valid entry open occurs first; only afterwards price crosses prohibited boundary | Preserve entry; no retroactive cancellation or invented stop/exit |
| WC17 No trade fields | Pre-entry cancellation is established | Entry, stop loss, targets, exit and computed profit/loss unavailable; cancellation evidence retained |
| WC18 Inside closes with prohibited wick | Every later close is inside, but one candle has a prohibited-side breach | Cancellation, not `no_breakout` or continued waiting |
| WC19 ETERNAL | Section 6 observations | No trade for 09:45 candidate; identify 10:00 wick evidence; independently identify 10:30-window SHORT at 11:45 open 365.25 |
| WC20 Other windows | The same pre-entry wick pattern occurs after the 10:30 or 10:50 group finishes | Apply that window's own boundaries and the same cancellation rule |
| WC21 Prohibited gap before entry | Price opens and remains beyond the prohibited boundary before any permitted confirmation | Cancel; no trade-through requirement |
| WC22 Historical time precision | Only five-minute OHLC establishes the wick breach | Name the cancelling candle; do not fabricate an exact crossing time |

Old expectations that a prohibited wick cannot cancel are superseded, including CAN-03/04/06, T10/T12 and P10/P12. Boundary-close and all-closes-inside cases must now additionally check for prohibited wicks. Historical passing examples with omitted highs/lows do not prove survival under this revision; verify the necessary observations before asserting parity or creating complete fixtures.

## 8 Output and implementation boundary

For an unambiguously qualified setup, retain `setup_cancelled` and its qualification/range evidence, but explain a **prohibited-side price breach** rather than requiring a wrong-direction close. Retain the cancelling candle's actual OHLC, the boundary and the high/low that crossed it, and available timing/provenance. An outside wick must not be mislabeled as a completed outside close or a permitted breakout.

No hypothetical trade values or stop/target/entry/exit markers should appear for the cancelled setup. Its fixed range and cancellation evidence may still be shown for explanation. Terminal, API and UI must use the same backend decision when implementation is separately authorized.

This document does not settle general earlier-extreme ties, both sides qualifying, permitted gaps, simultaneous entry-open gaps, stop-hit/target-hit rules, target measurement cutoff, position sizing, re-entry, or order execution. It does not expand the 09:45-only initial stop-loss rule to other windows.

Only this specification and documentation links are changed now. Existing code and tests still describe the prior implementation until a separate authorized implementation updates them. No test-pass count or live result from the old engine establishes compliance with this revision.
