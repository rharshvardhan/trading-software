import { useState } from "react";
import { hhmm, inr, price } from "../lib/format.js";

// Five-minute session chart: reference window, fixed range band, breakout and entry markers.
// Up candles are hollow and down candles filled, so direction never relies on color alone.

const W = 680;
const H = 260;
const M = { top: 22, right: 14, bottom: 26, left: 58 };
const SLOTS = 75; // 09:15 .. 15:25
const PW = W - M.left - M.right;
const PH = H - M.top - M.bottom;
const STEP = PW / SLOTS;
// Surface-colored outline behind annotation text so it stays legible over candles.
const HALO = { stroke: "var(--color-surface)", strokeWidth: 4, paintOrder: "stroke", strokeLinejoin: "round" };

const slotOf = (iso) => {
  const [h, m] = iso.slice(11, 16).split(":").map(Number);
  return (h * 60 + m - (9 * 60 + 15)) / 5;
};
const xOf = (slot) => M.left + (slot + 0.5) * STEP;
const edgeOf = (slot) => M.left + slot * STEP;

function niceTicks(min, max, count = 4) {
  const raw = (max - min) / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((f) => f * magnitude).find((s) => s >= raw) ?? raw;
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Number(v.toFixed(6)));
  return ticks;
}

const labelSlot = (hhmmText) => {
  const [h, m] = hhmmText.split(":").map(Number);
  return (h * 60 + m - (9 * 60 + 15)) / 5;
};

