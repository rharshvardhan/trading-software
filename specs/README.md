# Project specifications

All strategy specifications and acceptance examples are stored in this folder.

| Document | Purpose | Status |
|---|---|---|
| [SPEC.md](SPEC.md) | Original project contract, setup-and-entry rules, data requirements, interfaces, Dhan integration and UI additions | Version 0.2.0 is the implemented baseline; read the later direction clarification alongside it |
| [REVERSAL_DIRECTION_SPEC.md](REVERSAL_DIRECTION_SPEC.md) | Direction correction and later cancellation clarification, including Sun Pharma, Axis Bank and Adani Ports examples | Direction restriction **implemented** (section 10). Wrong-direction close cancellation **implemented** (sections 11 and 12) |
| [WICK_CANCELLATION_SPEC.md](WICK_CANCELLATION_SPEC.md) | Prohibited-side wick cancellation and teaching history; now explicitly confirmed as the third point for 09:45 SHORT and opposite LONG | Matches the implemented 09:45 SHORT and, since 16 November 2026, the implemented 09:45 LONG; other-window implementation scope is unchanged |
| [THREE_CANDLE_0945_REVERSAL_SPEC.md](THREE_CANDLE_0945_REVERSAL_SPEC.md) | Additional 09:45, 09:50, 09:55 reversal window; all other taught direction, close, entry and cancellation rules carry over | **Implemented** on 16 November 2026 at the user's request (its section 13); runs in every scan with the other windows |
| [THREE_CANDLE_0945_CONFIRMATION_SPEC.md](THREE_CANDLE_0945_CONFIRMATION_SPEC.md) | 09:45 SHORT first break, later confirming close, next-open entry, reference-high stop; third point: upper-wick breach before entry cancels | **Implemented**. The user explicitly retaught the third point; the latest doc update matches existing SHORT code. BEL 10:55 confirmation / 11:00 entry |
| [THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md) | Opposite LONG first high breach, later close above, next-open entry, reference-low stop; third point: lower-wick breach before entry cancels | **Implemented** on 16 November 2026 after the user's separate coding authorization (its section 12) |
| [THREE_CANDLE_0945_STOP_LOSS_SPEC.md](THREE_CANDLE_0945_STOP_LOSS_SPEC.md) | Initial stop-loss level for 09:45 only: SHORT uses the three-candle highest high; LONG uses the lowest low, including wick/body extremes | **Implemented** on 16 November 2026 at the user's request (its section 10). Stop-hit/exit execution remains undefined |
| [TWO_CANDLE_1050_REVERSAL_SPEC.md](TWO_CANDLE_1050_REVERSAL_SPEC.md) | Third window: 10:50 and 10:55; all previously taught qualification, direction, close, entry and cancellation rules carry over | **Implemented** on 16 November 2026 at the user's request (its section 13); runs in every scan with the other two windows |
| [HIGHEST_HIGH_60_PERCENT_TARGET_SPEC.md](HIGHEST_HIGH_60_PERCENT_TARGET_SPEC.md) | Morning comparison starts **09:15**; distance = (High - Low) x 0.60; SHORT = High - distance; LONG = Low + distance. CG Power SHORT target 829.39 | **Specification only; coding not authorized**. Measurement end cutoff and target execution remain open |
| [EXAMPLES.md](EXAMPLES.md) | Original Sun Pharma, Asian Paints, L&T and HCL teaching observations, acceptance cases and Dhan reconciliation | Historical evidence; directional expectations are qualified by the later direction specification |

The direction clarification takes precedence over the original unrestricted-direction wording. The user confirmed the trading explanation, then authorized coding on 15 November 2026; the correction is implemented.

**Latest 09:45 third point, explicitly confirmed:** After temporarily reserving cancellation for a separate explanation, the user taught it: **before SHORT entry, a high breach above the three-candle high cancels, including a wick**; apply the opposite to LONG: **a low breach below the three-candle low cancels, including a wick**. No completed outside close is required. The point is no longer pending. It matches the 09:45 SHORT code and, after the later LONG implementation, the 09:45 LONG code. No other reference window is changed.

For the revised 09:45 SHORT only, the first low breach (wick or close) is followed by a different later candle closing below the same reference low, then entry at the next open. Its confirmation need not be immediate, and its open is unrestricted. The user corrected the BEL teaching time to 10:55 confirmation and 11:00 entry. The engine, terminal, API and UI reflect this correction. The later-window entries retain their prior flow.

The user subsequently confirmed [the opposite 09:45 LONG rules](THREE_CANDLE_0945_LONG_CONFIRMATION_SPEC.md) and explicitly requested them in a spec: first high breach, different later close above, following-open entry and initial stop at group low. The user then explicitly taught the third point for SHORT and mirrored it for LONG: a lower-wick breach before LONG entry cancels. The user then authorized coding it, and the revised LONG entry/cancellation was implemented on 16 November 2026 through the same engine flow as the SHORT (its section 12).

The later three-candle variant uses the same rules with a 09:45/09:50/09:55 reference group, finalized at 10:00. It is a separate specification, implemented on 16 November 2026 (its section 13). At the user's request, every scan evaluates all windows side by side; their signals are never combined or ranked.

The third variant uses a 10:50/10:55 two-candle group, finalized at 11:00, compared with all earlier candles from 09:15 through 10:45. It was implemented on 16 November 2026 (its section 13); every scan now evaluates all three windows (09:45, 10:30, 10:50) independently.

The later stop-loss addition applies only to the 09:45 three-candle window and is documented separately. Its reference prices were implemented on 16 November 2026 (its section 10) and are reported only for 09:45 entries. The logic runs only when `STOP_LOSS_ENABLED=true` in `.env`. The other windows' stop losses and all target/exit execution rules remain undefined.

The existing target document now includes the user's later confirmation of both directions and the corrected **09:15** morning start: SHORT subtracts 60% of the high-low distance from the high; LONG adds it to the low. These are documented price-level formulas, not an implemented target or complete exit model. The measurement end cutoff and target execution remain open.

The operational setup guide remains in [docs/PROJECT_SETUP.md](../docs/PROJECT_SETUP.md). Compatibility links at the old specification and example paths preserve existing references without changing application or test code.
