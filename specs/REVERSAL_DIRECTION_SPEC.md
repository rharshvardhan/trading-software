# Four Candle Reversal: Direction Clarification

**Latest cancellation amendment, 16 November 2026:** [WICK_CANCELLATION_SPEC.md](WICK_CANCELLATION_SPEC.md) supersedes this document's close-only cancellation requirements: a prohibited-side wick before entry is sufficient to cancel. Entry confirmation still requires a permitted close. The amendment is specification only, with no coding authorization; sections 10–12 below preserve the earlier implementation history.

**Date:** 15 November 2026  
**Rule status:** The user confirmed the direction rule and later resolved cancellation on a wrong-direction candle close (section 11).  
**Document scope:** Specification, examples, the direction implementation record (section 10), the later cancellation clarification (section 11), and its implementation record (section 12).  
**Implementation authorization:** **Given by the user on 15 November 2026** ("implement it") for the direction implementation in section 10. The later cancellation clarification in section 11 was **authorized ("implement") and implemented on 15 November 2026** (section 12).

## 1 Purpose and relationship to the existing specification

This document records the user's correction to the direction of entries in the four candle reversal strategy. It supplements [the original specification](SPEC.md), especially R03, R06, R07 and decision D06. It takes precedence over the original statement that either boundary can trigger an entry regardless of which session extreme qualified.

Until 15 November 2026 the implementation permitted either breakout direction after qualification. The historical approval for version 0.2.0 did not authorize this correction by itself. The user then authorized coding it, and the engine, API, terminal, and UI now enforce it (section 10).

## 2 Candle definitions and fixed reference range

- Market: NSE cash equities.
- Interval: five minutes, with each candle labeled by its start time.
- Timezone: Asia/Kolkata (IST).
- Reference candles: **10:30, 10:35, 10:40 and 10:45**, on the requested trading date.
- All four reference candles must finish; the 10:45 candle closes at **10:50**.
- Reference high: the highest high of the whole four-candle group, including wicks.
- Reference low: the lowest low of the whole four-candle group, including wicks.

Compare the reference group with all earlier candles from **09:15 through 10:25**. The resulting qualification window is 09:15 through the completed 10:45 candle. The comparison is not limited to the single 09:15 candle, and entry boundaries are not taken from that candle.

The four-candle range stays fixed after it is formed. A later consolidation does not expand it. Qualification uses information available at 10:50, not the eventual full-day high or low.

## 3 Confirmed direction rule

| Reference-group qualification | Boundary that must be broken and closed beyond | Permitted entry | Direction that must not produce an entry under that qualification alone |
|---|---|---|---|
| The group makes a new morning session **high**, but not a new session low | **Below the reference low** | **SHORT**, at the next candle's open | An upward break must not produce a LONG |
| The group makes a new morning session **low**, but not a new session high | **Above the reference high** | **LONG**, at the next candle's open | A downward break must not produce a SHORT |
| Neither side makes or matches a morning session extreme | No qualifying reversal setup | No entry | Either range crossing must not manufacture a qualified setup |

In words: **session high -> break the four-candle low -> SHORT; session low -> break the four-candle high -> LONG.** Both extremes do not have to qualify. A tie with an earlier morning extreme and a group that qualifies on both sides require the decisions recorded in section 8.

This is the essential correction: qualification determines the permitted reversal direction. Merely obtaining a qualifying setup is not permission to take an entry in either direction.

## 4 Breakout confirmation and entry timing

1. Wait until the reference group is complete and its qualification is known.
2. Observe later candles in time order. A qualifying break can occur at 10:50, 11:00, 12:00, or later within the same session. There is no newly introduced fixed breakout time or consolidation deadline.
3. For a high-qualified SHORT setup, a completed candle must close **strictly below** the reference low. For a low-qualified LONG setup, a completed candle must close **strictly above** the reference high.
4. A wick crossing alone, a close exactly on the boundary, or a still-forming candle does not confirm entry.
5. The breakout candle must finish. Entry is the **open of the immediately following five-minute candle**.
6. Do not wait for the entry candle to close or require it to break another high or low. Do not skip a missing next candle and substitute a later candle.

For example, a 10:55 breakout candle runs from 10:55 to 11:00. Its confirmation occurs at 11:00, and the entry reference is the open of the candle starting at **11:00**.

## 5 Verified example: Sun Pharma, 13 November 2026

