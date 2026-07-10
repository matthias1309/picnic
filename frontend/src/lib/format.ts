export function formatCents(cents: number): string {
  return (cents / 100).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  });
}

export function getCurrentMonth(today: Date = new Date()): string {
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

/** Returns the `n` months immediately preceding the month of `today`, most recent first. */
export function getPastMonths(n: number, today: Date = new Date()): string[] {
  const months: string[] = [];
  for (let i = 1; i <= n; i++) {
    const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
    months.push(getCurrentMonth(date));
  }
  return months;
}

const RANGE_MONTHS: Record<string, number> = {
  "3m": 3,
  "6m": 6,
  "12m": 12,
};

/** Returns the ISO from-date for a price-history range, or undefined for "all". */
export function rangeToFromDate(range: string, today: Date = new Date()): string | undefined {
  const months = RANGE_MONTHS[range];
  if (months === undefined) {
    return undefined;
  }
  const from = new Date(today);
  from.setMonth(from.getMonth() - months);
  return from.toISOString().slice(0, 10);
}
