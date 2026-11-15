import Icon from "./Icon.jsx";
import { TONES, metaFor } from "../lib/states.js";

export default function StatusBadge({ result }) {
  const meta = metaFor(result);
  const tone = TONES[meta.tone];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium text-ink ${tone.soft}`}>
      <Icon name={meta.icon} className={`size-3.5 ${tone.icon}`} />
      {meta.label}
    </span>
  );
}
