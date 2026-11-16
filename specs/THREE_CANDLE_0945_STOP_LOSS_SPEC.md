# 09:45 Three Candle Reversal: Initial Stop-Loss Level

**Latest 09:45 third point:** The user explicitly confirmed pre-entry wick cancellation for SHORT and its opposite LONG: high > group high cancels SHORT; low < group low cancels LONG. See [SHORT spec](THREE_CANDLE_0945_CONFIRMATION_SPEC.md) (implemented) and [LONG spec](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md) (implemented 16 November 2026). Under both, the stop is reported only after the later confirmation, for an identified or pending entry. Initial stop levels here are unchanged; pre-entry cancellation does not define stop-hit/exit execution after entry. The latest teaching turn changes documentation only.

**Applies to:** The **09:45, 09:50, 09:55** three-candle reversal only.  
**Source:** The user's explanation of the stop-loss reference, followed by the clarification that the full candle extreme is used whether it is formed by a wick or by the candle body/close.  
**Rule status:** Explained back to the user; the user then requested this specification.  
**Implementation status:** **Implemented on 16 November 2026** after the user wrote "code it" (section 10).

## 1 Scope and precedence

This document supplements [THREE_CANDLE_0945_REVERSAL_SPEC.md](THREE_CANDLE_0945_REVERSAL_SPEC.md). It defines the **initial stop-loss price level** for that variant, replacing the statement that its stop-loss level has not yet been taught.

The stop-level addition did not itself change qualification, reference ranges or entry rules. Read the latest linked entry specs for the current first-break/confirmation sequence; the third-point cancellation is now explicitly defined for both 09:45 directions. See [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md) for the shared direction and cancellation rules.

This new stop-loss rule does **not** apply automatically to the 10:30 four-candle or 10:50 two-candle strategies. Their stop-loss rules remain undefined until the user teaches them.

The existing setup-and-entry implementation approvals did not authorize coding this later stop-loss addition; the user's separate "code it" request did (section 10).

## 2 Reference candles and extreme prices

Use exactly the three five-minute candles starting at:

1. **09:45**
2. **09:50**
3. **09:55**

All times are Asia/Kolkata (IST), and these are candle **start labels**. The last reference candle finishes at **10:00**.

| Quantity | Definition |
|---|---|
| Three-candle highest high | Maximum of the three actual candle highs |
| Three-candle lowest low | Minimum of the three actual candle lows |

Use the full candle extremes, including upper and lower **wicks**. A candle's high or low may coincide with its body or close; that does not change how it is selected. Do not calculate the level from closes alone or body edges alone.

Valid OHLC data already records the wick/body extreme in `high` and `low`. A close cannot be above its valid candle high or below its valid candle low. The user's clarification therefore means using the actual high/low values, not inventing a separate close-based stop level.

The reference group must be complete and valid. Stop-loss calculation does not excuse missing reference data, a forming reference candle, or invalid OHLC. Keep source decimal precision; no buffer, percentage, tick offset or rounding adjustment was taught.

## 3 SHORT stop loss

Under the existing rule, the three-candle group makes a new morning session high relative to the earlier 09:15-09:40 candles, yielding an unambiguous SHORT setup. A later permitted close below the group low and the next-candle open establish entry.

**Initial SHORT stop loss = the highest high of the 09:45, 09:50 and 09:55 candles.**

Use the high of whichever reference candle holds that maximum. For example, if 09:50 holds the group's highest high, the stop-loss level is that candle's high. It is not that candle's low, close, or body top when its upper wick is higher.

This level equals the already-fixed three-candle **reference high**. A later breakout or entry candle does not become the stop-loss reference merely because it occurs nearer to entry.

## 4 LONG stop loss

Under the existing rule, the three-candle group makes a new morning session low relative to the earlier 09:15-09:40 candles, yielding an unambiguous LONG setup. A later permitted close above the group high and the next-candle open establish entry.

**Initial LONG stop loss = the lowest low of the 09:45, 09:50 and 09:55 candles.**

Use the low of whichever reference candle holds that minimum. For example, if 09:55 holds the group's lowest low, the stop-loss level is that candle's low. It is not that candle's high, close, or body bottom when its lower wick is lower.

This level equals the already-fixed three-candle **reference low**.

## 5 Direction summary and timing

| Qualification and entry direction | Initial stop-loss level |
|---|---|
| New morning high -> permitted downward breakout -> **SHORT** | **Three-candle reference high**, wicks included |
| New morning low -> permitted upward breakout -> **LONG** | **Three-candle reference low**, wicks included |

