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
export function buildSteps(r) {
  const q = r.qualification;
  const ref = r.reference;
  const b = r.breakout;
  const e = r.entry;
  const missing = r.data?.missing_candles?.length ? `Missing candles: ${r.data.missing_candles.slice(0, 6).join(", ")}${r.data.missing_candles.length > 6 ? "…" : ""}` : "Data incomplete";

  let s1;
  if (q?.decision === "qualified") {
    const parts = [];
    if (q.high_side.status === "new_extreme") parts.push(`new session high ${price(q.high_side.reference_value)} at ${q.high_side.reference_candles.join(", ")}`);
    if (q.low_side.status === "new_extreme") parts.push(`new session low ${price(q.low_side.reference_value)} at ${q.low_side.reference_candles.join(", ")}`);
    s1 = ["done", cap(parts.join(" and "))];
  } else if (q?.decision === "not_qualified") {
    s1 = ["fail", `Earlier high ${price(q.high_side.earlier_value)} (${q.high_side.earlier_candles.join(", ")}) and low ${price(q.low_side.earlier_value)} (${q.low_side.earlier_candles.join(", ")}) are outside the four candles`];
  } else if (q?.decision === "needs_rule_decision") {
    s1 = ["question", "Only equals an earlier morning high or low; your tie rule is needed"];
  } else if (r.state === "waiting_for_reference") {
    s1 = ["pending", "The 10:30–10:45 candles finish at 10:50"];
  } else if (r.state === "invalid_data") {
    s1 = ["alert", missing];
  } else {
    s1 = ["idle", "Not evaluated"];
  }

  const s2 = ref ? ["done", `${price(ref.low)} – ${price(ref.high)}`] : ["idle", "Not formed"];

  let s3 = ["idle", "Not reached"];
  if (b && r.state === "needs_rule_decision") s3 = ["question", `${hhmm(b.candle_start)} candle lies entirely ${b.side} the range; your gap rule is needed`];
  else if (b) s3 = ["done", `${hhmm(b.candle_start)} candle closed ${price(b.close)}, ${b.side} ${price(b.boundary_value)}`];
  else if (r.state === "waiting_for_breakout") s3 = ["pending", "No close outside the range yet"];
  else if (r.state === "no_breakout") s3 = ["fail", "No candle closed outside the range"];
  else if (r.state === "invalid_data" && q?.decision === "qualified") s3 = ["alert", missing];

  let s4 = ["idle", "Not reached"];
  if (e?.time) s4 = ["done", `${cap(e.signal)} at the ${hhmm(e.time)} open · ${inr(e.price)}`];
  else if (r.state === "awaiting_entry") s4 = ["pending", `At the ${hhmm(e.expected_time)} open (not available yet)`];
  else if (r.state === "entry_unavailable_session_end") s4 = ["fail", "Breakout on the last candle; no same-day entry"];
  else if (r.state === "invalid_data" && b) s4 = ["alert", `The ${hhmm(e?.expected_time)} candle is missing; nothing substituted`];

  return [
    { title: "Morning extreme", hint: "09:15–10:45", status: s1[0], detail: s1[1] },
    { title: "Fixed range", hint: "10:30–10:45 candles", status: s2[0], detail: s2[1] },
    { title: "Breakout close", hint: "first close outside", status: s3[0], detail: s3[1] },
    { title: "Entry", hint: "next candle open", status: s4[0], detail: s4[1] },
  ];
}

export default function Steps({ result }) {
  const steps = buildSteps(result);
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
