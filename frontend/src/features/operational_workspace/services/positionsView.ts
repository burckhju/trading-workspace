import type { OperationalPosition } from '../types';

export const positionFilters = {
  all: 'Alle offenen Positionen',
  alerts: 'Fachliche Hinweise',
  data: 'Datenprobleme',
  gains: 'Gewinn',
  losses: 'Verlust',
} as const;
export const positionSorts = {
  attention: 'Aufmerksamkeit',
  product: 'Produkt',
  purchased: 'Kaufdatum',
  quantity: 'Stück',
  value: 'Marktwert (je Währung)',
  pnl: 'G/V (je Währung)',
  quote: 'Kurszeitpunkt',
} as const;
export type PositionFilter = keyof typeof positionFilters;
export type PositionSort = keyof typeof positionSorts;
export interface PositionsView {
  query: string;
  filter: PositionFilter;
  sort: PositionSort;
  descending: boolean;
  pageSize: 25 | 50 | 100;
  page: number;
}
export const defaultPositionsView: PositionsView = {
  query: '',
  filter: 'all',
  sort: 'attention',
  descending: false,
  pageSize: 25,
  page: 1,
};
export const positionsViewKey = 'workspace-positions-view-v1';

/** Only presentation preferences, never transaction state, are kept in this tab. */
export function readPositionsView(): PositionsView {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(positionsViewKey) ?? 'null');
    if (!value || typeof value !== 'object') return { ...defaultPositionsView };
    const v = value as Record<string, unknown>;
    return {
      query: typeof v.query === 'string' ? v.query.slice(0, 200) : '',
      filter:
        typeof v.filter === 'string' && Object.hasOwn(positionFilters, v.filter)
          ? (v.filter as PositionFilter)
          : 'all',
      sort:
        typeof v.sort === 'string' && Object.hasOwn(positionSorts, v.sort)
          ? (v.sort as PositionSort)
          : 'attention',
      descending: v.descending === true,
      pageSize: v.pageSize === 50 || v.pageSize === 100 ? v.pageSize : 25,
      page: typeof v.page === 'number' && Number.isSafeInteger(v.page) && v.page > 0 ? v.page : 1,
    };
  } catch {
    return { ...defaultPositionsView };
  }
}
export function savePositionsView(view: PositionsView): void {
  try {
    sessionStorage.setItem(positionsViewKey, JSON.stringify(view));
  } catch {
    /* Optional convenience only. */
  }
}

