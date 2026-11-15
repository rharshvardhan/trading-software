import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";

const media = () => window.matchMedia("(prefers-color-scheme: dark)");

function stored() {
  try {
    const value = localStorage.getItem("theme");
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

// Sun/moon toggle. Starts from the system setting; a click picks light or dark and remembers it.
export default function ThemeToggle() {
  const [choice, setChoice] = useState(stored);
  const [systemDark, setSystemDark] = useState(() => media().matches);

  useEffect(() => {
    const query = media();
    const update = (event) => setSystemDark(event.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (choice) root.dataset.theme = choice;
    else delete root.dataset.theme;
    try {
      if (choice) localStorage.setItem("theme", choice);
      else localStorage.removeItem("theme");
    } catch {
      /* storage unavailable: the toggle still works for this visit */
    }
  }, [choice]);

  const dark = choice ? choice === "dark" : systemDark;
  const next = dark ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setChoice(next)}
      onDoubleClick={() => setChoice(null)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode (double-click to follow the system)`}
      className="inline-flex size-8 items-center justify-center rounded-full border border-hairline bg-raised text-ink-2 transition-colors hover:text-ink"
    >
      <Icon name={dark ? "sun" : "moon"} className="size-4" />
    </button>
  );
}
