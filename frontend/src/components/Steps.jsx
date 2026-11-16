import Icon from "./Icon.jsx";
import { hhmm, inr, price } from "../lib/format.js";

const LOOK = {
  done: { icon: "check", ring: "bg-accent/12 text-accent" },
  fail: { icon: "x", ring: "bg-ink/5 text-muted" },
  pending: { icon: "clock", ring: "bg-accent/10 text-accent" },
  question: { icon: "question", ring: "bg-warning/20 text-warning" },
  alert: { icon: "alert", ring: "bg-serious/15 text-serious" },
  idle: { icon: "dash", ring: "bg-ink/5 text-muted" },
};

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

// The four strategy steps for one stock, each with its outcome in plain words.
const DEFAULT_WINDOW = { reference_candles: ["10:30", "10:35", "10:40", "10:45"], qualification_window: "09:15-10:45", range_final_at: "10:50" };

export function buildSteps(r, window = DEFAULT_WINDOW, stopEnabled = true) {
  const first = window.reference_candles[0];
  const last = window.reference_candles[window.reference_candles.length - 1];
  const q = r.qualification;
  const ref = r.reference;
  const b = r.breakout;
  const e = r.entry;
  const k = r.cancellation;
  const t = r.trigger;
  const twoStage = r.entry_rule === "break_then_confirm";
  const missing = r.data?.missing_candles?.length ? `Missing candles: ${r.data.missing_candles.slice(0, 6).join(", ")}${r.data.missing_candles.length > 6 ? "…" : ""}` : "Data incomplete";

  const code = r.rule_decision?.code;
  const setup = q?.permitted_signal; // "short" after a new morning high, "long" after a new morning low
  // Two-stage (09:45) wording: SHORT breaks/confirms below the reference low, LONG above the reference high.
  const dir = setup === "long" ? "above" : "below";
  const level = setup === "long" ? "high" : "low";
  let s1;
  if (q?.decision === "qualified") {
    const parts = [];
    if (q.high_side.status === "new_extreme") parts.push(`new session high ${price(q.high_side.reference_value)} at ${q.high_side.reference_candles.join(", ")}`);
    if (q.low_side.status === "new_extreme") parts.push(`new session low ${price(q.low_side.reference_value)} at ${q.low_side.reference_candles.join(", ")}`);
    if (code === "both_sides_qualified") s1 = ["question", `${cap(parts.join(" and "))}; which direction to trade is your rule decision`];
    else if (code === "equal_repeated_extreme") s1 = ["question", `${cap(parts.join(""))}, but the other side only ties an earlier extreme; direction depends on your tie rule`];
    else s1 = ["done", `${cap(parts.join(" and "))} → ${setup?.toUpperCase()} setup`];
  } else if (q?.decision === "not_qualified") {
    s1 = ["fail", `Earlier high ${price(q.high_side.earlier_value)} (${q.high_side.earlier_candles.join(", ")}) and low ${price(q.low_side.earlier_value)} (${q.low_side.earlier_candles.join(", ")}) are outside the four candles`];
  } else if (q?.decision === "needs_rule_decision") {
    s1 = ["question", "Only equals an earlier morning high or low; your tie rule is needed"];
  } else if (r.state === "waiting_for_reference") {
    s1 = ["pending", `The ${first}–${last} candles finish at ${window.range_final_at}`];
  } else if (r.state === "invalid_data") {
    s1 = ["alert", missing];
  } else {
    s1 = ["idle", "Not evaluated"];
  }

  const s2 = ref ? ["done", `${price(ref.low)} – ${price(ref.high)}`] : ["idle", "Not formed"];

  let s3 = ["idle", "Not reached"];
  if (k?.trigger_basis && k.trigger_basis !== "close") s3 = ["fail", `${hhmm(k.candle_start)} candle ${k.trigger_basis} ${price(k.candle[k.trigger_basis])} breached ${price(k.boundary_value)} before entry: setup cancelled (wick is sufficient)`];
  else if (k) s3 = ["fail", `${hhmm(k.candle_start)} candle closed ${price(k.close)}, ${k.side} ${price(k.boundary_value)} (wrong direction): setup cancelled at ${hhmm(k.confirmed_at)}`];
  else if (t && code === "gap_beyond_range") s3 = ["question", `The first break lies entirely ${t.side} the range; your gap rule is needed`];
  else if (b && code === "gap_beyond_range") s3 = ["question", `${hhmm(b.candle_start)} candle lies entirely ${b.side} the range; your gap rule is needed`];
  else if (b) s3 = ["done", `${hhmm(b.candle_start)} candle closed ${price(b.close)}, ${b.side} ${price(b.boundary_value)}`];
  else if (r.state === "waiting_for_confirmation") s3 = ["pending", `First break observed; waiting for a later candle to finish with its close ${dir} the reference ${level}`];
  else if (r.state === "waiting_for_breakout") s3 = ["pending", twoStage ? `No first ${level} break yet` : "No close outside the range yet"];
  else if (r.state === "no_breakout") s3 = ["fail", t ? `No later candle confirmed ${dir} the reference ${level}` : "No candle closed outside the range"];
  else if (r.state === "invalid_data" && q?.decision === "qualified") s3 = ["alert", missing];

  let s4 = ["idle", "Not reached"];
  if (e?.time) s4 = ["done", `${cap(e.signal)} at the ${hhmm(e.time)} open · ${inr(e.price)}`];
  else if (r.state === "awaiting_entry") s4 = ["pending", `At the ${hhmm(e.expected_time)} open (not available yet)`];
  else if (r.state === "entry_unavailable_session_end") s4 = ["fail", "Breakout on the last candle; no same-day entry"];
  else if (k) s4 = ["fail", "No entry: the setup was cancelled, and a later break does not revive it"];
  else if (twoStage && r.state === "no_breakout") s4 = ["fail", "No entry: a later confirmation close was not established before session end"];
  else if (r.state === "invalid_data" && b) s4 = ["alert", `The ${hhmm(e?.expected_time)} candle is missing; nothing substituted`];
  else if (twoStage && !b && t) s4 = ["pending", "No entry until a later candle confirms; entry will use the following candle's open"];

  // Fifth step only for an entry (made or pending): the 09:45 window has a taught initial stop level.
  let s5 = null;
  if (r.risk?.stop_loss) s5 = ["done", `${inr(r.risk.stop_loss)}: the ${r.risk.stop_loss_basis}. Stop-hit and exit rules are not yet defined`];
  else if ((e?.time || r.state === "awaiting_entry") && r.strategy_window === "0945_three_candle" && !stopEnabled)
    s5 = ["idle", "Turned off: set STOP_LOSS_ENABLED=true in .env to show this window's initial stop level"];
  else if (e?.time || r.state === "awaiting_entry") s5 = ["idle", "Not defined for this window yet"];

  return [
    { title: "Morning extreme", hint: window.qualification_window.replace("-", "–"), status: s1[0], detail: s1[1] },
    { title: "Fixed range", hint: `${first}–${last} candles`, status: s2[0], detail: s2[1] },
    ...(twoStage ? [{ title: "First break", hint: `wick or close ${dir} the range`, status: t ? "done" : k ? "fail" : "pending", detail: t ? `${hhmm(t.candle_start)} candle ${t.side === "above" ? "high" : "low"} ${price(t.extreme_value)}, ${t.side} ${price(t.boundary_value)}` : k ? "Cancelled before a valid first break" : `Waiting for the first ${level} breach` }] : []),
    { title: twoStage ? "Confirmation close" : "Breakout close", hint: setup ? `close ${setup === "short" ? "below" : "above"} the range` : "first close outside", status: s3[0], detail: s3[1] },
    { title: "Entry", hint: twoStage ? "open after confirmation" : "next candle open", status: s4[0], detail: s4[1] },
    ...(s5 ? [{ title: "Initial stop loss", hint: r.risk?.stop_loss ? "09:45 rule" : r.strategy_window === "0945_three_candle" && !stopEnabled ? "switched off" : "not taught", status: s5[0], detail: s5[1] }] : []),
  ];
}

export default function Steps({ result, window, stopEnabled }) {
  const steps = buildSteps(result, window, stopEnabled);
  return (
    <ol className="space-y-0">
      {steps.map((step, index) => {
        const look = LOOK[step.status];
        return (
          <li key={step.title} className="relative flex gap-3 pb-4 last:pb-0">
            {index < steps.length - 1 && <span className="absolute left-3.5 top-8 h-[calc(100%-2rem)] w-px bg-grid" aria-hidden="true" />}
            <span className={`relative flex size-7 shrink-0 items-center justify-center rounded-full ${look.ring}`}>
              <Icon name={look.icon} className="size-4" />
            </span>
            <div className="min-w-0 pt-0.5">
              <div className="text-sm font-medium">
                {index + 1}. {step.title} <span className="font-normal text-muted">· {step.hint}</span>
              </div>
              <div className="text-sm text-ink-2">{step.detail}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