// Backend monetary values have at most ten fractional digits. Keep sums and sorting
// exact; never aggregate binary floating-point amounts or mix valuation currencies.
export function decimalUnits(value: string | null | undefined): bigint | null {
  if (value == null || value.length > 120) return null;
  const match = /^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const exponent = Number(match[4] ?? 0);
  if (Math.abs(exponent) > 30) return null;
  let units = BigInt(match[2] + (match[3] ?? '')) * (match[1] === '-' ? -1n : 1n);
  const power = 10 + exponent - (match[3]?.length ?? 0);
  if (power < 0) {
    const divisor = 10n ** BigInt(-power);
    if (units % divisor !== 0n) return null;
    units /= divisor;
  } else units *= 10n ** BigInt(power);
  return units;
}
export function formatUnits(value: bigint, digits = 2, signed = false): string {
  const divisor = 10n ** BigInt(10 - digits);
  const absolute = value < 0n ? -value : value;
  const rounded = (absolute + divisor / 2n) / divisor;
  const unit = 10n ** BigInt(digits);
  const whole = new Intl.NumberFormat('de-DE').format(rounded / unit);
  const fraction = digits ? `,${String(rounded % unit).padStart(digits, '0')}` : '';
  return `${value < 0n ? '−' : signed && value > 0n ? '+' : ''}${whole}${fraction}`;
}
export function money(value: string | null, currency: string | null, signed = false): string {
  const units = decimalUnits(value);
  return units === null
    ? '—'
    : `${formatUnits(units, 2, signed)} ${currency ?? '(Währung ungeklärt)'}`;
}
export function numberLabel(value: string | null): string {
  const units = decimalUnits(value);
  if (units === null) return '—';
  return formatUnits(units, 10).replace(/,?0+$/, '').replace(/,$/, '');
}
export function pnlClass(value: string | null): string {
  const units = decimalUnits(value);
  return units === null || units === 0n
    ? 'text-slate-300'
    : units > 0n
      ? 'text-emerald-300'
      : 'text-rose-300';
}
export function hasAlert(p: OperationalPosition): boolean {
  return (
    p.open_alert_count > 0 ||
    (p.position_signal?.quality_status === 'AVAILABLE' &&
      (p.position_signal.alert_level === 'CRITICAL' ||
        p.position_signal.alert_level === 'ATTENTION'))
  );
}
export function hasDataProblem(p: OperationalPosition): boolean {
  return (
    p.monitoring_status !== 'OK' ||
    p.valuation_status !== 'AVAILABLE' ||
    Boolean(p.analysis_warning) ||
    p.market_value === null ||
    p.unrealized_gross_pnl === null ||
    !p.valuation_currency ||
    p.position_signal?.quality_status !== 'AVAILABLE' ||
    !p.position_signal.alert_level
  );
}
export type StatusTone = 'critical' | 'attention' | 'data' | 'ok';
export function positionTone(p: OperationalPosition): StatusTone {
  if (
    p.open_alert_types.includes('STOP_REACHED') ||
    (p.position_signal?.quality_status === 'AVAILABLE' &&
      p.position_signal.alert_level === 'CRITICAL')
  )
    return 'critical';
  if (hasAlert(p)) return 'attention';
  return hasDataProblem(p) ? 'data' : 'ok';
}
const rank: Record<StatusTone, number> = { critical: 0, attention: 1, data: 2, ok: 3 };
export function purchaseDate(p: OperationalPosition): string | null {
  if (p.opened_on) return p.opened_on;
  const d = new Date(p.opened_at);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
export function dateLabel(date: string | null): string {
  return date ? date.split('-').reverse().join('.') : '—';
}
export function timeLabel(time: string | null | undefined): string {
  return time && Number.isFinite(Date.parse(time))
    ? new Date(time).toLocaleString('de-DE')
    : 'Unbekannt';
}
function compare<T extends string | number | bigint>(
  a: T | null,
  b: T | null,
  descending: boolean,
): number {
  // Missing is always last, including descending sorts; zero is not missing.
  if (a === null) return b === null ? 0 : 1;
  if (b === null) return -1;
  const order = a < b ? -1 : a > b ? 1 : 0;
  return descending ? -order : order;
}
export function visiblePositions(
  positions: OperationalPosition[],
  view: PositionsView,
): OperationalPosition[] {
  const words = view.query.toLocaleLowerCase('de-DE').trim().split(/\s+/).filter(Boolean);
  return positions
    .filter((p) => {
      const text = [
        p.product_name,
        p.product_wkn,
        p.product_isin,
        p.underlying_name,
        p.underlying_symbol,
        p.product_symbol,
      ]
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase('de-DE');
      if (!words.every((word) => text.includes(word))) return false;
      if (view.filter === 'alerts') return hasAlert(p);
      if (view.filter === 'data') return hasDataProblem(p);
      const pnl = decimalUnits(p.unrealized_gross_pnl);
      if (view.filter === 'gains') return pnl !== null && pnl > 0n;
      if (view.filter === 'losses') return pnl !== null && pnl < 0n;
      return true;
    })
    .sort((a, b) => {
      let order = 0;
      if (view.sort === 'attention')
        order = compare(rank[positionTone(a)], rank[positionTone(b)], view.descending);
      if (view.sort === 'product')
        order = a.product_name.localeCompare(b.product_name, 'de-DE') * (view.descending ? -1 : 1);
      if (view.sort === 'purchased')
        order = compare(purchaseDate(a), purchaseDate(b), view.descending);
      if (view.sort === 'quantity')
        order = compare(a.open_quantity, b.open_quantity, view.descending);
      if (view.sort === 'quote')
        order = compare(
          a.quote_observed_at && Number.isFinite(Date.parse(a.quote_observed_at))
            ? Date.parse(a.quote_observed_at)
            : null,
          b.quote_observed_at && Number.isFinite(Date.parse(b.quote_observed_at))
            ? Date.parse(b.quote_observed_at)
            : null,
          view.descending,
        );
      if (view.sort === 'value' || view.sort === 'pnl') {
        const field = view.sort === 'value' ? 'market_value' : 'unrealized_gross_pnl';
        const av = decimalUnits(a[field]);
        const bv = decimalUnits(b[field]);
        if (av === null || bv === null) order = compare(av, bv, view.descending);
        else
          order =
            compare(a.valuation_currency, b.valuation_currency, false) ||
            compare(av, bv, view.descending);
      }
      return (
        order ||
        a.product_name.localeCompare(b.product_name, 'de-DE') ||
        a.position_id.localeCompare(b.position_id)
      );
    });
}
export function portfolioTotals(positions: OperationalPosition[]) {
  const groups = new Map<
    string,
    {
      count: number;
      valued: number;
      pnlCount: number;
      indicative: number;
      value: bigint;
      pnl: bigint;
      oldest: string | null;
      unknownTime: number;
    }
  >();
  for (const p of positions) {
    const currency = p.valuation_currency ?? 'Währung ungeklärt';
    const group = groups.get(currency) ?? {
      count: 0,
      valued: 0,
      pnlCount: 0,
      indicative: 0,
      value: 0n,
      pnl: 0n,
      oldest: null,
      unknownTime: 0,
    };
    group.count++;
    const value = decimalUnits(p.market_value);
    const pnl = decimalUnits(p.unrealized_gross_pnl);
    if (value !== null && p.valuation_currency) {
      group.valued++;
      group.value += value;
    }
    if (pnl !== null && p.valuation_currency) {
      group.pnlCount++;
      group.pnl += pnl;
    }
    if (value !== null && p.valuation_currency) {
      if (p.valuation_status !== 'AVAILABLE' || p.analysis_warning) group.indicative++;
      if (!p.quote_observed_at || !Number.isFinite(Date.parse(p.quote_observed_at)))
        group.unknownTime++;
      else if (!group.oldest || Date.parse(p.quote_observed_at) < Date.parse(group.oldest))
        group.oldest = p.quote_observed_at;
    }
    groups.set(currency, group);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}
