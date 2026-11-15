import { useEffect, useRef, useState } from "react";
import Icon, { Spinner } from "./Icon.jsx";
import { NIFTY_50 } from "../lib/presets.js";

const KIND_STYLE = {
  stock: { label: "Stock", className: "bg-accent/10 text-ink" },
  future: { label: "Future", className: "bg-serious/15 text-ink" },
  index: { label: "Index", className: "bg-ink/5 text-ink-2" },
};

function expiryLabel(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });
}

// Chips for chosen stocks plus a search box with stock / future / index suggestions.
// Only stocks can be added; futures and indices are shown, labeled, and disabled.
export default function StockPicker({ provider, values, onChange }) {
  const [text, setText] = useState("");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => {
    const query = text.trim();
    if (!query || query.includes(",")) {
      setItems([]);
      setError("");
      return undefined;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ provider, query, limit: "12" });
        const response = await fetch(`/v1/instruments?${params}`, { signal: controller.signal });
        const body = await response.json();
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Error ${response.status}`);
        setItems(body.results);
        setError("");
        setActive(body.results.findIndex((item) => item.scannable));
      } catch (err) {
        if (err.name !== "AbortError") {
          setItems([]);
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    }, 180);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [text, provider]);

  useEffect(() => {
    const close = (event) => !boxRef.current?.contains(event.target) && setOpen(false);
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  const add = (symbols) => {
    const next = [...values];
    for (const raw of symbols) {
      const symbol = raw.trim();
      if (symbol && !next.some((v) => v.toLowerCase() === symbol.toLowerCase())) next.push(symbol);
    }
    onChange(next);
  };

  const choose = (item) => {
    if (!item?.scannable) return;
    add([item.symbol]);
    setText("");
    setItems([]);
    inputRef.current?.focus();
  };

  const commitText = () => {
    if (text.trim()) add(text.split(","));
    setText("");
  };

  const onKeyDown = (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      if (!items.length) return;
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((index) => (index + step + items.length) % items.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (open && items[active]?.scannable) choose(items[active]);
      else if (text.trim()) commitText();
    } else if (event.key === ",") {
      event.preventDefault();
      commitText();
    } else if (event.key === "Backspace" && !text && values.length) {
      onChange(values.slice(0, -1));
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  const onPaste = (event) => {
    const pasted = event.clipboardData.getData("text");
    if (/[,\n]/.test(pasted)) {
      event.preventDefault();
      add(pasted.split(/[,\n]/));
    }
  };

  const showList = open && text.trim() && (items.length > 0 || loading || error);

  return (
    <div ref={boxRef} className="relative">
      <div
        className="flex min-h-11 flex-wrap items-center gap-1.5 rounded-lg border border-hairline bg-raised px-2 py-1.5 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20"
        onClick={() => inputRef.current?.focus()}
      >
        {values.map((symbol) => (
          <span key={symbol} className="inline-flex items-center gap-1 rounded-md bg-ink/5 py-0.5 pl-2 pr-1 text-xs font-medium">
            {symbol}
            <button
              type="button"
              aria-label={`Remove ${symbol}`}
              className="rounded p-0.5 text-muted hover:bg-ink/10 hover:text-ink"
              onClick={(event) => {
                event.stopPropagation();
                onChange(values.filter((v) => v !== symbol));
              }}
            >
              <Icon name="close" className="size-3" />
            </button>
          </span>
        ))}
        <div className="flex min-w-48 flex-1 items-center gap-2 px-1">
          <Icon name="search" className="size-4 shrink-0 text-muted" />
          <input
            ref={inputRef}
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            placeholder={values.length ? "Add another stock…" : "Search by name or symbol, e.g. HCL Technologies"}
            className="h-7 w-full bg-transparent text-sm outline-none placeholder:text-muted"
            role="combobox"
            aria-expanded={Boolean(showList)}
            aria-controls="stock-suggestions"
            aria-autocomplete="list"
          />
          {loading && <Spinner className="size-4 text-muted" />}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-2">
        <span>{values.length ? `${values.length} stock${values.length > 1 ? "s" : ""} selected` : "No stocks selected"}</span>
        <span className="text-axis">·</span>
        <button type="button" onClick={() => add(NIFTY_50.symbols)} className="rounded-md border border-hairline bg-raised px-2 py-0.5 font-medium text-ink hover:bg-ink/5" title={`NSE Indices list as of ${NIFTY_50.asOf}`}>
          + {NIFTY_50.label} stocks
        </button>
        {values.length > 0 && (
          <button type="button" onClick={() => onChange([])} className="rounded-md px-2 py-0.5 text-ink-2 hover:bg-ink/5 hover:text-ink">
            Clear all
          </button>
        )}
      </div>

      {showList && (
        <ul id="stock-suggestions" role="listbox" className="absolute z-20 mt-1 max-h-96 w-full overflow-auto rounded-lg border border-hairline bg-raised py-1 shadow-lg shadow-black/5">
          {error && <li className="px-3 py-2 text-sm text-ink-2">Suggestions unavailable: {error}</li>}
          {!error && !items.length && loading && <li className="px-3 py-2 text-sm text-muted">Searching…</li>}
          {items.map((item, index) => {
            const kind = KIND_STYLE[item.kind];
            const added = values.some((v) => v.toLowerCase() === item.symbol.toLowerCase());
            return (
              <li
                key={`${item.kind}-${item.symbol}`}
                role="option"
                aria-selected={index === active}
                aria-disabled={!item.scannable}
                onPointerEnter={() => setActive(index)}
                onPointerDown={(event) => {
                  event.preventDefault();
                  choose(item);
                }}
                className={`flex items-start justify-between gap-3 px-3 py-2 ${index === active ? "bg-ink/5" : ""} ${item.scannable ? "cursor-pointer" : "cursor-not-allowed"}`}
              >
                <div className={`min-w-0 ${item.scannable ? "" : "opacity-60"}`}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{item.symbol}</span>
                    {item.synthetic && <span className="text-xs text-muted">synthetic</span>}
                  </div>
                  <div className="truncate text-xs text-ink-2">{item.name}</div>
                  {!item.scannable && index === active && <div className="mt-0.5 text-xs text-ink-2">{item.note}</div>}
                </div>
                <div className="flex shrink-0 items-center gap-2 pt-0.5">
                  {item.kind === "future" && item.expiry && (
                    <span className="text-xs tabular-nums text-ink-2">
                      {expiryLabel(item.expiry)}
                      {item.lot_size ? ` · lot ${item.lot_size}` : ""}
                    </span>
                  )}
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${kind.className}`}>{kind.label}</span>
                  {added && <Icon name="check" className="size-4 text-accent" />}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
