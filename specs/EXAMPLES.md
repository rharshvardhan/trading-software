# Trading Examples and Acceptance Cases

**Latest cancellation amendment, 16 November 2026:** Read these historical observations with [WICK_CANCELLATION_SPEC.md](WICK_CANCELLATION_SPEC.md). A prohibited-side wick before entry cancels the candidate; a permitted-side wick still does not confirm entry. Earlier generic wick/keep-waiting expectations are superseded where they would retain a cancelled setup. The new document includes the ETERNAL example; this amendment is specification only and has not been authorized for implementation.

These examples preserve the user's teaching and the chart values inspected during the conversation. Dates below use the year shown in the charts, **2026**. All times are in `Asia/Kolkata`, and every candle is five minutes labeled by its start time.

**Later direction clarification:** Read these historical examples and acceptance cases with [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md). A morning-high setup permits only a SHORT below the group low; a morning-low setup permits only a LONG above the group high. In particular, the directional expectations in A07 and A08 require the corresponding qualification side. The new document includes the verified Axis Bank example and direction rejection cases. The correction was implemented on 15 November 2026 (its section 10).

Values are the **chart-displayed readings**, not a raw Dhan export. Some charts displayed one decimal place and some drawn horizontal lines differed slightly from the candle readings. Do not create complete provider fixtures by filling in candles that were never recorded.

## 1 Sun Pharma passing setup and user designated success

**Instrument:** NSE cash equity, `SUNPHARMA`  
**Date:** 13 November 2026

The four reference candles include the morning session high in the 10:40 candle. Its displayed high is **1,915.00**, and its displayed low is **1,910.00**. The observed four-candle range is **1,910.00 to 1,915.00**.

| Candle | Open | High | Low | Close |
|---|---:|---:|---:|---:|
| 10:40 | 1,910.50 | 1,915.00 | 1,910.00 | 1,913.00 |
| 10:45 | 1,912.90 | 1,913.60 | 1,910.20 | 1,911.00 |
| 10:50 | 1,910.30 | 1,911.70 | 1,906.50 | 1,906.50 |
| 10:55 | 1,906.60 | 1,907.40 | 1,901.40 | 1,901.40 |

The 10:50 candle closes below the reference low when it finishes at 10:55. The next candle, starting at **10:55**, provides the short-entry reference **1,906.60** at its open. Price subsequently continues downward in the inspected chart.

**Expected scanner result:** qualifying setup, downward breakout, entry identified at 10:55. The user called this a success example. No calculated exit price, stop-loss hit, or profit amount is established.

**Fixture reconciliation:** the drawn upper horizontal line was **1,915.10**, while the inspected 10:40 high displayed **1,915.00**. Use actual provider candle values in the eventual engine, not hand-drawn line coordinates. The complete 09:15-to-entry candle sequence still needs to be supplied as a fixture.

## 2 Asian Paints passing setup and user designated failure

**Instrument:** NSE cash equity, `ASIANPAINT`  
**Date:** 6 November 2026

The observed reference group includes the morning high in the 10:30 candle, displayed at **2,514.00**. The inspected 10:45 candle's low is **2,500.90**. The marked chart range was approximately **2,500.60 to 2,514.00**; its lower drawn line is not identical to that candle reading.

| Candle | Open | High | Low | Close |
|---|---:|---:|---:|---:|
| 10:30 | 2,513.00 | 2,514.00 | 2,507.40 | 2,509.00 |
| 10:45 | 2,503.00 | 2,504.70 | 2,500.90 | 2,501.80 |
| 10:50 | 2,500.80 | 2,501.10 | 2,495.00 | 2,495.70 |
| 10:55 | 2,495.70 | 2,499.00 | 2,494.10 | 2,494.40 |

The 10:50 candle closes below the observed lower range area. Entry under the taught next-candle rule is the **10:55** candle open, displayed at **2,495.70**. The next candle also makes a lower low; requiring that extra lower low is not part of the entry rule.

Later, the chart consolidates and returns above the marked upper level of **2,514.00**. The user explicitly described the model as failing after the next-candle entry.

**Expected scanner result:** qualifying setup and entry identified. Retain **user-designated failure** as the teaching label. Do not relabel it `not_qualified`, assume a stop price, compute a loss without exit rules, or claim that candle color caused the failure.