**Source:** Dhan Data API results inspected in the user's running scanner app on 15 November 2026. This records the displayed evidence; it is not a complete raw-data fixture.

| Item | Observed value |
|---|---|
| Qualifying side | New morning session **high** |
| Extreme candle | **10:40** |
| Reference/session high | **INR 1,915.00** |
| Four-candle reference low | **INR 1,910.00** |
| Four-candle range | **INR 1,910.00 to INR 1,915.00** |
| Breakout candle start | **10:50** |
| Breakout close | **INR 1,907.00**, below 1,910.00 |
| Breakout completion | **10:55** |
| Entry candle start | **10:55** |
| Direction | **SHORT** |
| Dhan entry open | **INR 1,906.50** |

The group makes the morning high, so only the downward reversal is eligible under this qualification. The 10:50 candle closes below the group's low. The next candle's open, at 10:55, is the entry reference. An upward break of 1,915.00 would not justify a LONG merely because the high side qualified.

The earlier teaching chart displayed an entry open of **1,906.60**, and a breakout close of **1,906.50**. Preserve those earlier chart readings in [EXAMPLES.md](EXAMPLES.md); do not silently replace them with Dhan values. The direction and entry time agree across the two recorded sources.

The user designated Sun Pharma a success example. This label is not a computed profit result because stop-loss and exit rules are still undefined.

## 6 Verified example: Axis Bank, 12 June 2026

**Source:** The user directed the check to the running scanner at localhost. Axis Bank cash equity was selected with trading date **2026-06-12**. The Dhan-backed result and expanded candle table were inspected on 15 November 2026. All times below are IST; prices are INR.

### Observed reference and entry sequence

| Candle start | Open | High | Low | Close | Role |
|---|---:|---:|---:|---:|---|
| 10:30 | 1,322.60 | 1,323.80 | 1,322.00 | 1,322.70 | Reference |
| 10:35 | 1,322.70 | 1,323.10 | 1,321.10 | 1,322.00 | Reference |
| 10:40 | 1,322.00 | 1,322.30 | 1,318.70 | 1,320.00 | Reference |
| 10:45 | 1,320.00 | 1,320.50 | **1,318.50** | 1,319.90 | Reference; new morning low |
| 10:50 | 1,319.90 | 1,322.80 | 1,318.60 | 1,322.00 | Closes inside the fixed range |
| 10:55 | 1,322.00 | 1,324.60 | 1,322.00 | **1,324.50** | Closes above the reference high |
| 11:00 | **1,324.50** | 1,324.80 | 1,323.00 | 1,323.40 | Entry candle; use its open |

The earlier 09:15-10:25 candles have a lowest low of **1,321.30**, at 10:15. Therefore, the reference low **1,318.50** at 10:45 is a new morning low. The earlier high is **1,334.00**, above the reference high, so this example qualifies on the low side only.

The four-candle range is **1,318.50 to 1,323.80**. The 10:50 close remains inside it. The 10:55 candle closes at **1,324.50**, strictly above **1,323.80**, and finishes at **11:00**. Entry is therefore **LONG at the 11:00 candle open, 1,324.50**. Its later close of 1,323.40 does not change the already-established entry open.

A downward break of 1,318.50 would not justify a SHORT under this low-only qualification. No profit, stop-out, or success/failure label has been established for this Axis Bank example.

These are observed values, not an invented complete historical fixture. The displayed table contained the full session, but no full candle export is added by this documentation change.

## 7 Acceptance cases for a later authorized implementation

These are specification cases only. They do not add or change test code. Except where noted, assume valid continuous data, a fixed reference range of **100.00 to 110.00**, a started next candle, and no unresolved gap or tie.

