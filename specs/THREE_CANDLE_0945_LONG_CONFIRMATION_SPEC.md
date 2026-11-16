# 09:45 LONG: Opposite of the Confirmed SHORT Rules

**Date:** 16 November 2026  
**Source:** After confirming the corrected SHORT explanation, the user instructed that all of those rules be applied in the opposite direction to the 09:45 LONG, then explicitly confirmed: write it in the spec.  
**Status:** Confirmed trading explanation. **Implemented on 16 November 2026** after the user's separate coding authorization ("Implement THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md"); see section 12. The 09:45 LONG no longer uses the earlier one-close entry flow.  
**Latest revision:** The user has now taught the third point for SHORT and explicitly instructed the opposite rule for LONG: before LONG entry, a low breach below the fixed three-candle low cancels, **even if only a wick**. The earlier reservation of this point is resolved; it is no longer pending.

**Scope:** The **09:45, 09:50, 09:55** three-candle LONG setup. The implemented SHORT rule is recorded in [THREE_CANDLE_0945_CONFIRMATION_SPEC.md](THREE_CANDLE_0945_CONFIRMATION_SPEC.md).

## 1 Morning-low qualification and fixed range

Use five-minute NSE cash-equity candles, labeled by their **start time**, on the selected trading date in Asia/Kolkata.

Compare the three reference candles against **all earlier candles from 09:15 through 09:40**. At least one reference candle must create the new morning **lowest low** for an unambiguous LONG setup. This comparison starts at **09:15**, not 09:45, and is not limited to the single 09:15 candle. It is evaluated when the reference group completes, not against the eventual full-day low.

Preserve the existing unresolved rules for equal earlier extremes, both sides qualifying and direction ambiguity. Do not use this mirror instruction to silently approve a tie or choose a direction when both extremes qualify.

All three reference candles must finish. The 09:55 candle closes at **10:00**. Then fix:

- **H:** highest high of the whole 09:45/09:50/09:55 group, including wicks.
- **L:** lowest low of that whole group, including wicks.

Mark **H** as the upward break/confirmation level for this LONG. Do not use only the candle that made the low, the single 09:15 candle's range, a later consolidation or a different window. Do not expand or reset the fixed range later.

## 2 First break: wick or close above H

Starting with the candle labeled **10:00**, observe later candles chronologically. The **first candle with high > H** starts the LONG entry sequence.

- An upper wick above H is sufficient for this first break; its close may return inside or onto the range.
- A candle that closes above H can also be the first break.
- Merely touching H does not break it. Keep comparisons strict at actual provider precision.
- This first break alone is **not an entry** and cannot serve as its own later confirmation.

There is no fixed breakout time or newly added consolidation deadline. A reliable forming candle's as-of high may establish the first breach, but its current close cannot confirm entry.

## 3 Later confirmation: close above H

After the first break candle, wait for a **different later candle** to finish with **close > H**.

- The confirming candle may be the immediate next candle or a later candle after further consolidation.
- Its **open may be above or below H**. Do not require its whole body or its low to stay above H.
- An upper wick alone does not confirm this second stage. A close exactly at H does not confirm it either.
- If a candidate candle closes inside/on the range, keep waiting for a later qualifying close, using the same fixed reference levels.
- If the first break itself closed above H, another later candle must still close above H. Both **wick then later close** and **outside close then another later outside close** are accepted sequences. No additional consecutive-close filter is added.
- Wait for the confirming candle to finish. A forming close or an opening price alone cannot establish confirmation.

## 4 Entry on the open after confirmation

Once that later confirmation finishes, LONG entry is the **open of the immediately following five-minute candle**.

Do not enter during the first break, at the first break's close, at the confirmation candle's open, or at its close. Do not wait for the entry candle to close or require it to break H again. Never skip a missing immediate entry candle or substitute a later open.

