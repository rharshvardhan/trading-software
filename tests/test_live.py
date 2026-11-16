"""Live updates over Server-Sent Events (user requests of 16 Nov 2026: live updates instead of
clicking Scan; refresh every LIVE_REFRESH_SECONDS, default 60, from the 09:15 open)."""

import asyncio
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from helpers import make_service
from trading_scanner.api import create_app
from trading_scanner.config import Settings
from trading_scanner.live import live_phase, live_scan_events, next_refresh
from trading_scanner.market import IST
from trading_scanner.models import ScanRequest

DAY = datetime(2026, 11, 16, tzinfo=IST).date()


def at(hhmmss: str, day=DAY) -> datetime:
    h, m, s = map(int, hhmmss.split(":"))
    return datetime(day.year, day.month, day.day, h, m, s, tzinfo=IST)


# ------------------------------------------------------------------ schedule


@pytest.mark.parametrize(
    "now, expected",
    [("07:00:00", "09:15:08"), ("09:15:00", "09:15:08"), ("09:15:08", "09:16:08"), ("09:57:00", "09:57:08"),
     ("09:59:50", "10:00:08"), ("10:00:08", "10:01:08"), ("12:34:59", "12:35:08"), ("15:34:30", "15:35:08")],
)
def test_sixty_second_cadence_is_anchored_at_the_open(now, expected):
    assert next_refresh(at(now), 60) == at(expected)


def test_every_candle_close_is_scanned_eight_seconds_later_at_sixty_seconds():
    scans, now = [], at("09:15:00")
    while now < at("10:31:00"):
        now = next_refresh(now, 60)
        scans.append(now.strftime("%H:%M:%S"))
    assert all(s.endswith(":08") for s in scans) and {"10:00:08", "10:05:08", "10:30:08"} <= set(scans)
    gaps = {(datetime.strptime(b, "%H:%M:%S") - datetime.strptime(a, "%H:%M:%S")).seconds for a, b in zip(scans, scans[1:])}
    assert gaps == {60}


def test_odd_intervals_keep_the_anchor_but_never_land_just_before_a_boundary():
    assert next_refresh(at("09:15:08"), 45) == at("09:15:53")
    now, scans = at("09:15:00"), []
    while now < at("11:00:00"):
        now = next_refresh(now, 45)
        scans.append(now)
    for scan in scans:  # never within 5 s before a five-minute boundary
        assert not (scan.minute % 5 == 4 and scan.second >= 55)


def test_live_phase():
    assert live_phase(at("09:00:00"), DAY) == "before_open"
    assert live_phase(at("09:15:00"), DAY) == "open" and live_phase(at("15:35:00"), DAY) == "open"
    assert live_phase(at("15:35:01"), DAY) == "closed"
    assert live_phase(at("11:00:00"), DAY - timedelta(days=3)) == "closed"  # a past trading date never changes


def test_refresh_setting_is_clamped_and_forgiving():
    def parsed(raw):
        return Settings(_env_file=None, LIVE_REFRESH_SECONDS=raw).live_refresh_seconds

    assert parsed("60") == 60 and parsed(" 30 ") == 30 and parsed("5") == 15 and parsed("999") == 300
    assert parsed("abc") == 60 and parsed("") == 60 and Settings(_env_file=None).live_refresh_seconds == 60


# ------------------------------------------------------------------ event stream


class FakeClock:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


class StubResponse:
    def __init__(self, scanned_at):
        self.scanned_at = scanned_at

    def model_dump_json(self):
        return json.dumps({"scanned_at": self.scanned_at.isoformat()})


class StubService:
    def __init__(self, clock, fail_on=()):
        self.clock, self.calls, self.fail_on = clock, [], set(fail_on)

    def now(self):
        return self.clock.now

    def scan(self, request):
        self.calls.append(self.clock.now)
        if len(self.calls) in self.fail_on:
            raise RuntimeError("provider hiccup")
        return StubResponse(self.clock.now)


def collect(service, clock, trading_date=DAY, refresh=60, max_updates=None, disconnect_after=None):
    async def is_disconnected():
        return disconnect_after is not None and len(service.calls) >= disconnect_after

    async def run():
        request = ScanRequest(trading_date=trading_date, stocks=["SYN-LONG"], provider="fixture")
        return [chunk async for chunk in live_scan_events(
            service, request, refresh_seconds=refresh, is_disconnected=is_disconnected,
            clock=clock, sleep=clock.sleep, max_updates=max_updates,
        )]

    return asyncio.run(run())