| Case | Conditions | Required behavior |
|---|---|---|
| DIR-01 High-to-low reversal | Only the high side qualifies; a later completed candle closes at 99.00; the next candle opens at 98.80 | SHORT at the next open, 98.80 |
| DIR-02 Reject high-to-high entry | Only the high side qualifies; before any entry, the first outside close is 111.00 | Cancel this SHORT setup; no LONG entry and no later entry under this setup (sections 11 and 12; implemented) |
| DIR-03 Low-to-high reversal | Only the low side qualifies; a later completed candle closes at 111.00; the next candle opens at 111.20 | LONG at the next open, 111.20 |
| DIR-04 Reject low-to-low entry | Only the low side qualifies; before any entry, the first outside close is 99.00 | Cancel this LONG setup; no SHORT entry and no later entry under this setup (sections 11 and 12; implemented) |
| DIR-05 No morning extreme | Earlier morning high is above 110.00 and earlier morning low is below 100.00 | Not qualified; no strategy entry from either crossing |
| DIR-06 Wick only | High-only setup: low reaches 99.00 but close is 101.00; or low-only setup: high reaches 111.00 but close is 109.00 | No confirmed directional breakout |
| DIR-07 Close on boundary | Close is exactly 100.00 for a SHORT setup, or exactly 110.00 for a LONG setup | No confirmed directional breakout |
| DIR-08 Forming breakout | Price crosses the permitted boundary but that candle has not finished | Wait; no confirmed breakout |
| DIR-09 Delayed reversal | After consolidation, the 12:00 candle makes the first permitted breakout close and finishes at 12:05 | Entry at the 12:05 next-candle open, without an extra confirmation candle |
| DIR-10 Entry candle reverses | Valid directional breakout followed by an entry candle that later closes back in the range | Entry remains at its open; its close is not an entry filter |
| DIR-11 Missing next candle | Breakout exists, but the immediately following required historical candle is absent | Entry price unavailable; do not substitute a later candle |
| DIR-12 Sun Pharma | The observed Dhan values in section 5 | SHORT, 10:50 breakout, 10:55 entry open 1,906.50 |
| DIR-13 Axis Bank | The observed Dhan values in section 6 | LONG, 10:55 breakout, 11:00 entry open 1,324.50 |
| DIR-14 Valid entry later fails | A qualifying directional reversal entry is followed by adverse price movement | Preserve the valid entry; calculate no outcome without exit rules |

Both observed examples also produced the expected direction in the original unrestricted engine. They illustrate the intended rule but do not by themselves prove that the direction restriction is enforced. DIR-02 and DIR-04 now also record the later cancellation decision in section 11, and the tests expect cancellation for those crossings (section 12).

## 8 Decisions not settled by this clarification

| Open item | Boundary of the confirmed rule |
|---|---|
| Both sides qualify | When the group makes both a new morning high and a new morning low, direction priority and which signal to report are not newly settled. Do not choose a priority silently. |
| Equal earlier extreme | Matching an earlier morning high or low without making a new extreme remains the original open tie policy. |
| Entire breakout candle beyond the range | The original unresolved gap policy remains open. |
| Re-entry or multiple trades | No new authorization for another entry, an opposite trade, or re-entry after failure. |
| Session end and missing provider candles | Keep the original coverage and same-session boundaries; do not fabricate missing candles or redefine market hours. The Dhan session-tail observations in the original specification apply to the observed dates, not automatically to every date. |
| Stop loss, target and exit | Still undefined. Leave stop loss, targets, exit time, exit price, and profit or loss unavailable. Do not infer a stop from the other range boundary. |

These open items do not change the two unambiguous examples above. Any later implementation must make unresolved cases explicit instead of inventing trading rules.

**Resolved later:** the wrong-direction-first question is no longer an open trading rule. Section 11 records the user's decision to cancel on a completed close strictly beyond the prohibited boundary, with wick-only crossings ignored. It is implemented (section 12).

## 9 Authorization record

| Item | Status |
|---|---|
| User confirmed the explained high-to-low SHORT and low-to-high LONG rule | **Yes**, in this chat on 15 November 2026 |
| User requested a populated Markdown specification | **Yes** |
| User requested one folder containing the specifications | **Yes**, `specs/` |
| User authorized coding this correction | **Yes**, in chat on 15 November 2026: "implement it" (after first withholding authorization) |
| Application, test, API, provider or UI implementation changed | **Yes**, on 15 November 2026; see section 10 |

**Implementation:** the direction correction was completed on 15 November 2026 under the user's authorization (section 10). The remaining section 8 items stay open. The later wrong-direction cancellation in section 11 was implemented on 15 November 2026 (section 12).

## 10 Implementation record

**Authorization:** in chat on 15 November 2026, the user referred to this file and wrote "implement it".