The reference level is known when the three candles finish at **10:00**. A later entry uses that same reference group; no trailing, replacement reference group or later-candle recalculation has been taught.

Computing a reference price does not create an entry, place an order or turn a rejected/cancelled setup into a trade. Existing qualification and entry requirements still apply. Equal highs or equal lows within the three reference candles give the same price level; this does not resolve the separate open rule about a tie with an earlier morning extreme.

## 6 Synthetic examples

All values below are **invented illustrations**, not historical stock data. Assume the relevant morning qualification and subsequent entry are valid under the main three-candle specification.

### SHORT example: upper wick sets the stop

| Reference candle | Open | High | Low | Close |
|---|---:|---:|---:|---:|
| 09:45 | 104.00 | 108.00 | 102.00 | 107.00 |
| 09:50 | 107.00 | **110.00** | 101.00 | 108.00 |
| 09:55 | 108.00 | 109.00 | 100.00 | 102.00 |

The group high is **110.00**, held by the 09:50 candle's upper wick. The group low is **100.00**. With a valid SHORT entry at a later next-candle open of **98.80**, the initial stop-loss level is **110.00**.

Using the maximum close, **108.00**, would be incorrect. Do not add an offset above 110.00 or use the entry/breakout candle's high instead.

### LONG example: lower wick sets the stop

| Reference candle | Open | High | Low | Close |
|---|---:|---:|---:|---:|
| 09:45 | 96.00 | 100.00 | 94.00 | 95.00 |
| 09:50 | 95.00 | 97.00 | **90.00** | 92.00 |
| 09:55 | 92.00 | 98.00 | 91.00 | 96.00 |

The group low is **90.00**, held by the 09:50 candle's lower wick. The group high is **100.00**. With a valid LONG entry at a later next-candle open of **101.20**, the initial stop-loss level is **90.00**.

Using the minimum close, **92.00**, would be incorrect. Do not add an offset below 90.00.

## 7 Stop-loss level versus stop-hit and exit rules

The user has established **where the initial stop-loss level comes from**. The wick/body/close clarification in this explanation identifies the full reference-candle extreme used for that level.

It does not by itself specify how a later candle triggers a stop, the execution price, or a complete exit model. Those details remain for the user's teaching:

- Whether a later touch, penetration or completed close triggers a stop; treatment of equality at the stop level.
- Stop activation within the entry candle and intrabar event ordering.
- Gaps through the stop and any execution/fill-price assumptions.
- Profit targets, trailing stops, partial exits, time exits and position sizing.
- Computed exit time, exit price, profit/loss, and success/failure classification.

Do not infer the stop-hit policy from the existing **close-only breakout/cancellation** policy, and do not assume a touch-triggered policy from the fact that reference wicks set the level. An initial stop-loss price can be defined without enough rules to compute an exit.

The user has now explicitly taught the third point in both 09:45 directions: a prohibited-side wick breach cancels before entry. This is independent of stop-hit or exit execution after entry, which remains undefined.

## 8 Acceptance cases for a later authorized implementation

These were written as requirements first; `tests/test_stop_loss_0945.py` now covers them (section 10). Assume an otherwise valid three-candle setup and entry where applicable.

| Case | Conditions | Required level or behavior |
|---|---|---|
| SL01 SHORT level | Reference highs are 108.00, 110.00, 109.00 | Initial stop loss **110.00** |
| SL02 LONG level | Reference lows are 94.00, 90.00, 91.00 | Initial stop loss **90.00** |
| SL03 Upper wick exceeds all closes | Group highest high is 110.00; highest close is 108.00 | SHORT stop **110.00**, not 108.00 |
| SL04 Lower wick below all closes | Group lowest low is 90.00; lowest close is 92.00 | LONG stop **90.00**, not 92.00 |
| SL05 Extreme coincides with close | Highest high/lowest low is also that candle's close | Use that same full extreme; do not require a wick |
| SL06 Any reference candle | The maximum high or minimum low belongs to 09:45, 09:50 or 09:55 | Select by price, not by a fixed candle position or color |
| SL07 Equal internal extremes | Two reference candles share the group's highest high/lowest low | Same stop price; no arbitrary candle preference changes the level |
| SL08 Later entry | Entry comes much later after consolidation | Initial level still comes from the original three reference candles |
| SL09 Different later extreme | A breakout/entry/later candle has a different high or low | Do not replace the taught initial reference level automatically |
| SL10 No buffer | The selected extreme is 110.00 or 90.00 | Use the exact source value; no added/subtracted offset |
| SL11 Invalid reference data | A reference candle is missing, forming or invalid | Retain the main specification's waiting/data handling; do not fabricate a level |
| SL12 Other variants | Result belongs to 10:30 four-candle or 10:50 two-candle strategy | This rule supplies no stop loss for that window |
| SL13 Undefined stop execution | A later candle trades near/across the level | Do not compute a stop hit, exit or loss without the still-undefined trigger/execution rules |
| SL14 Earlier tie/both sides | Entry direction depends on an unresolved qualification rule | Do not use the stop-loss addition to choose direction or create a trade |

