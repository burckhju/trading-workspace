export function chartRangeStart(end: string, months: string): string | null {
  if (months === 'all') return null;
  const [year, month, day] = end.split('-').map(Number);
  const first = new Date(Date.UTC(year, month - 1 - Number(months), 1));
  const lastDay = new Date(
    Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0),
  ).getUTCDate();
  first.setUTCDate(Math.min(day, lastDay));
  return first.toISOString().slice(0, 10);
}
