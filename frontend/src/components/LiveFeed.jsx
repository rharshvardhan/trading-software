import StatusBadge from "./StatusBadge.jsx";
import { hhmm, inr, price } from "../lib/format.js";

// What changed in one live update, in plain words.
function detail(r) {
  if (r.state === "entry_identified" && r.entry?.time) {
    const stop = r.risk?.stop_loss ? ` · stop ${inr(r.risk.stop_loss)}` : "";
    return `${r.entry.signal.toUpperCase()} at the ${hhmm(r.entry.time)} open · ${inr(r.entry.price)}${stop}`;
  }
  if (r.state === "awaiting_entry") return `Breakout confirmed; entry at the ${hhmm(r.entry?.expected_time)} open`;
  if (r.state === "setup_cancelled" && r.cancellation) return `Wrong-way close at ${hhmm(r.cancellation.candle_start)}; cancelled at ${hhmm(r.cancellation.confirmed_at)}`;
  if (r.state === "waiting_for_breakout" && r.reference) {
    const setup = r.qualification?.permitted_signal?.toUpperCase();
    return `${setup ? `${setup} setup` : "Setup"} formed · range ${price(r.reference.low)} – ${price(r.reference.high)}`;
  }
  return r.reason.split(". ")[0];
}

// Live changes, newest first.
export default function LiveFeed({ items, windowsByKey }) {
  if (!items.length) {
    return (
      <p className="px-4 py-3 text-sm text-ink-2">
        Nothing new yet. New setups, entries and cancellations appear here as they happen (checked every refresh).
      </p>
    );
  }
  return (
    <ul className="max-h-72 divide-y divide-hairline overflow-auto">
      {items.map(({ id, at, result: r }) => (
        <li key={id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 text-sm">
          <span className="tabular-nums text-muted">{at.slice(11, 19)}</span>
          <span className="font-semibold">{r.instrument?.symbol ?? r.input_name}</span>
          <span className="text-xs text-ink-2">{windowsByKey[r.strategy_window]?.reference_candles[0]} window</span>
          <StatusBadge result={r} />
          <span className="text-ink-2">{detail(r)}</span>
        </li>
      ))}
    </ul>
  );
}