## 9 Authorization and implementation boundary

| Item | Status |
|---|---|
| User taught initial SHORT stop as the three-candle highest high | Yes |
| User taught initial LONG stop as the three-candle lowest low | Yes |
| User clarified that the full extreme includes wick or body/close | Yes |
| User requested an explanation before writing the spec | Done; the user then requested the spec |
| User requested this Markdown specification | Yes |
| Coding this stop-loss addition authorized | **Yes**, on 16 November 2026: "code it" |
| Application, API, UI, terminal, tests or fixtures changed | **Yes**, see section 10 |

The user explicitly requested implementation on 16 November 2026 (section 10). Do not extend this stop-loss level to the other windows until the user teaches theirs.

## 10 Implementation record

**Authorization:** in chat on 16 November 2026, the user referred to this file and wrote "code it".

| ID | Implemented behavior |
|---|---|
| S1 Rule location | The 09:45 window definition carries `initial_stop_rule = reference_extreme`; the 10:30 and 10:50 windows carry none. The shared engine computes the level: SHORT uses the reference high and LONG the reference low of the 09:45, 09:50, and 09:55 candles (actual highs and lows, so wick or body extremes alike), at exact source precision with no buffer, never recalculated from later candles. |
| S2 When a level is reported | Only for a 09:45 result with an unambiguous direction and a trade: `entry_identified`, or `awaiting_entry` (permitted breakout confirmed, next-candle open not yet delivered). No level is reported for `waiting_for_breakout`, `setup_cancelled`, `not_qualified`, `needs_rule_decision`, `entry_unavailable_session_end`, missing or invalid data, or another window (sections 5 and 8: a level must not create a trade or choose a direction). |
| S3 Output | `risk.stop_loss` holds the level as a decimal string, and `risk.stop_loss_basis` explains it (for example "reference high of the 09:45-09:55 candles (09:50), wicks included"). `risk.reason` is "Initial stop-loss level per THREE_CANDLE_0945_STOP_LOSS_SPEC.md; stop-hit, target, and exit rules not yet defined". A 09:45 result without an entry says "No entry, so no stop loss". The other windows keep "Rules not yet defined". `targets`, `exit_time`, `exit_price`, `outcome`, and `profit_loss` stay `null` everywhere (section 7). The result's reason sentence also names the stop. |
| S4 Interfaces | The terminal's Stop loss column shows the price ("—" for a 09:45 result without an entry, "Not defined" for other windows), and `--details` prints the basis. The web UI shows the price with "range high" or "range low", adds an "Initial stop loss" step to the checklist, and draws a dashed stop line from the entry onward on the chart. No stop hit, exit, or loss is computed or drawn. |
| S5 On/off switch | Added at the user's request on 16 November 2026 ("create a value true or false in env for stop loss working logic"). `STOP_LOSS_ENABLED` in `.env` controls the logic: only `true` (also `1`, `yes`, or `on`, in any case) enables it. `false`, a blank value, a missing line, or an unrecognised value disables it. When disabled, no level is computed. The engine takes the switch as a parameter and never reads `.env` itself. 09:45 results report `risk.reason` "Stop-loss logic is turned off (STOP_LOSS_ENABLED is not true in .env)...". Scan responses and `/health` include `stop_loss_enabled`. The UI header shows "Stop loss on/off" and 09:45 stop cells show "Off", and the terminal footer states the switch. The switch is read when the app starts, so restart after changing it. |

**Verification:** `tests/test_stop_loss_0945.py` has 20 tests covering SL01-SL14 with this spec's section 6 values, plus pending-entry, session-end, API serialization, and `STOP_LOSS_ENABLED` switch checks; the full suite of 301 tests passes. A live Dhan scan for 13 November 2026 showed L&T's 09:45 SHORT entry at the 10:20 open (4,172.00) with initial stop loss 4,193.60, the 09:50 reference high, while its 10:30 and 10:50 results showed "Not defined".

