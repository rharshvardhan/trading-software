import { useEffect, useMemo, useState } from "react";
import Icon, { Spinner } from "./components/Icon.jsx";
import ResultRow from "./components/ResultRow.jsx";
import StockPicker from "./components/StockPicker.jsx";
import SummaryTiles from "./components/SummaryTiles.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { isWeekend, lastWeekdayIST, longDate, todayIST } from "./lib/format.js";
import { GROUP_ORDER, metaFor } from "./lib/states.js";

// All trading logic lives in the Python backend; this page only collects input and explains results.

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
      const entries = body.results.filter((r) => r.state === "entry_identified");
      setExpanded(new Set(body.results.length === 1 ? [body.results[0].input_name] : entries.length === 1 ? [entries[0].input_name] : []));
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  const rows = useMemo(() => {
    if (!scan) return [];
    const order = (r) => GROUP_ORDER.indexOf(metaFor(r).group);
    return scan.results
      .map((r, index) => ({ r, index }))
      .filter(({ r }) => filter === "all" || metaFor(r).group === filter)
      .sort((a, b) => order(a.r) - order(b.r) || a.index - b.index)
      .map(({ r }) => r);
  }, [scan, filter]);

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
            <button type="submit" disabled={busy}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-60">
              {busy ? <><Spinner className="size-4" /> Scanning {stocks.length} · {elapsed}s</> : <>Scan {stocks.length ? `${stocks.length} stock${stocks.length > 1 ? "s" : ""}` : ""}</>}
            </button>
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
              <h2 className="text-base font-semibold">Results for {longDate(scan.trading_date)}</h2>
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
            <SummaryTiles results={scan.results} filter={filter} onFilter={setFilter} />
            <div className="overflow-x-auto rounded-xl border border-hairline bg-surface">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr>
                    <th className="py-2.5 pl-4 pr-3 font-medium">Stock</th>
                    <th className="px-3 py-2.5 font-medium">Result</th>
                    <th className="px-3 py-2.5 font-medium">Range</th>
                    <th className="px-3 py-2.5 font-medium">Breakout</th>
                    <th className="px-3 py-2.5 font-medium">Entry</th>
                    <th className="px-3 py-2.5 text-right font-medium">Entry price</th>
                    <th className="hidden px-3 py-2.5 font-medium xl:table-cell">Stop loss</th>
                    <th className="hidden px-3 py-2.5 font-medium xl:table-cell">Exit</th>
                    <th className="py-2.5 pl-2 pr-4"><span className="sr-only">Details</span></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <ResultRow key={r.input_name} result={r} expanded={expanded.has(r.input_name)} onToggle={() => toggle(r.input_name)} />
                  ))}
                  {!rows.length && (
                    <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-muted">No stocks in this group.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-ink-2">
              Click a row to see why. Stop loss, target and exit: rules not yet defined. Entry prices are the next candle's
              open (a reference price, not an order fill); no orders are placed.
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