| First break candle | Later confirmation candle | Confirmation finishes | Entry candle/open |
|---|---|---|---|
| 10:00 | 10:05 | 10:10 | **10:10** |
| 10:05 | 10:10 | 10:15 | **10:15** |
| 10:25 | 10:55 | 11:00 | **11:00** |
| 10:25 | 11:00, if no earlier later candle confirmed | 11:05 | **11:05** |

These are timing illustrations, not historical LONG trades or fixed trigger times. The earliest possible LONG entry under this revised sequence is **10:10**. Candle labels are start times: a 10:55 confirmation completes at 11:00 and its next open is the 11:00 candle.

## 5 Third point: LONG setup cancellation

Mirror the user's explicit SHORT third point using the opposite boundary: before entry, a post-reference candle with **low < L** cancels this LONG setup. L is the lowest low of the original **09:45/09:50/09:55** group.

- Even a lower wick below L is sufficient. Do not wait for a completed close below L.
- Start after the reference group is complete and use that same fixed L; do not replace it using later candles.
- Check cancellation before accepting a first upward break or a later confirming close from that candle. A candle that crosses below L and closes above H cannot rescue the cancelled candidate.
- Mere equality at L does not cancel. Use strict source-precision comparisons without an invented buffer.
- Reliable forming-candle low data can establish a breach. Historical five-minute OHLC identifies the cancelling candle, not the exact second of the breach.
- After cancellation, do not revive, reset or search again under the same stock/date/window setup. A later upward confirmation must not create an entry from that cancelled group.
- A cancelled setup has no entry, trade stop, target or exit values. This is a failed candidate before entry, not a computed stop hit or trading loss.
- After a valid entry open, later movement cannot retrospectively cancel it. Stop-hit and exit execution remain separate untaught rules.

The earlier instruction to reserve this point is resolved. The rule is part of the LONG specification and is implemented (section 12). Other windows remain independent.

## 6 Initial LONG stop loss

**Initial LONG stop loss = L**, the lowest low of the original **09:45, 09:50, 09:55** reference candles.

Use whichever of those three candles holds the minimum, including a lower wick or a low coinciding with the body/close. Do not use minimum closes alone, only the low-making candle's body, the first-break/confirmation/entry candle's low, or a later low.

This is the price-level rule already taught in [THREE_CANDLE_0945_STOP_LOSS_SPEC.md](THREE_CANDLE_0945_STOP_LOSS_SPEC.md), not a new stop formula. Keep the level fixed, with no buffer or trailing update. Report a trade stop only after confirmation for an identified/pending entry, respecting the existing **STOP_LOSS_ENABLED** switch. This specification does not change that switch or define stop activation/hit, fills, targets, exits or profit/loss.

## 7 SHORT versus LONG mapping

| Condition | Confirmed SHORT | Mirrored LONG |
|---|---|---|
| Qualifying morning extreme in the three reference candles | New highest high | New lowest low |
| First later breach, wick or close | **Low < L** | **High > H** |
| Different later completed confirmation | **Close < L** | **Close > H** |
| Confirmation open | Either side of its confirming boundary | Either side of its confirming boundary |
| Entry | Immediately following candle's open | Immediately following candle's open |
| Third point: pre-entry cancellation, wick sufficient | **High > H** | **Low < L** |
| Initial stop level | **H** | **L** |

## 8 Synthetic passing and failure examples

All numbers below are **synthetic illustrations**, not actual stock data. Assume valid continuous data, earlier morning high **115.00** and low **95.00**, and reference group **H = 100.00, L = 90.00**. Only the low side makes a new extreme, so this is a LONG setup.

### Wick then later close: pass

At **10:25**, a candle reaches high **101.00** but closes at **99.00**: its upper wick starts the sequence. Intervening candles need not close above 100.00 immediately. At **10:55**, a later candle opens at **99.00** and finishes with close **101.00**, using the original fixed reference levels. Confirmation completes at **11:00**; if that candle's next open is **101.20**, LONG entry is **11:00 at 101.20**. Initial stop is **90.00** when enabled.

