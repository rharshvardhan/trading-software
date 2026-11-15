// Display helpers. Prices arrive as decimal strings and are never rounded.

export function price(value) {
  if (value === null || value === undefined) return "—";
  const [whole, fraction = ""] = String(value).split(".");
  const negative = whole.startsWith("-");
  const digits = negative ? whole.slice(1) : whole;
  const grouped =
    digits.length > 3
      ? digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + digits.slice(-3)
      : digits;
  return `${negative ? "-" : ""}${grouped}.${fraction.padEnd(2, "0")}`;
}

export const inr = (value) => (value === null || value === undefined ? "—" : `₹${price(value)}`);

// Backend times are ISO strings in +05:30, so the wall-clock part is already IST.
export const hhmm = (iso) => (iso ? iso.slice(11, 16) : "—");

export function longDate(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}

export function todayIST() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

// Most recent weekday on or before today (exchange holidays are not known here).
export function lastWeekdayIST() {
  const [y, m, d] = todayIST().split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  while ([0, 6].includes(date.getUTCDay())) date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
}

export const isWeekend = (isoDate) => {
  const [y, m, d] = isoDate.split("-").map(Number);
  return [0, 6].includes(new Date(Date.UTC(y, m - 1, d)).getUTCDay());
};
