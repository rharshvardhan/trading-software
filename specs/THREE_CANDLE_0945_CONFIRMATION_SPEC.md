# 09:45 SHORT: First Break, Later Confirmation, Then Entry

**Date:** 16 November 2026  
**Authorization:** The user requested implementation of the 09:45 SHORT correction, then confirmed its price conditions and corrected the BEL entry time to **11:00**.  
**Status:** The 09:45 SHORT entry correction and upper-wick cancellation are implemented. The user has now explicitly taught cancellation as the **third point**, after temporarily asking to reserve it, and instructed the opposite rule for LONG. The third point is no longer pending. This turn updates documentation only; the existing SHORT code already matches it. See section 8 for the earlier verified implementation.

**Later opposite LONG teaching:** The user then confirmed that all these rules should be mirrored for the morning-low LONG and requested a spec. [THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md) records first high breach, a different later close above, next-open entry and reference-low stop. The user has now confirmed its mirrored lower-wick cancellation as the third point. The user later authorized coding it; the mirrored LONG flow was implemented on 16 November 2026 through the same engine function (see that document's section 12). This implementation record remains SHORT-specific.

## 1 Scope and precedence

This correction covers the **09:45 SHORT** described by the user: reference candles **09:45, 09:50, 09:55**, on the five-minute chart. It refines the one-close entry in [THREE_CANDLE_0945_REVERSAL_SPEC.md](THREE_CANDLE_0945_REVERSAL_SPEC.md), and records the now-explicit third point: a pre-entry high breach, including a wick, cancels this SHORT. This agrees with [WICK_CANCELLATION_SPEC.md](WICK_CANCELLATION_SPEC.md) for this scope. The mirrored 09:45 LONG is covered by its own, since implemented, specification; the two later windows retain their separately authorized behavior, and the global wick amendment is not silently implemented outside the 09:45 window.

Morning qualification still starts at **09:15**, comparing the whole reference group against all earlier candles through 09:40. A new morning high yields SHORT, subject to existing unresolved ties/both-sides rules. Use information available when the group finishes at **10:00**, not the eventual full-day extreme.

Let **H** be the maximum high of the three reference candles, **L** their minimum low. Include reference wicks and keep the whole-group range fixed.

## 2 Confirmed sequence

1. Starting after the reference group finishes, identify the **first later candle with low < L**. The break may be a wick with an inside/boundary close, or an outside close. Mere equality of the low is not a break.
2. Starting with a **different candle after that first break**, wait for the **first completed candle with close < L**. The user explicitly clarified that its open may be above or below L. No full-body-below, high-below, candle-color or consecutive-closes filter is added.
3. Entry is the **open of the candle immediately after that confirmation**. Do not enter at the first-break close, at the confirmation candle's open, or at the confirmation close.

The confirmation may be the immediate next candle or a later candle after consolidation. If an intervening candle does not close below L, continue waiting with the same fixed range. Do not cancel simply because the immediately next candle failed to confirm, require a new reference group, or introduce a deadline.

A first-break candle that already closes below L cannot also serve as its own second-candle confirmation: another later candle must close below L. Thus both **wick then later close** and **outside close then another later outside close** are valid sequences. The following open is the entry in either case.

A forming candle's reliable as-of low can establish the first break, but a forming close cannot confirm entry. Every confirmation must finish before the next open is used.

### Timing examples

| First break | Later confirmation candle | Confirmation completes | Entry open |
|---|---|---|---|
| 10:00 | 10:05 | 10:10 | **10:10** |
| 10:05 | 10:10 | 10:15 | **10:15** |
| 10:25 | 10:55 | 11:00 | **11:00** |
| 10:25 | 11:00, if no earlier later candle confirmed | 11:05 | **11:05** |

Times are Asia/Kolkata and labels are **start times**. These are conditional examples, not fixed trigger times. The earliest possible entry for this corrected SHORT is 10:10.

## 3 Third point: SHORT setup cancellation

**The user explicitly taught this point and then instructed the opposite rule for LONG.** Before entry, if a post-reference candle's **high > H**, cancel this SHORT setup. Even an upper wick above the highest high of the 09:45/09:50/09:55 group is sufficient. A completed close above H is not required.

- Start only after the reference group is complete, using the same fixed H throughout the entry search.
- Check this breach before accepting a first downward break or a later confirming close from that candle. A candle with high > H and close < L still cancels; its close cannot rescue the entry.
- A touch exactly at H without crossing it is not a break. Use strict comparisons at actual source precision; add no buffer.
- Reliable forming-candle high data can establish a breach without waiting for that candle to close. Historical OHLC identifies the candle, not the exact second of the crossing.
- After cancellation, do not report an entry, trade stop, target or exit, and do not revive or restart this same stock/date/window setup on a later downward close. Other windows remain independent.
- This is cancellation **before entry**. A valid entry already established at its open is not retrospectively erased by later movement; stop-hit and exit execution still require their own rules.

The earlier instruction to reserve this point is resolved by the user's later explanation. There is no pending close-versus-wick question for this cancellation.

## 4 Initial stop loss

**Initial SHORT stop = H**, the highest high of the same 09:45/09:50/09:55 group, including its wick/body extreme. The user identified **09:55** as the high-holder in the BEL example.

This is the existing level in [THREE_CANDLE_0945_STOP_LOSS_SPEC.md](THREE_CANDLE_0945_STOP_LOSS_SPEC.md). Report it after confirmation for an identified or pending entry, respecting the existing **STOP_LOSS_ENABLED** switch. This request does not silently turn that switch on. There is no trade stop before confirmation or for a cancelled setup. The third point defines pre-entry cancellation; the initial stop level does not define stop-hit execution after entry.

No buffer, trailing replacement, later-candle high, stop-hit/fill, target/exit execution or calculated profit/loss is supplied by this amendment.

## 5 Teaching evidence and corrected BEL time

### SBI Life: user-supplied output

The pasted result gives range **1,798.20–1,806.10**, a possible first break at **10:05** with close **1,798.10**, and the old entry at the **10:10 open 1,798.10**. The user said the 10:10 candle did not provide the required below-range confirmation. That open alone cannot establish entry from the stated first-break/confirmation sequence. Continue waiting for a later confirming close. No exact 10:10 close, date or complete raw fixture was supplied; do not fabricate one or assert a full historical result from the excerpt. Earlier candles still determine the actual first breach and whether the third-point cancellation occurred before entry.

### BEL: 13 November 2026, TradingView observations

The visible chart is **Bharat Electronics (BEL), NSE, five minutes**. The following are displayed readings inspected during this conversation, not a complete raw provider fixture.

| Candle start | Open | High | Low | Close | Relevance |
|---|---:|---:|---:|---:|---|
| 09:45 | 404.10 | 405.50 | 404.10 | 405.45 | Reference |
| 09:50 | 405.60 | 405.65 | 404.80 | 405.20 | Reference |
| 09:55 | 405.20 | **406.00** | 405.15 | 405.80 | Reference high; stop level |
| 10:25 | 404.40 | 404.50 | **403.75** | 404.10 | Wick below group low; close on boundary |
| 10:55 | 404.40 | 404.50 | 404.00 | **404.00** | Later below-range close; finishes at 11:00 |
| 11:00 | **404.00** | 404.25 | 403.60 | 403.60 | Next open; accepted entry time |
| 11:05 | 403.60 | 403.95 | 403.35 | 403.85 | Later candle; not needed for this entry |

The observed three-candle range is **404.10–406.00**. A wick below it is present at 10:25. The **10:55** candle closes at **404.00 < 404.10**, even though its open is above L. It completes at **11:00**, so the next **11:00 open 404.00** is the entry reference. The stop level is **406.00**, the 09:55 high, when enabled.

The user initially called the confirming candle 11:00 and the entry 11:05. After the start-label/end-time distinction and actual 10:55 close were explained, the user explicitly accepted **10:55 confirmation and 11:00 entry**. Preserve that final correction rather than adding an open/body filter or skipping an earlier valid confirmation to force 11:05.

These observations establish the taught timing and prices. Complete morning/intervening data must still be obtained and reconciled before promoting this partial observation into a full historical acceptance fixture. No profit, stop hit or complete exit is claimed.

## 6 Coverage and unresolved boundaries

Preserve complete valid morning/reference coverage and continuous scheduled post-reference coverage through the decisive event. A missing historical candle is invalid data, not a failed price condition; do not substitute a later candle. Missing confirmation data during a current session means waiting, with no assumed close or entry.

Before a first breach, retain waiting/no-breakout behavior. After a first breach but before a later completed confirming close, use **waiting_for_confirmation** with no trade stop or entry price. At historical session end, a first breach without a later confirmation is no confirmed breakout/entry. If a confirmation or entry slot would fall outside the session, do not use next day's candles.

A first break candle lying entirely below L retains the existing unresolved permitted-gap policy. A later confirmation candle may be wholly below L after an ordinary first break; no new trade-through requirement applies to it.

Ties, both sides qualifying, gap treatment and stop/target/exit execution retain explicit unresolved handling. The third-point pre-entry wick cancellation is now explicit. Priority for a gap at the exact intended entry open remains an unresolved boundary case; do not infer it from later intrabar movement. These questions must not create a new body filter, retry restriction or speculative trade.

## 7 Acceptance requirements

- Accept first break by wick or close; require a different later completed close below L.
- Accept confirmation with its open above or below L; do not require its high or whole body below L.
- Allow delayed confirmation and continue waiting across inside/boundary closes and wick-only excursions.
- Never confirm from a forming close, reuse the first candle as confirmation, or enter at confirmation open.
- Enter at the immediate next open after confirmation, respecting missing-data and session-end safeguards.
- Cancel SHORT before entry on high > H, wick sufficient; mirror as low < L for the LONG specification. No entry or trade stop after cancellation.
- Preserve a valid entry when its candle later reverses or crosses the stop reference.
- Keep initial stop H at source precision when enabled; retain the existing off switch.
- Keep the separately authorized other-window behavior (the 09:45 LONG is now governed by its own implemented specification).
- Distinguish first break, confirmation and entry in the API, terminal, checklist and chart.
- Record BEL's corrected **10:55 confirmation / 11:00 entry**, without fabricating complete candles or a target/exit.

## 8 Implementation and verification record

The user's now-explicit SHORT third point matches the upper-wick cancellation already implemented below. The temporary documentation withdrawal did not change code. The mirrored LONG entry/cancellation was later implemented separately (LONG specification section 12).

Implemented in the shared backend engine, used by FastAPI, terminal scans and live refresh. The 09:45 window selects the corrected SHORT flow (and, since the later LONG implementation, its mirror); the other windows keep their prior entry flow. The result exposes **trigger**, **confirmation**, **entry_rule**, and **waiting_for_confirmation**. The existing **breakout** field holds the completed confirming candle; **entry** holds the immediately following open.

Cancellation evidence distinguishes a high breach from a cancelling close, with no fabricated intrabar confirmation timestamp. The UI checklist and chart show first break separately from the later confirmation and next entry. The synthetic 09:45 SHORT fixture now uses first break 10:00, confirmation 10:05, entry 10:10 at 98.80; it is not historical BEL/SBI data.

**Verification:** 349 automated tests pass, including 24 new cases in `tests/test_confirmation_0945.py`. They cover wick/close triggers, delayed confirmation, open above/below the low, strict boundaries, forming candles, cancellation before/on confirmation, missing coverage, session end, gap questions, post-entry reversal, source stop precision, and API evidence. Existing 09:45 SHORT tests and its synthetic fixture were updated for the extra confirmation stage; existing LONG/other-window checks pass. The synthetic-fixture consistency check and `pnpm build` pass. An offline UI checklist smoke check verified first break, later confirmation, next-open entry, initial stop, waiting and wick cancellation on explicitly synthetic API results. No real Dhan requests were made by tests. No order placement, stop-hit or exit computation was added.
