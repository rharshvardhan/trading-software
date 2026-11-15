import { metaFor } from "../lib/states.js";

const TILES = [
  { key: "all", label: "Scanned" },
  { key: "entry", label: "Entries" },
  { key: "waiting", label: "Waiting" },
  { key: "attention", label: "Needs attention" },
  { key: "none", label: "No trade" },
];

// Counts by outcome; each tile filters the table below.
export default function SummaryTiles({ results, filter, onFilter }) {
  const count = (key) => (key === "all" ? results.length : results.filter((r) => metaFor(r).group === key).length);
  const entries = results.filter((r) => r.state === "entry_identified");
  const longs = entries.filter((r) => r.entry?.signal === "long").length;
  const sub = {
    all: "stocks",
    entry: `${longs} long · ${entries.length - longs} short`,
    waiting: "range or breakout pending",
    attention: "rule or data issue",
    none: "no setup or no breakout",
  };
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {TILES.map((tile) => {
        const active = filter === tile.key;
        return (
          <button key={tile.key} type="button" onClick={() => onFilter(tile.key)} aria-pressed={active}
            className={`rounded-lg border bg-raised p-3 text-left transition-colors ${active ? "border-accent ring-2 ring-accent/20" : "border-hairline hover:border-axis"}`}>
            <div className="text-xs text-ink-2">{tile.label}</div>
            <div className="mt-1 text-2xl font-semibold">{count(tile.key)}</div>
            <div className="mt-0.5 truncate text-xs text-muted">{sub[tile.key]}</div>
          </button>
        );
      })}
    </div>
  );
}
