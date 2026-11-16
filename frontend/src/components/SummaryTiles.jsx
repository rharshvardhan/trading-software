import { metaFor } from "../lib/states.js";

const TILES = [
  { key: "all", label: "Scanned" },
  { key: "entry", label: "Entries" },
  { key: "waiting", label: "Waiting" },
  { key: "attention", label: "Needs attention" },
  { key: "none", label: "No trade" },
];

// Counts by outcome across both windows (one result per stock and window); each tile filters the table.
export default function SummaryTiles({ results, windows, filter, onFilter }) {
  const count = (key, list = results) => list.filter((r) => key === "all" || metaFor(r).group === key).length;
  const stocks = new Set(results.map((r) => r.input_name)).size;
  const perWindow = (key) =>
    windows.map((w) => `${w.reference_candles[0]}: ${count(key, results.filter((r) => r.strategy_window === w.key))}`).join(" · ");
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {TILES.map((tile) => {
        const active = filter === tile.key;
        return (
          <button key={tile.key} type="button" onClick={() => onFilter(tile.key)} aria-pressed={active}
            className={`rounded-lg border bg-raised p-3 text-left transition-colors ${active ? "border-accent ring-2 ring-accent/20" : "border-hairline hover:border-axis"}`}>
            <div className="text-xs text-ink-2">{tile.label}</div>
            <div className="mt-1 text-2xl font-semibold">{tile.key === "all" ? stocks : count(tile.key)}</div>
            <div className="mt-0.5 truncate text-xs text-muted">
              {tile.key === "all" ? `stocks × ${windows.length} windows` : perWindow(tile.key)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