**Fixture reconciliation:** complete reference candles, including 10:35 and 10:40, must be acquired to confirm the exact four-candle minimum. Preserve the **2,500.60 drawn line versus 2,500.90 inspected low** discrepancy for review. The initial lower close is below both displayed levels, but that does not justify inventing the missing raw dataset.

## 3 L and T failing the setup qualification

**Instrument:** NSE cash equity, `LT`, Larsen & Toubro  
**Date:** 13 November 2026

| Reference candle | High | Low |
|---|---:|---:|
| 10:30 | 4,174.90 | 4,162.60 |
| 10:35 | 4,176.70 | 4,168.60 |
| 10:40 | 4,178.60 | 4,169.20 |
| 10:45 | 4,184.70 | 4,176.10 |

The reference range is **4,162.60 to 4,184.70**. Before this group:

- The **09:50** candle has a displayed high of **4,193.60**, above the reference high.
- The **09:20** candle has a displayed low of **4,127.60**, below the reference low.

Neither session extreme is created by the four reference candles. The setup therefore fails the first condition.

**Expected scanner result:** `not_qualified`, with the earlier high and low supplied as evidence. No strategy breakout or entry should be presented as actionable under this setup, even if price later crosses its range. This is a **setup rejection**, distinct from Asian Paints' failure after a valid entry.

## 4 HCL Technologies passing setup and confirmed entry

**Instrument:** NSE cash equity, `HCLTECH`  
**Date:** 13 November 2026

| Reference candle | Open | High | Low | Close |
|---|---:|---:|---:|---:|
| 10:30 | 1,390.80 | 1,394.20 | 1,390.60 | 1,393.90 |
| 10:35 | 1,394.30 | 1,396.70 | 1,394.30 | 1,395.20 |
| 10:40 | 1,395.40 | 1,396.00 | 1,393.00 | 1,394.00 |
| 10:45 | 1,393.80 | 1,394.70 | 1,393.00 | 1,394.60 |

The **10:35** candle creates the morning session high, **1,396.70**. The four-candle range is **1,390.60 to 1,396.70**.

| Later candle | Open | High | Low | Close | Meaning |
|---|---:|---:|---:|---:|---|
| 10:50 | 1,394.00 | 1,394.40 | 1,391.60 | 1,393.70 | Closes inside range |
| 10:55 | 1,393.70 | 1,394.30 | 1,391.20 | 1,391.20 | Closes inside range |
| 11:00 | 1,391.10 | 1,391.10 | 1,384.60 | 1,385.00 | First close below range |
| 11:05 | 1,384.90 | 1,385.00 | 1,383.20 | 1,383.80 | Entry candle |

The breakout candle starts at **11:00** and finishes at **11:05**. Entry is at the open of the candle starting at **11:05**, with displayed price **1,384.90**. That entry candle runs from 11:05 to 11:10. The user explicitly confirmed this timing as correct and asked for the logic to be preserved exactly.

**Expected scanner result:** `entry_identified`, short direction, breakout start 11:00, breakout end and confirmation 11:05, entry time 11:05, entry reference price 1,384.90. Stop-loss and exit values remain unavailable.

## 5 Synthetic conditions for future acceptance tests

These cases specify expected behavior; they are not test code or historical market claims. Unless a case says otherwise, assume valid continuous candles, a qualifying reference group, no unresolved ties or gaps, and a fixed range **100.00 to 110.00**. The price scale is illustrative.

