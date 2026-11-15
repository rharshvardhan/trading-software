# Project working instructions

## Specification first

- `SPEC.md` version 0.2.0 was approved by the user on 15 November 2026 for the **setup-and-entry implementation scope only** (see its section 11). It is the implementation contract.
- Changes to trading behavior must be written into `SPEC.md` and approved by the user before they are implemented. Do not mark future revisions approved on the user's behalf.
- Dhan integration and the minimal UI were requested by the user on 15 November 2026 (SPEC.md section 13). Risk and exit behavior requires the user's rules and is not authorized yet.
- Read `SPEC.md`, `docs/EXAMPLES.md`, and `docs/PROJECT_SETUP.md` before future project work.

## Product and strategy boundaries

- Build a Python backend with FastAPI and a terminal interface. The user later requested a bare-minimum React and Tailwind UI (`frontend/`, SPEC.md section 13 U1); keep it plain and keep all logic in the backend.
- Keep one shared strategy implementation for the terminal and API interfaces.
- Preserve the separate session-extreme qualification and four-candle breakout range. The entry candle is the candle immediately after the confirmed breakout candle.
- The Dhan adapter follows SPEC.md section 13. Credentials live only in the git-ignored `.env`; never print, log, or commit them, and never call Dhan from tests. Do not fabricate security identifiers, provider responses, or complete historical fixtures from partial chart observations.
- Stop-loss, target, and exit rules remain undefined. Keep those outputs unavailable rather than adding conventional defaults.
- A valid setup can subsequently fail. Do not classify every qualifying stock as a profitable trade or invent a cause of failure from chart movement alone.
- This project reports signals and reference prices. Order placement is outside the requested scope.
