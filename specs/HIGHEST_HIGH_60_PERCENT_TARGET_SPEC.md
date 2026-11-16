# 60% High-Low Target Specification: SHORT and LONG

**Source:** The user's CG Power explanation, supplied prices, and later explicit confirmation of both directional target formulas and the 09:15 start time.  
**Context:** The example refers to the **10:50 and 10:55** candles on a five-minute chart.  
**Measurement start:** **09:15 IST — காலை ஒன்பது மணி பதினைந்து நிமிடம்.**  
**Scope:** Record the confirmed target calculation separately from entry-direction and stop-loss rules.  
**Status:** **Specification only. No implementation authorization has been given for this target addition.**

## 1 Confirmed explanation

The user described these steps:

1. Start the morning high-low comparison at **09:15 on the selected trading date**. The user corrected the spoken time and explicitly confirmed **09:15**, not 09:45.
2. Identify the selected highest high and lowest low from the eligible morning candles beginning at 09:15. In the original CG Power example, the selected highest high occurs in the **10:50/10:55** reference group. The end cutoff for automated selection is addressed in section 4.
3. Subtract the selected low from the selected high to obtain the full high-to-low price distance.
4. Take **60% of that distance**.
5. For a **SHORT** trade, measure that amount **downward from the highest high**: subtract the 60% distance from H.
6. For a **LONG** trade, measure that amount **upward from the lowest low**: add the 60% distance to L.

The user confirmed both anchors: the highest high for SHORT and the lowest low for LONG. The calculation does not use the entry price as its anchor.

This document now records **both** the downward SHORT target and the upward LONG target. Existing entry-direction rules in [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md) remain unchanged: defining a LONG target does not turn a high-qualified SHORT setup into a LONG entry. Which windows receive target outputs in the scanner remains subject to a later implementation request; documenting the formulas does not change the running application.

## 2 Definitions and formula

| Symbol | Meaning |
|---|---|
| H | The selected highest-high price from the eligible morning candles beginning at 09:15 |
| L | The selected lowest-low price from the eligible morning candles beginning at 09:15 |
| R | Full measured price distance: **H - L** |
| D | Target distance: **R x 60 / 100**, or **R x 0.60** |
| SHORT target | Target price measured down from H: **H - D** |
| LONG target | Target price measured up from L: **L + D** |

**Target distance = (High - Low) x 0.60**

**SHORT target = High - [(High - Low) x 0.60]**

**LONG target = Low + [(High - Low) x 0.60]**

Taking 60% means multiplying the high-low distance by 0.60. Do not divide the distance by 0.60, apply 60% to the entire stock price, or substitute a percentage of entry price or stop-loss risk.

The target distance is a price movement in points. The target price is an absolute price level. Keep these two quantities distinct in any future implementation or presentation.

## 3 CG Power example supplied by the user

**Instrument:** CG Power & Industrial Solutions Ltd, NSE cash equity (`CGPOWER`).  
**Chart:** Five-minute candles. The attached screenshot's selected candle is labeled **Friday, 13 November 2026, 10:55**.  
**Evidence:** The user's attached chart and explicitly supplied **High 841.90, Low 821.05**. This is a teaching observation, not a complete provider candle export or a verified trade fill.

Use the prices explicitly given by the user for this example:

| Step | Calculation | Result |
|---|---|---:|
| Selected high | H | **841.90** |
| Selected low | L | **821.05** |
| Full distance | 841.90 - 821.05 | **20.85 points** |
| 60% distance | 20.85 x 0.60 | **12.51 points** |
| SHORT target from the highest high | 841.90 - 12.51 | **829.39** |
| LONG formula applied to the same supplied levels | 821.05 + 12.51 | **833.56** |

**The original downward CG Power target calculation is INR 829.39.** Applying the now-confirmed LONG formula to the same two prices gives **INR 833.56**. The second result is an arithmetic illustration only, not a claim that the attached CG Power chart has a valid LONG setup or trade.

The lower drawn horizontal label in the screenshot displays **821.00**, but the user explicitly supplied **821.05**. Preserve the user's stated input for this calculation; do not replace it with the rounded/different drawn-line label or a misheard spoken value.

No entry price, target hit, exit time, actual exit fill or profit has been established by these two supplied prices. Do not invent those results from this arithmetic or the screenshot.

## 4 Selecting high and low in a future automated scan

The illustrated high belongs to the 10:50/10:55 reference group in [TWO_CANDLE_1050_REVERSAL_SPEC.md](TWO_CANDLE_1050_REVERSAL_SPEC.md). The user's explanation compares that high with the morning beginning at 09:15. The existing setup qualification must still be checked; a target formula cannot qualify an otherwise invalid setup.

The user has now explicitly confirmed that the morning comparison **begins at 09:15**. H and L refer to the selected morning highest high and lowest low from that start. This is not a comparison that begins at 09:45, and it does not restrict the low to the 09:15 candle alone or automatically to just the 10:50/10:55 candles. The user supplied **821.05** as L for the CG Power example.