| Case | Conditions | Expected behavior |
|---|---|---|
| A01 High qualifies | The four candles contain a new morning high, although their low is not the morning low | Setup qualifies; both extremes are not required |
| A02 Low qualifies | The four candles contain a new morning low, although their high is not the morning high | Setup qualifies |
| A03 Neither qualifies | Earlier morning high is above the reference high and earlier morning low is below the reference low | `not_qualified`; no strategy entry |
| A04 Wick above only | Later candle high 111.00, close 109.00 | No confirmed breakout; keep waiting |
| A05 Wick below only | Later candle low 99.00, close 101.00 | No confirmed breakout; keep waiting |
| A06 Close on boundary | Later close equals 110.00 or 100.00 exactly | No confirmed breakout |
| A07 Upward close | A later completed candle closes at 111.00 and its immediately following candle opens at 111.20 | Long entry at that next open, not at 110.00 or the breakout close |
| A08 Downward close | A later completed candle closes at 99.00 and its immediately following candle opens at 98.80 | Short entry at that next open |
| A09 Delayed breakout | Candles remain inside the range until a 12:00 candle closes below it at 12:05 | Entry at 12:05 next-candle open; do not require a 10:50 breakout |
| A10 Forming candle | Current candle trades outside but is not yet closed | No confirmed breakout |
| A11 No entry candle yet | Breakout has closed but the next candle open has not arrived | `awaiting_entry`; entry price unavailable |
| A12 Missing reference candle | 10:35 candle absent | `invalid_data`; do not form the range from three candles |
| A13 Missing morning candle | A required candle before 10:30 is absent | `invalid_data`; an earlier extreme cannot be ruled out |
| A14 Missing post-window candle | A candle between 10:50 and a proposed later breakout is absent | Cannot establish the first breakout; report invalid data |
| A15 Missing immediate next candle | Breakout present, next scheduled historical candle absent, later candles present | Do not skip to a later candle for entry |
| A16 Unknown exits | Setup and entry valid, risk rules still absent | Entry reported; stop loss, target, exit, and computed outcome unavailable |
| A17 Later reversal | Valid entry followed later by price crossing back through the range | Keep the original valid setup and entry; no invented invalidation or stop rule |
| A18 Later new extreme | After valid qualification, a later candle makes a new session extreme | Do not use future data to retroactively change qualification |
| A19 Candle color | A reference candle is red or green, with identical relevant highs and lows | Color alone does not change eligibility |
| A20 Repeated equal extreme | Reference high equals an earlier high, with no new low | `needs_rule_decision` until the tie policy is approved |
| A21 Entire gap beyond range | Later candle opens and remains beyond the range | Requires the unresolved gap policy; do not invent trade-through requirements |
| A22 Last session candle | Breakout exists but there is no next same-session candle | Under the proposed session policy, leave entry unavailable; no next-day substitution |
| A23 Batch with bad symbol | One stock qualifies, one rejects, and another cannot resolve | Keep all three per-stock results and preserve their distinct reasons |
| A24 No breakout all day | Complete historical session qualifies, but every later close stays inside or on the range | `no_breakout`; no entry |
| A25 Multiple breakouts | First confirmed breakout and a later opposite breakout both occur | Initial proposed scanner reports the first only; re-entry behavior awaits approval |

## 6 Conditions for promoting examples into fixtures

For each historical test, capture the resolved instrument, source, date, timezone, interval, retrieval time, and complete candle coverage from 09:15 through the required analysis end. Keep actual source precision and identify adjusted versus unadjusted prices where relevant.

Reconcile the Sun Pharma and Asian Paints drawing discrepancies before freezing exact numeric expectations. Record the approved expected qualification, range, first breakout, and next-candle open with each fixture. Keep the user's example outcome label separate from any computed outcome.

Do not fabricate missing candles, silently change the historical date, or substitute another exchange or contract to force a match.

## 7 Reconciliation with Dhan data on 15 November 2026

`scripts/reconcile_teaching_examples.py` compared every recorded chart value with Dhan's 5-minute candles for the same instrument, date, and start label. **20 of the 74 recorded values differ, each by at most 0.90**. This suggests the teaching charts came from a different data feed. Running the full engine on Dhan's complete candles gives the same decisions as the teaching:

| Example | Engine result on Dhan data | Chart reading |
|---|---|---|
| HCL Technologies, 13 Nov | `entry_identified`: session high 1,396.70 at 10:35, range 1,390.60 to 1,396.70, 11:00 breakout confirmed at 11:05, short entry at the **11:05 open 1,385.00** | Entry open 1,384.90 |
| Sun Pharma, 13 Nov | `entry_identified`: range 1,910.00 to 1,915.00, 10:50 close 1,907.00, short entry at the **10:55 open 1,906.50** | 10:50 close 1,906.50; entry open 1,906.60 |
| Asian Paints, 6 Nov | `entry_identified`: range **2,500.40** to 2,514.00 (the unrecorded 10:35 or 10:40 candle holds the low), short entry at the 10:55 open 2,495.70 | Inspected 2,500.90; drawn 2,500.60; entry open 2,495.70 |
| L&T, 13 Nov | `not_qualified`: earlier high 4,193.60 at 09:50 and earlier low 4,127.60 at 09:20 | Same extremes; reference high 4,184.70 (Dhan 4,185.00) |

The observation fixtures keep the chart readings unchanged as teaching evidence. Dhan values are not copied into the repository.