| ID | Implemented behavior |
|---|---|
| I1 Permitted direction | Derived from the strictly new extremes of the 09:15-10:45 comparison (SPEC.md D04): a new high only gives SHORT; a new low only gives LONG. Reported as `qualification.permitted_signal`. |
| I2 Directional confirmation | As in 0.2.0, the engine examines the first completed candle that closes strictly outside the range, on either side. If it closes on the permitted side, the gap check (D05) and the next-candle entry apply unchanged. |
| I3 Wrong direction first (section 8) | If that first close is on the prohibited side, the result is `needs_rule_decision` with code `wrong_direction_first`. The crossing is shown with `breakout.direction_permitted = false`, no entry is reported, and no later candle is searched. Wick-only crossings and boundary closes on the prohibited side are ignored, as before. |
| I4 Both sides (section 8) | A group that makes both a new high and a new low gives `needs_rule_decision` with code `both_sides_qualified`. No breakout is searched for. |
| I5 Tie on the other side (section 8) | A new extreme on one side with an exact tie on the other gives `needs_rule_decision` with code `equal_repeated_extreme`. If the open tie policy counted the tie, the setup would qualify on both sides, so the direction cannot be fixed. This replaces D04's statement that such a tie "does not matter", which predates the direction rule. |
| I6 Unchanged | Coverage, closed candles, session boundaries, the gap policy (the prohibited direction is checked first), first signal only, and null risk and exit fields. |
| I7 Interfaces | The API adds `qualification.permitted_signal`, `breakout.direction_permitted`, and the two new rule codes. The terminal `--details` view prints the permitted direction. The web UI shows "SHORT setup" or "LONG setup", explains each decision, and labels a prohibited close "Wrong-way close". The synthetic demos were rebuilt: SYN-LONG (DIR-03), SYN-SHORT (DIR-01), SYN-WRONGWAY (DIR-02), and SYN-BOTHSIDES are new or redefined, and the gap and last-candle demos moved to the permitted side. |

**Verification:** 216 automated tests pass. They cover DIR-01 to DIR-11 and DIR-14 on synthetic data, and DIR-12 and DIR-13 on the recorded observations; `axisbank-2026-06-12.json` holds only the section 6 values, with nothing filled in. A live Dhan scan on 15 November 2026 returned Sun Pharma, 13 November: SHORT, 10:50 breakout, 10:55 entry at 1,906.50. It returned Axis Bank, 12 June: LONG, 10:55 breakout, 11:00 entry at 1,324.50. HCL Technologies, TCS, and Infosys on 13 November were unchanged short entries.

The I3 implementation above describes the current code and the verification before the later decision in section 11. Section 11 supersedes its rule-question outcome as a specification requirement; it does not claim that cancellation has already been coded.

## 11 Later clarification: wrong-direction close cancels the setup

**Confirmed by the user:** 15 November 2026, while explaining the Adani Ports result. The user said that breaking farther below a low-qualified group fails that setup, and breaking farther above a high-qualified group likewise fails it. When asked whether a wick was sufficient, the user explicitly chose **candle close, not wick alone**.

**Status:** trading rule confirmed, recorded, and implemented on 15 November 2026 after the user wrote "implement" (section 12).

### Cancellation rule before entry

After the four reference candles are complete and the setup has a permitted direction, inspect subsequent completed candles in order. The first close strictly outside the fixed range decides whether to confirm the permitted breakout or cancel the setup:

| Setup | Permitted breakout close | Cancelling close |
|---|---|---|
| New morning low -> LONG | Close strictly above the four-candle reference high | Close strictly below the four-candle reference low |
| New morning high -> SHORT | Close strictly below the four-candle reference low | Close strictly above the four-candle reference high |

- A cancelling close means the **setup failed before entry**. Do not enter in the prohibited direction, and do not keep waiting for a later permitted reversal under that same setup on that date.
- Keep the original four-candle range fixed. Do not recalculate it to revive the cancelled setup, restart the search after the cancelling candle, or manufacture a re-entry.
- A wick beyond the prohibited boundary does not cancel the setup if its close is inside or on the range. Continue waiting for a decisive close.
- A close exactly on a boundary is not strictly outside and does not cancel. A still-forming candle cannot establish cancellation.
- If the permitted breakout is confirmed first, its entry remains the immediately following candle's open under the existing rules. A later prohibited-side close must not retroactively erase that entry or be treated as a stop-loss or exit; those risk rules are still undefined.
- The remaining open rules for ties, both sides qualifying, and gaps on a permitted breakout are not resolved by this decision.

### Adani Ports example supplied by the user

The user pasted the following scanner result. Its trading date was not included, so no date or complete historical fixture is invented here:

