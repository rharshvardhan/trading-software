import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon, { Spinner } from "./components/Icon.jsx";
import LiveFeed from "./components/LiveFeed.jsx";
import StockGroup from "./components/StockGroup.jsx";
import StockPicker from "./components/StockPicker.jsx";
import SummaryTiles from "./components/SummaryTiles.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { isWeekend, lastWeekdayIST, longDate, todayIST } from "./lib/format.js";
import { GROUP_ORDER, metaFor } from "./lib/states.js";

// All trading logic lives in the Python backend; this page only collects input and explains results.

// Live updates: states worth announcing when they change (setups, entries, cancellations, problems).
const NOTABLE = new Set([
  "waiting_for_breakout", "awaiting_entry", "entry_identified", "setup_cancelled", "needs_rule_decision",
  "entry_unavailable_session_end", "no_breakout", "invalid_data", "provider_error",
]);
const resultKey = (r) => `${r.input_name}|${r.strategy_window}`;
const signature = (r) =>
  [r.state, r.entry?.time, r.entry?.price, r.breakout?.candle_start, r.cancellation?.candle_start, r.risk?.stop_loss].join("|");
const BASE_TITLE = "Four Candle Scanner";
const FRESH_MS = 120_000; // how long a changed row stays highlighted
const clockTime = (iso) => (iso ? iso.slice(11, 19) : "");

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="size-9" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--color-accent)" />
      {[[7, 11, 9, 20], [13, 9, 7, 15], [19, 12, 8, 17], [25, 15, 10, 22]].map(([x, top, h, wick]) => (
        <g key={x}>
          <line x1={x} x2={x} y1={top - 3} y2={wick + 3} stroke="white" strokeWidth="1.2" strokeOpacity="0.8" />
          <rect x={x - 2} y={top} width="4" height={h} rx="1" fill="white" />
        </g>
      ))}
    </svg>
  );
}

function StopLossPill({ health }) {
  if (!health?.ok) return null;
  const on = Boolean(health.stop_loss_enabled);
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-hairline bg-raised px-3 py-1 text-xs font-medium"
      title={on ? "STOP_LOSS_ENABLED=true in .env" : "Set STOP_LOSS_ENABLED=true in .env to enable"}>
      <span className={`size-2 rounded-full ${on ? "bg-up" : "bg-muted"}`} />
      Stop loss {on ? "on" : "off"}
    </span>
  );
}