export default function CandleChart({ result, window }) {
  const [hover, setHover] = useState(null);
  const refCandles = window?.reference_candles ?? ["10:30", "10:35", "10:40", "10:45"];
  const refStart = labelSlot(refCandles[0]);
  const refCount = refCandles.length;
  const candles = result.candles;
  if (!candles?.length) return null;

  const ref = result.reference;
  // The chart marks the candle that confirmed a breakout, or the one that cancelled the setup.
  const breakout = result.breakout ?? result.cancellation;
  const cancelled = !result.breakout && Boolean(result.cancellation);
  const entry = result.entry?.time ? result.entry : null;
  const trigger = result.trigger;

  let lo = Math.min(...candles.map((c) => Number(c.low)));
  let hi = Math.max(...candles.map((c) => Number(c.high)));
  const pad = (hi - lo || hi * 0.01) * 0.06;
  lo -= pad;
  hi += pad;
  const yOf = (v) => M.top + ((hi - Number(v)) / (hi - lo)) * PH;
  const ticks = niceTicks(lo, hi);
  const body = Math.max(1.5, STEP * 0.62);

  const bandEnd = breakout ? slotOf(breakout.candle_end) : slotOf(candles[candles.length - 1].end);
  const bySlot = new Map(candles.map((c) => [Math.round(slotOf(c.start)), c]));
  const hovered = hover !== null ? bySlot.get(hover) : null;

  const onMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * W;
    const slot = Math.min(SLOTS - 1, Math.max(0, Math.floor((x - M.left) / STEP)));
    setHover(bySlot.has(slot) ? slot : null);
  };

  const entryX = entry ? xOf(slotOf(entry.time)) : 0;
  const stop = result.risk?.stop_loss ?? null;
  const stopFromX = entry ? entryX : breakout && !cancelled ? edgeOf(slotOf(breakout.candle_end)) : null;
  const entryLabelLeft = entryX > W - 150;
  const breakoutX = breakout ? xOf(slotOf(breakout.candle_start)) : 0;
  const breakoutBelow = breakout?.side === "below";

  const summary = [
    ref && `Reference range ${price(ref.low)} to ${price(ref.high)}`,
    trigger && `first break ${hhmm(trigger.candle_start)} ${trigger.side} the range`,
    breakout && (cancelled && breakout.trigger_basis && breakout.trigger_basis !== "close"
      ? `cancelled by ${hhmm(breakout.candle_start)} candle ${breakout.trigger_basis} breach`
      : `${trigger ? "confirmation" : "breakout"} candle ${hhmm(breakout.candle_start)} closed ${breakout.side} the range`),
    entry && `entry at ${hhmm(entry.time)} open ${inr(entry.price)}`,
  ].filter(Boolean).join(", ");

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full select-none" role="img"
        aria-label={`Five-minute candles for ${result.instrument?.symbol ?? result.input_name}. ${summary}`}
        onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {/* grid + y axis */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={W - M.right} y1={yOf(t)} y2={yOf(t)} stroke="var(--color-grid)" strokeWidth="1" />
            <text x={M.left - 8} y={yOf(t)} dy="0.32em" textAnchor="end" fontSize="10" fill="var(--color-muted)" style={{ fontVariantNumeric: "tabular-nums" }}>
              {price(String(t))}
            </text>
          </g>
        ))}
        <line x1={M.left} x2={W - M.right} y1={M.top + PH} y2={M.top + PH} stroke="var(--color-axis)" strokeWidth="1" />
        {["09:15", "10:30", "12:00", "13:30", "15:00"].map((label) => {
          const [h, m] = label.split(":").map(Number);
          const slot = (h * 60 + m - 555) / 5;
          return (
            <text key={label} x={edgeOf(slot)} y={H - 8} textAnchor="middle" fontSize="10" fill="var(--color-muted)">{label}</text>
          );
        })}

        {/* reference window 10:30-10:50 */}
        <rect x={edgeOf(refStart)} y={M.top} width={STEP * refCount} height={PH} fill="var(--color-ink)" fillOpacity="0.05" />

        {/* fixed range band */}
        {ref && (
          <g>
            <rect x={edgeOf(refStart)} y={yOf(ref.high)} width={Math.max(STEP * refCount, edgeOf(bandEnd) - edgeOf(refStart))}
              height={Math.max(1, yOf(ref.low) - yOf(ref.high))} fill="var(--color-accent)" fillOpacity="0.1" />
            {[ref.high, ref.low].map((level) => (
              <line key={level} x1={edgeOf(refStart)} x2={Math.max(edgeOf(refStart + refCount), edgeOf(bandEnd))} y1={yOf(level)} y2={yOf(level)}
                stroke="var(--color-accent)" strokeWidth="1" />
            ))}
          </g>
        )}

        {/* candles */}
        {candles.map((c) => {
          const slot = slotOf(c.start);
          const up = Number(c.close) >= Number(c.open);
          const color = up ? "var(--color-up)" : "var(--color-down)";
          const top = yOf(up ? c.close : c.open);
          const height = Math.max(1, Math.abs(yOf(c.open) - yOf(c.close)));
          return (
            <g key={c.start}>
              <line x1={xOf(slot)} x2={xOf(slot)} y1={yOf(c.high)} y2={yOf(c.low)} stroke={color} strokeWidth="1" />
              <rect x={xOf(slot) - body / 2} y={top} width={body} height={height}
                fill={up ? "var(--color-surface)" : color} stroke={color} strokeWidth="1" />
            </g>
          );
        })}

        {/* breakout marker */}
        {breakout && (
          <g>
            <path
              d={breakoutBelow
                ? `M${breakoutX - 4} ${yOf(breakout.candle.low) + 6} h8 l-4 6 z`
                : `M${breakoutX - 4} ${yOf(breakout.candle.high) - 6} h8 l-4 -6 z`}
              fill="var(--color-ink-2)" />
            <text x={breakoutX} y={breakoutBelow ? Math.min(H - 32, yOf(breakout.candle.low) + 24) : Math.max(12, yOf(breakout.candle.high) - 16)}
              textAnchor="middle" fontSize="10" fill="var(--color-ink-2)" {...HALO}>
              {cancelled ? "Cancelled" : trigger ? "Confirmed" : "Breakout"} {hhmm(breakout.candle_start)}
            </text>
          </g>
        )}

        {trigger && (
          <g>
            <circle cx={xOf(slotOf(trigger.candle_start))} cy={yOf(trigger.extreme_value)} r="3.5" fill="var(--color-accent)" />
            <text x={xOf(slotOf(trigger.candle_start))}
              y={trigger.side === "above" ? Math.max(12, yOf(trigger.extreme_value) - 12) : Math.min(H - 30, yOf(trigger.extreme_value) + 20)}
              textAnchor="middle" fontSize="10" fill="var(--color-accent)" {...HALO}>
              First break {hhmm(trigger.candle_start)}
            </text>
          </g>
        )}

        {/* entry marker */}
        {entry && (
          <g>
            <circle cx={entryX} cy={yOf(entry.price)} r="6" fill="var(--color-surface)" />
            <circle cx={entryX} cy={yOf(entry.price)} r="4" fill={entry.signal === "long" ? "var(--color-up)" : "var(--color-down)"} />
            <text x={entryLabelLeft ? entryX - 10 : entryX + 10} y={yOf(entry.price)} dy="0.32em"
              textAnchor={entryLabelLeft ? "end" : "start"} fontSize="11" fontWeight="600" fill="var(--color-ink)" {...HALO}>
              Entry {inr(entry.price)}
            </text>
          </g>
        )}

        {/* initial stop-loss level (09:45 window): drawn from the entry onward; no stop hit is computed */}
        {stop && stopFromX !== null && (
          <g>
            <line x1={stopFromX} x2={W - M.right} y1={yOf(stop)} y2={yOf(stop)} stroke="var(--color-ink-2)"
              strokeWidth="1.25" strokeDasharray="5 4" />
            <text x={W - M.right} y={yOf(stop) - 5} textAnchor="end" fontSize="10.5" fontWeight="600"
              fill="var(--color-ink)" {...HALO}>
              Stop {inr(stop)}
            </text>
          </g>
        )}

        {/* hover crosshair */}
        {hovered && (
          <line x1={xOf(hover)} x2={xOf(hover)} y1={M.top} y2={M.top + PH} stroke="var(--color-axis)" strokeWidth="1" pointerEvents="none" />
        )}
        <rect x={M.left} y={M.top} width={PW} height={PH} fill="transparent" />
      </svg>

      {hovered && (
        <div
          className="pointer-events-none absolute top-2 z-10 rounded-md border border-hairline bg-raised px-2.5 py-1.5 text-xs shadow-md shadow-black/5"
          style={{ left: `${(xOf(hover) / W) * 100}%`, transform: xOf(hover) > W / 2 ? "translateX(calc(-100% - 10px))" : "translateX(10px)" }}
        >
          <div className="mb-1 font-medium text-ink-2">{hhmm(hovered.start)} – {hhmm(hovered.end)}</div>
          <div className="grid grid-cols-[auto_auto] gap-x-3 tabular-nums">
            {["open", "high", "low", "close"].map((k) => (
              <div key={k} className="contents">
                <span className="font-semibold text-ink">{price(hovered[k])}</span>
                <span className="text-muted capitalize">{k}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-2">
        <span className="inline-flex items-center gap-1.5"><span className="inline-block h-2.5 w-2 border border-up bg-surface" />Up candle (hollow)</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block h-2.5 w-2 bg-down" />Down candle (filled)</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block h-2.5 w-4 bg-ink/10" />Reference window ({refCandles[0]}–{refCandles[refCount - 1]})</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block h-2.5 w-4 border-y border-accent bg-accent/10" />Fixed range</span>
        {entry && <span className="inline-flex items-center gap-1.5"><span className={`inline-block size-2 rounded-full ${entry.signal === "long" ? "bg-up" : "bg-down"}`} />Entry (next candle open)</span>}
        {stop && <span className="inline-flex items-center gap-1.5"><span className="inline-block w-4 border-t-[1.5px] border-dashed border-ink-2" />Initial stop loss</span>}
      </div>
    </div>
  );
}