### First break also closes above: pass after another close

The first break at 10:25 closes at **101.00**. It still cannot confirm itself. A different later candle closes at **101.50**, then entry uses that confirming candle's immediate next open. The same fixed high and initial stop apply.

### Upper wick without the later confirming close: no entry yet

After the first high breach, later candles wick above 100.00 but close at **99.00** or exactly **100.00**. There is no confirmed entry. Continue waiting while required data remains available; do not enter because an opening price is above H.

### Third point: lower wick cancels before entry

Before entry, a later candle reaches low **89.90**, even if it returns inside the range or closes above **100.00**. Because **89.90 < L = 90.00**, cancel. No LONG, trade stop, target or exit is reported. A later upward close cannot revive this same setup. These are synthetic illustration prices, not a historical trade.

## 9 Data and inherited unresolved cases

Carry over the SHORT specification's coverage, as-of, normalization, provenance and session safeguards, using the opposite price comparisons. Require all morning/reference candles and continuous later coverage through the decisive event. Distinguish missing historical data from an ordinary nonconfirming close; never fabricate or skip candles.

After the first breach, wait for confirmation with no entry price or trade stop. If the complete session ends without a later confirmation, report no confirmed breakout/entry. If no same-session confirmation or entry slot exists, do not use next day's candles.

A first break candle wholly above H retains the existing unresolved permitted-gap policy. A later confirmation candle may be wholly above H after an ordinary first break; no extra trade-through condition is taught. A cancelling gap before entry also breaches L and cancels. Priority when the intended entry itself opens below L at the same instant remains unresolved; do not infer it from later intrabar prices.

This instruction does not settle general earlier-extreme ties, both sides qualifying, stop-hit/target-hit execution, target measurement cutoff, trailing, re-entry after cancellation, position sizing or order placement. Do not add a condition to make a particular historical outcome fit.

## 10 Acceptance cases for future implementation

These were written as requirements first. Section 12 records the executable synthetic tests that now cover them; no complete historical fixture is added.

| Case | Conditions | Required behavior |
|---|---|---|
| LC01 Low qualification | Group low is strictly below earlier morning lows; high does not also qualify/tie | LONG setup; use the entire three-candle H/L |
| LC02 First upper wick | High > H but close returns inside | First break only; wait for a different later confirming close |
| LC03 First outside close | First high breach also closes above H | Still require another later candle's close above H |
| LC04 Delayed confirmation | Immediate next candle fails; a later candle closes above H | Keep waiting without resetting the range; next open after valid confirmation is entry |
| LC05 Either confirmation open | Confirmation opens above or below H, then closes above H | Both satisfy confirmation if no third-point cancelling breach occurs |
| LC06 Confirmation wick/boundary | High > H but close <= H | No confirmation or entry from that candle |
| LC07 Forming data | Forming high breaches H; or forming close is above H | First breach may be observed; no confirmed close/entry until complete |
| LC08 Initial stop | Valid LONG confirmation/entry, switch enabled | Initial stop exactly L, wicks included |
| LC09 Lower breach before entry | Low < L even if only a wick, with close inside or above H | Cancel; no entry, trade stop or later revival |
| LC10 Boundary touch | Low equals L without crossing below | No third-point cancellation from equality alone |
| LC11 Stop level versus execution | Price later crosses the initial stop reference | No stop-hit/exit rule is inferred from the price level |
| LC12 Missing/session-end data | Required confirmation/entry coverage is absent, or next slot is outside session | Existing missing-data/waiting/session-end handling; never substitute later/next-day candles |
| LC13 Initial permitted gap | First high breach lies wholly above H | Preserve the unresolved permitted-gap question |
| LC14 Confirmation wholly above | Ordinary first break, then confirmation entirely above H | Valid later close; no new trade-through filter |
| LC15 Shared interfaces | Future LONG implementation is enabled | Terminal, API, live refresh, checklist and chart share the backend's first-break/confirmation/entry decision |