function ConnectionPill({ health }) {
  if (health === null) return <span className="text-xs text-muted">Checking backend…</span>;
  const [dot, label] = !health.ok
    ? ["bg-critical", "Backend offline"]
    : health.dhan_configured
      ? ["bg-up", "Dhan connected"]
      : ["bg-warning", "Dhan not configured"];
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-hairline bg-raised px-3 py-1 text-xs font-medium">
      <span className={`size-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export default function App() {
  const [date, setDate] = useState(lastWeekdayIST());
  const [stocks, setStocks] = useState([]);
  const provider = "dhan"; // the web page always scans live Dhan data
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [scan, setScan] = useState(null);
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState(() => new Set());
  const [health, setHealth] = useState(null);
  const [live, setLive] = useState(false);
  const [liveStatus, setLiveStatus] = useState(null);
  const [activity, setActivity] = useState([]);
  const [changed, setChanged] = useState(() => new Map());
  const [tick, setTick] = useState(() => Date.now());
  const sourceRef = useRef(null);
  const previousRef = useRef(null);
  const isToday = date === todayIST();

  useEffect(() => {
    fetch("/health")
      .then((response) => response.json())
      .then((body) => setHealth({ ok: true, ...body }))
      .catch(() => setHealth({ ok: false }));
  }, []);

  useEffect(() => {
    if (!busy) return undefined;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 500);
    return () => clearInterval(timer);
  }, [busy]);

  // ------------------------------------------------------------- live updates (SSE)

  const applyLiveScan = useCallback((body) => {
    const previous = previousRef.current;
    const changes = previous
      ? body.results.filter((r) => previous.has(resultKey(r)) && previous.get(resultKey(r)) !== signature(r) && NOTABLE.has(r.state))
      : [];
    previousRef.current = new Map(body.results.map((r) => [resultKey(r), signature(r)]));
    setScan(body);
    if (changes.length) {
      const stamp = Date.now();
      setActivity((items) => [...changes.map((r) => ({ id: `${body.scanned_at}|${resultKey(r)}`, at: body.scanned_at, result: r })), ...items].slice(0, 60));
      setChanged((map) => {
        const next = new Map(map);
        changes.forEach((r) => next.set(resultKey(r), stamp));
        return next;
      });
      if (document.hidden) document.title = `● ${changes.length} update${changes.length > 1 ? "s" : ""} · ${BASE_TITLE}`;
    }
  }, []);

  const stopLive = useCallback((message) => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setLive(false);
    setLiveStatus(message ? { phase: "stopped", message } : null);
  }, []);

  const startLive = useCallback(() => {
    if (!stocks.length) return setError("Add at least one stock to go live.");
    if (date !== todayIST()) return setError("Live updates work only for today's trading date.");
    sourceRef.current?.close();
    setError("");
    setActivity([]);
    previousRef.current = null;
    const params = new URLSearchParams({ trading_date: date, stocks: stocks.join(","), provider });
    const source = new EventSource(`/v1/scans/stream?${params}`);
    sourceRef.current = source;
    setLive(true);
    setLiveStatus({ phase: "connecting", message: "Connecting…" });
    source.addEventListener("scan", (event) => {
      const body = JSON.parse(event.data);
      applyLiveScan(body);
      setLiveStatus((s) => ({ ...s, connected: true, message: "", lastUpdate: body.scanned_at }));
    });
    source.addEventListener("status", (event) => {
      const status = JSON.parse(event.data);
      setLiveStatus((s) => ({ ...s, ...status, connected: true }));
    });
    source.addEventListener("scan_error", (event) => {
      setLiveStatus((s) => ({ ...s, message: JSON.parse(event.data).message }));
    });
    source.addEventListener("done", (event) => {
      source.close(); // otherwise EventSource would reconnect after the server ends the stream
      sourceRef.current = null;
      setLive(false);
      setLiveStatus({ phase: "done", message: JSON.parse(event.data).message });
    });
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        sourceRef.current = null;
        setLive(false);
        setLiveStatus({ phase: "stopped", message: "Live connection closed. Press Go live to reconnect." });
      } else {
        setLiveStatus((s) => ({ ...s, connected: false, message: "Connection lost; reconnecting…" }));
      }
    };
  }, [stocks, date, applyLiveScan]);

  // Changing the stock list or date while live restarts the stream (or stops it if the date is not today).
  const liveKey = `${date}|${stocks.join(",")}`;
  useEffect(() => {
    if (!sourceRef.current) return undefined;
    const timer = setTimeout(() => {
      if (!stocks.length) stopLive("Live updates stopped: no stocks selected.");
      else if (date !== todayIST()) stopLive("Live updates stopped: live works only for today's date.");
      else startLive();
    }, 800);
    return () => clearTimeout(timer);
  }, [liveKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => sourceRef.current?.close(), []);

  useEffect(() => {
    if (!live) return undefined;
    const timer = setInterval(() => setTick(Date.now()), 15_000);
    return () => clearInterval(timer);
  }, [live]);

  useEffect(() => {
    const reset = () => {
      if (!document.hidden) document.title = BASE_TITLE;
    };
    document.addEventListener("visibilitychange", reset);
    return () => document.removeEventListener("visibilitychange", reset);
  }, []);

  const isFresh = useCallback((key) => changed.has(key) && tick - changed.get(key) < FRESH_MS, [changed, tick]);

  async function runScan(event) {
    event.preventDefault();
    if (!stocks.length) return setError("Add at least one stock to scan.");
    setBusy(true);
    setElapsed(0);
    setError("");
    try {
      const response = await fetch("/v1/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trading_date: date, stocks, provider }),
      });
      const body = await response.json();
      if (!response.ok) {
        setError(Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : `Request failed (${response.status})`);
        return;
      }
      setScan(body);
      setFilter("all");
      setExpanded(new Set()); // every row starts collapsed after a scan; click a row to open it
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  // One group per stock (input order), holding that stock's result for each window.
  const groups = useMemo(() => {
    if (!scan) return [];
    const byStock = new Map();
    for (const r of scan.results) {
      if (!byStock.has(r.input_name)) byStock.set(r.input_name, []);
      byStock.get(r.input_name).push(r);
    }
    const order = (r) => GROUP_ORDER.indexOf(metaFor(r).group);
    return [...byStock.values()]
      .map((results, index) => ({ index, results: filter === "all" ? results : results.filter((r) => metaFor(r).group === filter) }))
      .filter((g) => g.results.length)
      .sort((a, b) => Math.min(...a.results.map(order)) - Math.min(...b.results.map(order)) || a.index - b.index);
  }, [scan, filter]);
  const windowsByKey = useMemo(() => Object.fromEntries((scan?.windows ?? []).map((w) => [w.key, w])), [scan]);

  const toggle = (key) => setExpanded((current) => {
    const next = new Set(current);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });

  return (
    <div className="min-h-screen">
      <header className="border-b border-hairline bg-surface">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo />
            <div>
              <h1 className="text-base font-semibold leading-tight">Four Candle Reversal Scanner</h1>
              <p className="text-xs text-ink-2">NSE cash stocks · 5-minute candles · Asia/Kolkata</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ConnectionPill health={health} />
            <StopLossPill health={health} />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        <form onSubmit={runScan} className="rounded-xl border border-hairline bg-surface p-4 sm:p-5">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <span className="mb-1.5 block text-sm font-medium">Stocks</span>
              <StockPicker provider={provider} values={stocks} onChange={setStocks} />
            </div>
            <div className="flex flex-wrap items-start gap-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium">Trading date</span>
                <input type="date" value={date} max={todayIST()} onChange={(event) => setDate(event.target.value)} required
                  className="h-11 rounded-lg border border-hairline bg-raised px-3 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" />
                <span className="mt-1 block text-xs text-ink-2">{isWeekend(date) ? "Weekend: markets are closed" : longDate(date)}</span>
              </label>
              <div>
                <span className="mb-1.5 block text-sm font-medium">Data</span>
                <span className="inline-flex h-11 items-center gap-2 rounded-lg border border-hairline bg-raised px-3 text-sm font-medium">
                  <span className="size-2 rounded-full bg-up" aria-hidden="true" />
                  Dhan live
                </span>
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
            <p className="text-xs text-ink-2">
              Only NSE cash stocks are scanned. Futures and indices appear in search but cannot be added.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {live ? (
                <button type="button" onClick={() => stopLive("Live updates stopped.")}
                  className="inline-flex h-10 items-center gap-2 rounded-lg border border-hairline bg-raised px-4 text-sm font-semibold hover:bg-ink/5">
                  <span className="relative flex size-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-up opacity-75" />
                    <span className="relative inline-flex size-2.5 rounded-full bg-up" />
                  </span>
                  Live · Stop
                </button>
              ) : (
                <button type="button" onClick={startLive} disabled={!isToday || busy}
                  title={isToday ? "Scan now and keep updating after every five-minute candle close" : "Live updates work only for today's date"}
                  className="inline-flex h-10 items-center gap-2 rounded-lg border border-accent px-4 text-sm font-semibold text-accent transition-colors hover:bg-accent/10 disabled:cursor-not-allowed disabled:border-hairline disabled:text-muted disabled:hover:bg-transparent">
                  Go live
                </button>
              )}
              <button type="submit" disabled={busy || live}
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60">
                {busy ? <><Spinner className="size-4" /> Scanning {stocks.length} · {elapsed}s</> : <>Scan {stocks.length ? `${stocks.length} stock${stocks.length > 1 ? "s" : ""}` : ""}</>}
              </button>
            </div>
          </div>
          {error && (
            <div className="mt-3 flex gap-2 rounded-md bg-critical/10 p-3 text-sm">
              <Icon name="alert" className="mt-0.5 size-4 shrink-0 text-critical" />
              {error}
            </div>
          )}
        </form>

        {scan ? (
          <section aria-label="Scan results" className={`space-y-4 transition-opacity ${busy ? "opacity-50" : ""}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold">Results for {longDate(scan.trading_date)}</h2>
                <p className="text-xs text-ink-2">
                  All {scan.windows.length} reference windows run on every stock ({scan.windows.map((w) => w.label).join(", ")}); each window is an independent signal.
                </p>
              </div>
              <p className="text-xs text-ink-2">
                Source Dhan Data API · scanned {scan.scanned_at.slice(11, 16)} IST · strategy {scan.strategy_version}
              </p>
            </div>
            {scan.synthetic_data_present && (
              <div className="flex gap-2 rounded-md bg-serious/15 p-3 text-sm">
                <Icon name="alert" className="mt-0.5 size-4 shrink-0 text-serious" />
                <span><span className="font-medium">Synthetic data:</span> some results use invented prices for testing, not market data.</span>
              </div>
            )}
            {(live || liveStatus) && (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-hairline bg-surface px-4 py-2.5 text-sm">
                <span className="inline-flex items-center gap-2 font-semibold">
                  <span className={`size-2 rounded-full ${live && liveStatus?.connected !== false ? "bg-up" : "bg-muted"}`} />
                  {live ? "Live" : "Live off"}
                </span>
                {liveStatus?.lastUpdate && <span className="text-ink-2">updated {clockTime(liveStatus.lastUpdate)}</span>}
                {live && liveStatus?.phase === "before_open" && <span className="text-ink-2">waiting for the 09:15 open</span>}
                {live && liveStatus?.next_scan_at && <span className="text-ink-2">next scan {clockTime(liveStatus.next_scan_at)}</span>}
                {liveStatus?.message && <span className="text-ink-2">{liveStatus.message}</span>}
                {live && liveStatus?.refresh_seconds && (
                  <span className="text-xs text-muted">Refreshing every {liveStatus.refresh_seconds} s from the 09:15 open.</span>
                )}
              </div>
            )}
            {(live || activity.length > 0) && (
              <div className="rounded-xl border border-hairline bg-surface">
                <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-hairline px-4 py-2.5">
                  <h3 className="text-sm font-semibold">Live updates</h3>
                  <span className="text-xs text-muted">new setups, entries and cancellations, newest first</span>
                </div>
                <LiveFeed items={activity} windowsByKey={windowsByKey} />
              </div>
            )}
            <SummaryTiles results={scan.results} windows={scan.windows} filter={filter} onFilter={setFilter} />
            <div className="overflow-x-auto rounded-xl border border-hairline bg-surface">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr>
                    <th className="py-2.5 pl-4 pr-3 font-medium">Stock / window</th>
                    <th className="px-3 py-2.5 font-medium">Result</th>
                    <th className="px-3 py-2.5 font-medium">Range</th>
                    <th className="px-3 py-2.5 font-medium">Breakout</th>
                    <th className="px-3 py-2.5 font-medium">Entry</th>
                    <th className="px-3 py-2.5 text-right font-medium">Entry price</th>
                    <th className="px-3 py-2.5 font-medium">Stop loss</th>
                    <th className="hidden px-3 py-2.5 font-medium xl:table-cell">Exit</th>
                    <th className="py-2.5 pl-2 pr-4"><span className="sr-only">Details</span></th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <StockGroup key={g.results[0].input_name} results={g.results} windowsByKey={windowsByKey} expanded={expanded}
                      onToggle={toggle} stopEnabled={scan.stop_loss_enabled} isFresh={isFresh} />
                  ))}
                  {!groups.length && (
                    <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-muted">No stocks in this group.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-ink-2">
              Click a row to see why.{" "}
              {scan.stop_loss_enabled
                ? "Stop loss is on: initial level for the 09:45 window only (its reference high for a SHORT, low for a LONG)."
                : "Stop loss is off (set STOP_LOSS_ENABLED=true in .env and restart to show the 09:45 initial stop level)."}{" "}
              Other windows' stop loss, targets and exits are not yet defined, and no stop hits or exits are computed. Entry
              prices are the next candle's open (a reference price, not an order fill); no orders are placed.
            </p>
          </section>
        ) : (
          <section className="rounded-xl border border-dashed border-hairline p-8 text-center text-sm text-ink-2">
            Search and add stocks above (or add the Nifty 50), pick a trading day, and press <span className="font-medium text-ink">Scan</span>.
            Each stock is checked against the four steps, and you can open any row to see why.
          </section>
        )}
      </main>
    </div>
  );
}
