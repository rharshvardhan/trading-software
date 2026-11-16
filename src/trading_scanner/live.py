"""Live updates: re-run the shared scan on a candle-aligned schedule and stream it over SSE.

Requested by the user on 16 November 2026 ("each time we cannot click on scan as am trading live
now so can we have a sse so all updates live"). No trading rule changes: every update is the same
``ScanService.scan`` the Scan button runs, pushed to the browser as Server-Sent Events.

Schedule, in Asia/Kolkata and only while the trading date is today (user request: "as market
starts at 9:15, i need every 60 seconds it to be refreshed"):

* one scan as soon as the stream opens;
* then a fixed cadence anchored at the 09:15 open: 09:15:08, and every ``LIVE_REFRESH_SECONDS``
  (default 60) after that until 15:35. The 8-second offset gives the provider time to publish the
  candle that just closed; with 60 seconds every five-minute candle close is picked up 8 seconds
  later. A scan that would land in the last seconds before a five-minute boundary (possible only
  with intervals that do not divide 300) moves to just after it, so a provider clock slightly ahead
  cannot deliver a candle "from the future";
* before 09:15 the stream waits for the open; after 15:35, or for a past trading date, it sends a
  final scan and a ``done`` event, because the results can no longer change.

Events: ``scan`` (a full scan response), ``status`` (phase and next scan time), ``scan_error``,
and ``done``; ``: keep-alive`` comments flow while waiting.
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date, datetime, time, timedelta

from starlette.concurrency import run_in_threadpool

from trading_scanner.market import IST
from trading_scanner.models import ScanRequest
from trading_scanner.service import ScanService

LIVE_START = time(9, 15)
LIVE_END = time(15, 35)
SETTLE_SECONDS = 8  # after a candle boundary, so the just-closed candle has been published
GUARD_SECONDS = 5  # no regular refresh this close before a boundary
KEEPALIVE_SECONDS = 15
RETRY_MILLISECONDS = 5000


def next_refresh(now: datetime, refresh_seconds: int, settle: int = SETTLE_SECONDS, guard: int = GUARD_SECONDS) -> datetime:
    """The next scheduled live scan strictly after ``now``: 09:15 + settle, then every ``refresh_seconds``."""
    anchor = datetime.combine(now.date(), LIVE_START, tzinfo=now.tzinfo) + timedelta(seconds=settle)
    if now < anchor:
        candidate = anchor
    else:
        steps = math.floor((now - anchor).total_seconds() / refresh_seconds) + 1
        candidate = anchor + timedelta(seconds=steps * refresh_seconds)
    slot_start = candidate.replace(second=0, microsecond=0) - timedelta(minutes=candidate.minute % 5)
    next_boundary = slot_start + timedelta(minutes=5)
    if candidate >= next_boundary - timedelta(seconds=guard):
        candidate = next_boundary + timedelta(seconds=settle)
    return candidate


def live_phase(now: datetime, trading_date: date) -> str:
    """``before_open``, ``open``, or ``closed`` (session over, or the date is not today)."""
    if trading_date != now.date():
        return "closed"
    current = now.time().replace(tzinfo=None)
    if current < LIVE_START:
        return "before_open"
    return "open" if current <= LIVE_END else "closed"


def sse_event(name: str, data: str, event_id: str | None = None) -> str:
    lines = [f"event: {name}"]
    if event_id:
        lines.append(f"id: {event_id}")
    lines.extend(f"data: {line}" for line in (data.splitlines() or [""]))
    return "\n".join(lines) + "\n\n"


async def live_scan_events(
    service: ScanService,
    request: ScanRequest,
    *,
    refresh_seconds: int,
    is_disconnected: Callable[[], Awaitable[bool]],
    clock: Callable[[], datetime] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    max_updates: int | None = None,
) -> AsyncIterator[str]:
    """Yield SSE text: a scan now, then on the live schedule until the session ends or the client leaves."""
    now_fn = clock or service.now
    yield f"retry: {RETRY_MILLISECONDS}\n\n"
    attempts = 0
    while True:
        attempts += 1
        try:
            response = await run_in_threadpool(service.scan, request)  # blocking provider I/O off the loop
        except Exception as exc:  # report and keep the stream alive for the next scheduled scan
            yield sse_event("scan_error", json.dumps({"message": f"Scan failed ({type(exc).__name__}): {exc}"}))
        else:
            yield sse_event("scan", response.model_dump_json(), response.scanned_at.isoformat())

        now = now_fn().astimezone(IST)
        phase = live_phase(now, request.trading_date)
        if phase == "closed" or (max_updates is not None and attempts >= max_updates):
            message = (
                "Live updates stopped: the trading date is not today, so these results will not change."
                if request.trading_date != now.date()
                else "Live updates stopped: the session has ended; these are the final results."
                if phase == "closed"
                else "Live updates stopped."
            )
            yield sse_event("done", json.dumps({"phase": phase, "message": message}))
            return
        next_at = next_refresh(now, refresh_seconds)  # before the open this is 09:15:08
        yield sse_event(
            "status",
            json.dumps({"phase": phase, "next_scan_at": next_at.isoformat(), "refresh_seconds": refresh_seconds}),
        )

        while (remaining := (next_at - now_fn().astimezone(IST)).total_seconds()) > 0:
            if await is_disconnected():
                return
            await sleep(min(KEEPALIVE_SECONDS, remaining))
            yield ": keep-alive\n\n"
        if await is_disconnected():
            return
