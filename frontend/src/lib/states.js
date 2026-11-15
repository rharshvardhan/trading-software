// How each backend result state is shown. Every status carries an icon and a label,
// never color alone.

export const STATE_META = {
  entry_identified: { group: "entry", label: "Entry", tone: "accent", icon: "check" },
  awaiting_entry: { group: "waiting", label: "Breakout · entry pending", tone: "accent", icon: "clock" },
  waiting_for_breakout: { group: "waiting", label: "Waiting for breakout", tone: "accent", icon: "clock" },
  waiting_for_reference: { group: "waiting", label: "Range forms at 10:50", tone: "accent", icon: "clock" },
  no_breakout: { group: "none", label: "No breakout", tone: "neutral", icon: "dash" },
  entry_unavailable_session_end: { group: "none", label: "Breakout at close", tone: "neutral", icon: "dash" },
  not_qualified: { group: "none", label: "Not qualified", tone: "neutral", icon: "x" },
  no_session: { group: "none", label: "No trading session", tone: "neutral", icon: "dash" },
  needs_rule_decision: { group: "attention", label: "Needs your rule", tone: "warning", icon: "question" },
  invalid_data: { group: "attention", label: "Data incomplete", tone: "serious", icon: "alert" },
  symbol_error: { group: "attention", label: "Unknown stock", tone: "critical", icon: "alert" },
  provider_error: { group: "attention", label: "Data error", tone: "critical", icon: "alert" },
};

export const GROUP_ORDER = ["entry", "waiting", "attention", "none"];

export function metaFor(result) {
  const meta = STATE_META[result.state] ?? { group: "attention", label: result.state, tone: "neutral", icon: "dash" };
  if (result.state === "entry_identified" && result.entry) {
    const long = result.entry.signal === "long";
    return { ...meta, label: long ? "Long entry" : "Short entry", tone: long ? "up" : "down", icon: long ? "up" : "down" };
  }
  return meta;
}

// Full class strings so Tailwind can see them at build time.
export const TONES = {
  up: { soft: "bg-up/12", icon: "text-up" },
  down: { soft: "bg-down/12", icon: "text-down" },
  accent: { soft: "bg-accent/10", icon: "text-accent" },
  neutral: { soft: "bg-ink/5", icon: "text-muted" },
  warning: { soft: "bg-warning/20", icon: "text-warning" },
  serious: { soft: "bg-serious/15", icon: "text-serious" },
  critical: { soft: "bg-critical/12", icon: "text-critical" },
};