**Still to confirm for automation:** the end cutoff of the morning measurement interval and when H/L are frozen for target calculation. The start is already settled as **09:15**; do not ask again whether it starts at 09:45. Do not silently choose entry time, breakout time, reference-window completion, or eventual session end as the cutoff. The two formulas and supplied CG Power arithmetic are established without choosing that remaining timing detail.

Do not use an eventual full-day low or candles formed after a required decision time to calculate a historical target. If the selected low cannot be established from the user's approved rule and available data, report that missing rule/data rather than fabricating it.

Use actual candle extremes, including wicks, when candle highs/lows are the selected source. Preserve decimal price precision. This document adds no price buffer, offset, exchange-tick rounding policy or adjustment to force a target onto a desired price.

## 5 Relationship to entries, cancellation and stop loss

- The SHORT anchor is H and the LONG anchor is L. A different entry price does not change the respective target when H and L stay the same.
- The original qualification, permitted direction, candle-close breakout, next-candle-open entry and pre-entry cancellation rules are unchanged.
- Computing a target reference level does not place an order or create a trade for a rejected, cancelled or unresolved setup.
- The [09:45 stop-loss specification](THREE_CANDLE_0945_STOP_LOSS_SPEC.md) is a separate rule for a different window. It does not define the target formula's L or authorize a stop loss for the 10:50 window.
- The upward LONG-target formula is now explicitly confirmed: **L + D**. This later confirmation supersedes the earlier highest-high-only scope of this document.
- Formula confirmation does not change entry directions or authorize coding target outputs for any window. Preserve the existing independent per-window setup evaluation.

## 6 Target execution and other rules still open

This is a target **price-level** specification. It does not define:

- Whether a later touch, penetration or candle close counts as the target being hit.
- Execution/fill price, gap handling, partial exits or order behavior at the target.
- How to treat a target level already reached or passed before entry.
- Priority if a stop and target are both touched within the same candle.
- Trailing or recalculation, time exits, position size, profit/loss or computed success/failure.

Do not infer target-hit policy from the existing close-only breakout/cancellation rule or assume that knowing a target price makes an exit calculation possible. The existing scanner's outputs remain unchanged until implementation is separately authorized.

## 7 Acceptance cases for a later authorized implementation

These are written specification cases, not new executable tests. The synthetic inputs below are arithmetic examples only.

| Case | Inputs or condition | Required result |
|---|---|---|
| TG01 CG Power full distance | H = 841.90, L = 821.05 | R = **20.85** |
| TG02 CG Power 60% distance | R = 20.85 | D = **12.51** |
| TG03 CG Power SHORT target | H = 841.90, D = 12.51 | SHORT target = **829.39** |
| TG04 Synthetic levels, both directions | H = 110.00, L = 100.00 | R = 10.00; D = 6.00; SHORT target = **104.00**; LONG target = **106.00** |
| TG05 Entry-independent anchors | H and L are unchanged but the entry price differs | Same directional target; SHORT uses H - D and LONG uses L + D, not entry +/- D |
| TG06 Percentage operation | Calculate 60% of 20.85 | **12.51**; do not divide by 0.60 |
| TG07 User's supplied low | Screenshot line shows 821.00 but the user's input is 821.05 | Teaching example uses **821.05**, preserving the source distinction |
| TG08 Unknown measurement cutoff | Morning starts at 09:15 but its end cutoff is not established for another scan | Preserve the confirmed start; do not invent a cutoff, H or L |
| TG09 Entry directions | A target formula is available but setup qualification/direction does not allow that trade | No invented entry or change to the existing direction mapping |
| TG10 Target execution unknown | T is known and later candles trade near/across it | Do not invent a target hit, fill, exit, profit or trade outcome |
| TG11 LONG arithmetic on supplied levels | L = 821.05, D = 12.51 | LONG formula result = **833.56**; not a claim of an actual CG Power LONG trade |
| TG12 Correct morning start | Comparing eligible highs/lows for either target direction | Start at **09:15**, not 09:45, on the selected trading date |

## 8 Authorization and implementation record

| Item | Status |
|---|---|
| User explained the high-low distance and taking 60% | Yes |
| User explicitly anchored the target at the highest high | Yes |
| User explicitly confirmed LONG target from the lowest low upward | Yes: **L + D** |
| User explicitly corrected and confirmed the morning comparison start | Yes: **09:15**, not 09:45 |
| User supplied CG Power H = 841.90 and L = 821.05 | Yes |
| The original SHORT target calculation was explained back | Yes: D = 12.51, SHORT target = 829.39 |
| User requested a separate populated spec file | Yes |
| User requested this document to match the later confirmed explanation | Yes; update this existing file with both directions and the corrected start |
| Measurement end cutoff and full target execution policy settled | **No** |
| Coding this target addition authorized | **No** |
| Application, API, UI, terminal, test or fixture code changed by this task | **No** |

Store this document alongside the other specifications. Do not mark the target implemented, infer missing trading rules, or treat older implementation approvals as coding authorization for this addition.
