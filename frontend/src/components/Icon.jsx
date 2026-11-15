// Small inline icons (16px grid, stroke = currentColor).
const PATHS = {
  check: <path d="M3.5 8.5l3 3 6-7" />,
  x: <path d="M4.5 4.5l7 7m0-7l-7 7" />,
  dash: <path d="M4 8h8" />,
  clock: <><circle cx="8" cy="8" r="5.5" /><path d="M8 5v3.2l2 1.3" /></>,
  question: <><path d="M6.2 6.2a1.9 1.9 0 113 1.5c-.8.5-1.2.9-1.2 1.8" /><path d="M8 11.6v.1" /></>,
  alert: <><path d="M8 2.5l6 10.5H2z" /><path d="M8 6.5v3M8 11.3v.1" /></>,
  up: <path d="M8 3.5l4.5 6h-9z" fill="currentColor" />,
  down: <path d="M8 12.5l4.5-6h-9z" fill="currentColor" />,
  chevron: <path d="M6 4l4 4-4 4" />,
  search: <><circle cx="7" cy="7" r="4.5" /><path d="M10.5 10.5L14 14" /></>,
  close: <path d="M5 5l6 6m0-6l-6 6" />,
  sun: <><circle cx="8" cy="8" r="3" /><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1" /></>,
  moon: <path d="M13.5 9.8A5.5 5.5 0 016.2 2.5a5.5 5.5 0 107.3 7.3z" />,
};

export default function Icon({ name, className = "size-4" }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}

export function Spinner({ className = "size-4" }) {
  return (
    <svg viewBox="0 0 16 16" className={`${className} animate-spin`} aria-hidden="true">
      <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
      <path d="M14 8a6 6 0 00-6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
