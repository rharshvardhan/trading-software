import { Fragment } from "react";
import CandleChart from "./CandleChart.jsx";
import Icon from "./Icon.jsx";
import StatusBadge from "./StatusBadge.jsx";
import Steps from "./Steps.jsx";
import { hhmm, inr, price } from "../lib/format.js";

function CandleTable({ candles }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-ink-2 hover:text-ink">Show all {candles.length} candles</summary>
      <div className="mt-2 max-h-64 overflow-auto rounded-md border border-hairline">
        <table className="w-full text-xs tabular-nums">
          <thead className="sticky top-0 bg-surface text-muted">
            <tr>{["Time", "Open", "High", "Low", "Close", "Volume"].map((h) => <th key={h} className="px-2 py-1 text-right font-medium first:text-left">{h}</th>)}</tr>
          </thead>
          <tbody>
            {candles.map((c) => (
              <tr key={c.start} className="border-t border-hairline">
                <td className="px-2 py-1">{hhmm(c.start)}</td>
                <td className="px-2 py-1 text-right">{price(c.open)}</td>
                <td className="px-2 py-1 text-right">{price(c.high)}</td>
                <td className="px-2 py-1 text-right">{price(c.low)}</td>
                <td className="px-2 py-1 text-right">{price(c.close)}</td>
                <td className="px-2 py-1 text-right">{c.volume ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default function ResultRow({ result: r, expanded, onToggle }) {
  const symbol = r.instrument?.symbol ?? r.input_name;
  const entryCell = r.entry?.time ? hhmm(r.entry.time) : r.state === "awaiting_entry" ? `${hhmm(r.entry.expected_time)} pending` : "—";
  return (
    <Fragment>
      <tr onClick={onToggle} className={`cursor-pointer border-t border-hairline transition-colors hover:bg-ink/[0.03] ${expanded ? "bg-ink/[0.03]" : ""}`}>
        <td className="py-3 pl-4 pr-3">
          <div className="font-medium">{symbol}</div>
          <div className="max-w-44 truncate text-xs text-ink-2">
            {r.instrument?.name ?? "—"}
            {r.synthetic && <span className="ml-1 font-medium text-serious">· synthetic</span>}
          </div>
        </td>
        <td className="px-3 py-3"><StatusBadge result={r} /></td>
        <td className="whitespace-nowrap px-3 py-3 tabular-nums text-ink-2">{r.reference ? `${price(r.reference.low)} – ${price(r.reference.high)}` : "—"}</td>
        <td className="px-3 py-3 tabular-nums">
          {r.breakout ? (
            <span className="inline-flex items-center gap-1">
              <Icon name={r.breakout.side === "above" ? "up" : "down"} className={`size-3 ${r.breakout.side === "above" ? "text-up" : "text-down"}`} />
              {hhmm(r.breakout.candle_start)}
            </span>
          ) : "—"}
        </td>
        <td className="px-3 py-3 tabular-nums">{entryCell}</td>
        <td className="px-3 py-3 text-right font-semibold tabular-nums">{inr(r.entry?.price)}</td>
        <td className="hidden px-3 py-3 text-muted xl:table-cell">Not defined</td>
        <td className="hidden px-3 py-3 text-muted xl:table-cell">Not defined</td>
        <td className="py-3 pl-2 pr-4 text-right">
          <button type="button" aria-expanded={expanded} aria-label={`${expanded ? "Hide" : "Show"} details for ${symbol}`}
            className="rounded p-1 text-muted hover:bg-ink/5 hover:text-ink" onClick={(event) => { event.stopPropagation(); onToggle(); }}>
            <Icon name="chevron" className={`size-4 transition-transform ${expanded ? "rotate-90" : ""}`} />
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-ink/[0.03]">
          <td colSpan={9} className="px-4 pb-5 pt-1">
            <div className="grid gap-6 rounded-lg border border-hairline bg-raised p-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]">
              <div>
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Why this result</h4>
                <Steps result={r} />
                <p className="mt-4 text-sm leading-relaxed text-ink-2">{r.reason}</p>
                {r.rule_decision && (
                  <div className="mt-3 flex gap-2 rounded-md bg-warning/15 p-3 text-sm">
                    <Icon name="question" className="mt-0.5 size-4 shrink-0 text-warning" />
                    <span><span className="font-medium">Your decision needed:</span> {r.rule_decision.question}</span>
                  </div>
                )}
                {r.notes.map((note) => <p key={note} className="mt-2 text-xs text-ink-2">Note: {note}</p>)}
              </div>
              <div className="min-w-0">
                {r.candles?.length ? (
                  <>
                    <CandleChart result={r} />
                    <CandleTable candles={r.candles} />
                  </>
                ) : (
                  <div className="flex h-full min-h-32 items-center justify-center rounded-md border border-dashed border-hairline text-sm text-muted">No candle data to chart</div>
                )}
              </div>
            </div>
            {r.data && (
              <p className="mt-2 text-xs text-muted">
                {r.data.data_label} Data as of {r.data.as_of.slice(0, 16).replace("T", " ")} IST · last closed candle {r.data.last_closed_candle ?? "none"}
                {r.data.notes.length ? ` · ${r.data.notes.join(" ")}` : ""}
              </p>
            )}
          </td>
        </tr>
      )}
    </Fragment>
  );
}
