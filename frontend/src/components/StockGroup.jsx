import { Fragment } from "react";
import ResultRow from "./ResultRow.jsx";

// A stock-level failure is identical in every window, so it is shown once.
const STOCK_LEVEL = new Set(["symbol_error", "provider_error", "no_session"]);

// One stock: a header row, then one row per reference window (each window is an independent signal).
export default function StockGroup({ results, windowsByKey, expanded, onToggle, stopEnabled, isFresh = () => false }) {
  const first = results[0];
  const symbol = first.instrument?.symbol ?? first.input_name;
  const shared =
    results.length > 1 && STOCK_LEVEL.has(first.state) && results.every((r) => r.state === first.state && r.reason === first.reason);
  const rows = shared
    ? [{ r: first, key: `${first.input_name}|all`, label: "All windows", sub: "same result for each window" }]
    : results.map((r) => {
        const w = windowsByKey[r.strategy_window];
        return {
          r,
          key: `${r.input_name}|${r.strategy_window}`,
          label: `${w.reference_candles[0]} window`,
          sub: `${w.reference_candles.length} candles · range final ${w.range_final_at}`,
        };
      });
  return (
    <Fragment>
      <tr className="border-t-2 border-hairline bg-ink/[0.025]">
        <td colSpan={9} className="px-4 py-2">
          <span className="font-semibold">{symbol}</span>
          <span className="ml-2 text-xs text-ink-2">{first.instrument?.name ?? ""}</span>
          {first.synthetic && <span className="ml-2 text-xs font-medium text-serious">synthetic</span>}
        </td>
      </tr>
      {rows.map(({ r, key, label, sub }) => (
        <ResultRow key={key} result={r} window={windowsByKey[r.strategy_window]} windowLabel={label} windowSub={sub}
          expanded={expanded.has(key)} onToggle={() => onToggle(key)} stopEnabled={stopEnabled}
          highlight={isFresh(`${r.input_name}|${r.strategy_window}`)} />
      ))}
    </Fragment>
  );
}