def events(chunks):
    out = []
    for chunk in chunks:
        if chunk.startswith("event: "):
            name = chunk.split("\n", 1)[0][len("event: "):]
            data = "\n".join(line[6:] for line in chunk.splitlines() if line.startswith("data: "))
            out.append((name, json.loads(data)))
    return out


def test_live_stream_scans_now_then_every_sixty_seconds_with_keep_alives():
    clock = FakeClock(at("10:01:30"))
    service = StubService(clock)
    chunks = collect(service, clock, max_updates=3)
    assert chunks[0] == "retry: 5000\n\n"
    assert [c.strftime("%H:%M:%S") for c in service.calls] == ["10:01:30", "10:02:08", "10:03:08"]
    names = [name for name, _ in events(chunks)]
    assert names == ["scan", "status", "scan", "status", "scan", "done"]
    status = events(chunks)[1][1]
    assert status == {"phase": "open", "next_scan_at": at("10:02:08").isoformat(), "refresh_seconds": 60}
    assert ": keep-alive\n\n" in chunks


def test_before_the_open_it_waits_for_0915():
    clock = FakeClock(at("08:50:00"))
    service = StubService(clock)
    chunks = collect(service, clock, max_updates=2)
    assert [c.strftime("%H:%M:%S") for c in service.calls] == ["08:50:00", "09:15:08"]
    assert events(chunks)[1][1]["phase"] == "before_open"


def test_past_date_or_closed_session_sends_one_scan_and_done():
    clock = FakeClock(at("11:00:00"))
    service = StubService(clock)
    names = [name for name, _ in events(collect(service, clock, trading_date=DAY - timedelta(days=3)))]
    assert names == ["scan", "done"] and len(service.calls) == 1
    clock_after = FakeClock(at("15:40:00"))
    done = events(collect(StubService(clock_after), clock_after))[-1]
    assert done[0] == "done" and "session has ended" in done[1]["message"]


def test_stream_stops_when_the_browser_disconnects():
    clock = FakeClock(at("10:01:30"))
    service = StubService(clock)
    chunks = collect(service, clock, disconnect_after=1)
    assert len(service.calls) == 1 and [n for n, _ in events(chunks)] == ["scan", "status"]


def test_a_failed_scan_is_reported_and_the_stream_continues():
    clock = FakeClock(at("10:01:30"))
    service = StubService(clock, fail_on={1})
    names = [name for name, _ in events(collect(service, clock, max_updates=2))]
    assert names == ["scan_error", "status", "scan", "done"]


# ------------------------------------------------------------------ endpoint


def test_endpoint_streams_the_same_scan_as_the_post_endpoint():
    client = TestClient(create_app(make_service()))
    response = client.get("/v1/scans/stream", params={"trading_date": "2026-11-13", "stocks": "SYN-LONG,NOPE", "provider": "fixture"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    streamed = dict(events([chunk + "\n\n" for chunk in response.text.split("\n\n") if chunk]))
    assert set(streamed) == {"scan", "done"}  # a past date: one scan, then done
    posted = client.post("/v1/scans", json={"trading_date": "2026-11-13", "stocks": ["SYN-LONG", "NOPE"], "provider": "fixture"}).json()
    assert streamed["scan"] == posted


def test_endpoint_today_sends_a_first_scan_immediately():
    client = TestClient(create_app(make_service()))  # fixed clock: 2026-11-15 12:00 IST
    response = client.get("/v1/scans/stream", params={"trading_date": "2026-11-15", "stocks": "SYN-LONG", "provider": "fixture", "max_updates": 1})
    names = [name for name, _ in events([c + "\n\n" for c in response.text.split("\n\n") if c])]
    assert names == ["scan", "done"]


@pytest.mark.parametrize(
    "params",
    [{"trading_date": "2026-11-13", "provider": "fixture"},
     {"trading_date": "2026-11-13", "stocks": " , ", "provider": "fixture"},
     {"trading_date": "13-11-2026", "stocks": "SYN-LONG", "provider": "fixture"},
     {"trading_date": "2026-11-16", "stocks": "SYN-LONG", "provider": "fixture"},
     {"trading_date": "2026-11-13", "stocks": "SYN-LONG", "provider": "csv"}],
)
def test_endpoint_rejects_bad_requests_before_streaming(params):
    assert TestClient(create_app(make_service())).get("/v1/scans/stream", params=params).status_code == 422