## 11 Implementation boundary

The user confirmed this mirrored explanation and requested it in the spec; the documentation turn did not authorize code. The user then separately authorized implementation with the instruction **"Implement THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md"** on 16 November 2026. The third point is explicit for both directions: SHORT high > H and LONG low < L cancel before entry, including wicks. Both 09:45 directions now share one implemented first-break/confirmation/entry flow. The 10:30 and 10:50 windows keep their separately authorized one-close flow and close-based cancellation; this implementation does not apply the broader wick amendment to them.

## 12 Implementation and verification record

**Engine.** The shared backend engine (`strategy.py`, `_evaluate_break_then_confirm`) now runs the 09:45 window's two-stage flow for both permitted directions. The window flag is `entry_rule = "break_then_confirm"` (formerly SHORT-only `short_entry_rule`); the 10:30 and 10:50 windows keep `single_close`. For a LONG, each post-reference candle is checked in this order:

1. **Third point first:** low < L cancels immediately, a wick or a reliable forming low being sufficient. The result is `setup_cancelled` with no entry, trade stop, target or exit, and the search stops, so no later revival is possible.
2. **First break:** the first candle with high > H, by wick or close. Equality does not break. A closed first-break candle lying wholly above H returns the existing `gap_beyond_range` rule question.
3. **Confirmation:** a different later completed candle with close > H, with its open unrestricted. Inside/boundary closes and wick-only excursions keep the same fixed range and wait (`waiting_for_confirmation`). A forming close never confirms.
4. **Entry:** the open of the immediately following candle, with the existing missing-candle, pending-entry and session-end safeguards. If that open is itself below L, the unresolved priority question is reported as `needs_rule_decision` / `entry_open_cancellation` (the question text now covers both directions), with no entry.

The SHORT path runs through the same function with the opposite boundaries. Its result messages are unchanged.

**Initial stop.** Unchanged: L, attached only after confirmation (identified or pending entry) and only when `STOP_LOSS_ENABLED=true`. No stop-hit, exit, target or profit/loss is computed.

**Interfaces.** FastAPI, the terminal and live refresh read the same evaluation. The API now reports `entry_rule = "break_then_confirm"` for any permitted 09:45 setup, a `trigger` with `side = "above"` for a LONG first break, and a LONG cancellation with `trigger_basis = "low"` and `confirmed_at = null`. The terminal `--details` view, the UI checklist and the chart word the first break, confirmation and cancellation by direction instead of assuming a low breach.

**Synthetic demos.** `SYN-0945-LONG` now shows 10:00 first break, 10:05 confirmation and entry at the 10:10 open, 111.20. `SYN-0945-CANCEL` now shows a pure lower wick, 10:00 low 99.50 below 100.00 with a close back inside at 100.50. The old close-only rule would not have cancelled it. Both are invented prices, not market data.

**Verification.** 380 automated tests pass. They include 31 new cases in `tests/test_long_confirmation_0945.py`, built on section 8's synthetic values (H 100.00, L 90.00; 10:25 wick, 10:55 confirmation, 11:00 entry at 101.20, stop 90.00). These cases cover LC01 to LC15 and the entry-open priority question.

Five existing tests that encoded the earlier LONG one-close entry and close-only cancellation were updated to the new rule: T04, T06/T08 and T10 in `tests/test_three_candle.py`, SL02/SL04 in `tests/test_stop_loss_0945.py`, and the all-windows API test.

The synthetic-fixture check and `pnpm build` pass. An offline checklist smoke check ran the UI's `buildSteps` on synthetic API results for `SYN-0945-LONG`, `SYN-0945-CANCEL` and `SYN-0945-SHORT`. It confirmed direction-correct first-break, confirmation, entry, stop and wick-cancellation text, with SHORT wording unchanged. No Dhan requests were made by tests. No order placement, stop-hit or exit logic was added.