| Item | Supplied value |
|---|---|
| Qualification | New morning low **1,916.70**, at **10:40** -> LONG setup |
| Fixed four-candle range | **1,916.70 to 1,920.00** |
| First outside close | **10:55** candle closes at **1,916.20** |
| Relation to cancelling boundary | **1,916.20 < 1,916.70** |
| Cancellation confirmed | At **11:00**, when the 10:55 five-minute candle finishes |
| Required result under this clarification | **Setup cancelled: wrong-direction candle close. No entry.** |

This LONG setup needs an upward close above 1,920.00, but a downward close below 1,916.70 occurs first. Therefore the setup is cancelled. A later close above 1,920.00 must not revive it. This is setup rejection before entry, not a computed trading loss.

Before section 12 the code showed the now-resolved cancel-versus-wait question; it now explains the cancellation instead. The specific API state and presentation changes belong to that later implementation; this document does not silently redefine `not_qualified` or an existing result state.

### Acceptance cases for the cancellation update

These are specification cases, not new executable tests. Assume valid data, a reference range of **100.00 to 110.00**, one unambiguous qualifying side, and no unresolved permitted-breakout gap.

| Case | Sequence | Expected behavior |
|---|---|---|
| CAN-01 LONG cancellation | Low-only qualification; first outside close is 99.00 | Cancel the LONG setup; no entry |
| CAN-02 SHORT cancellation | High-only qualification; first outside close is 111.00 | Cancel the SHORT setup; no entry |
| CAN-03 LONG wick only | Low-only qualification; later low is 99.00 but close is 101.00 | Not cancelled; keep waiting |
| CAN-04 SHORT wick only | High-only qualification; later high is 111.00 but close is 109.00 | Not cancelled; keep waiting |
| CAN-05 Boundary close | LONG closes at 100.00, or SHORT closes at 110.00 | Not cancelled by that candle |
| CAN-06 Forming candle | Price trades beyond the cancelling boundary before its candle has closed | No confirmed cancellation yet |
| CAN-07 No revival | A cancelling close is followed by a later close beyond the permitted boundary | Preserve cancellation; no later entry under that setup |
| CAN-08 Valid entry already exists | The permitted breakout occurs first, the next candle supplies entry, and only later a prohibited-side close occurs | Preserve the original entry; do not invent an exit or a loss |
| CAN-09 Adani Ports | The supplied 10:55 close is 1,916.20, below the LONG setup's fixed low of 1,916.70 | Cancel at 11:00; no entry; no cancel-versus-wait question |

## 12 Cancellation implementation record

**Authorization:** in chat on 15 November 2026, the user referred to this file again and wrote "implement", after section 11 was added.

| ID | Implemented behavior |
|---|---|
| C1 New result state | `setup_cancelled` means the setup qualified, had a permitted direction, and failed before entry. The result keeps the qualification and reference evidence, reports `setup_qualified: true`, and leaves the entry `null`. It is not `not_qualified`, a stop, an exit, or a computed loss. |
| C2 Cancelling close | As in section 10, the engine examines the first completed candle that closes strictly outside the fixed range. If it is on the prohibited side, the result is `setup_cancelled`, confirmed when that candle closes. This is checked before the gap policy, which applies only to permitted breakouts. |
| C3 Evidence | A new `cancellation` object (side, boundary, candle, close, confirmation time) reports the cancelling candle. `breakout` stays `null`, because no permitted breakout occurred. |
| C4 Not cancelling | Wick-only crossings, closes exactly on a boundary, and still-forming candles do not cancel, unchanged from earlier behavior. |
| C5 No revival or re-search | After a cancellation, no later candle is examined, so a later permitted close cannot revive the setup. After a confirmed entry, later candles are not examined, so a later prohibited close cannot erase the entry. |
| C6 Removed | The `wrong_direction_first` rule question (section 10, I3) no longer exists. Both sides qualifying, ties, and gaps on a permitted breakout remain rule decisions. |
| C7 Interfaces | The terminal shows "Cancelled" and the cancelling candle. The web UI shows a "Setup cancelled" badge in the No trade group and "HH:MM cancelled" in the Breakout column; the checklist explains the wrong-direction close, and the chart marks the cancelling candle. The `SYN-WRONGWAY` demo is now CAN-02 plus CAN-07. |

**Verification:** 221 automated tests pass. They cover CAN-01 to CAN-08 on synthetic data and CAN-09 (Adani Ports) on the supplied numbers only; no date was supplied, so no fixture was created. The cancelled result was also rendered and checked in the web UI.

