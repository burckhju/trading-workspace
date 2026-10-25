import type { ClosedTradeReport, RealizedGrossFilters } from '../types/api';
import { filterKey } from './presentation';

export const CLOSED_REPORT_PATH = '/performance/closed-trades';
export const CLOSED_REPORT_DEFINITION = 'closed-trade-gross-v1';
export const CLOSED_REPORT_PAGE_SIZE = 20;
export const closedReportViews = [
  'candidates',
  'qualified',
  'unresolved',
  'excluded',
  'all',
] as const;
export type ClosedReportView = (typeof closedReportViews)[number];
export interface ClosedReportContext {
  filters: RealizedGrossFilters;
  view: ClosedReportView;
  page: number;
  basis: string | null;
}

// Deliberately no URL/returnTo, amount, classification, workspace or source ID.
// This is navigation context, never a historical report or trusted money input.
export const closedContextKeys = [
  'report_context',
  'from_date',
  'to_date',
  'report_currency',
  'report_timezone',
  'report_view',
  'report_page',
  'report_basis',
] as const;
const fingerprint = /^[0-9a-f]{64}$/;
const invalidContext =
  'Ungültiger oder mehrdeutiger Abschlussberichtskontext. Keine Ersatzperiode und kein fremdes Rücksprungziel.';

function isDate(value: string): boolean {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) || value.startsWith('0000')) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function closedFiltersError(filters: RealizedGrossFilters): string | null {
  if (!isDate(filters.from_date) || !isDate(filters.to_date) || filters.from_date > filters.to_date)
    return 'Bitte einen gültigen Zeitraum angeben: Von darf nicht nach Bis liegen.';
  if (!/^[A-Z]{3}$/.test(filters.report_currency) || !filters.report_timezone)
    return 'Bitte Berichtswährung und Berichtszeitzone ausdrücklich auswählen.';
  if (filters.report_timezone.length > 64 || /[\s\\?#]/.test(filters.report_timezone))
    return 'Bitte eine gültige Berichtszeitzone (IANA) auswählen.';
  try {
    new Intl.DateTimeFormat('de-DE', { timeZone: filters.report_timezone });
  } catch {
    return 'Bitte eine gültige Berichtszeitzone (IANA) auswählen.';
  }
  return null;
}

export function parseClosedContext(query: URLSearchParams): {
  context: ClosedReportContext | null;
  error: string | null;
} {
  if (!closedContextKeys.some((key) => query.has(key))) return { context: null, error: null };
  const invalid = { context: null, error: invalidContext };
  if (closedContextKeys.some((key) => query.getAll(key).length > 1)) return invalid;
  if (query.get('report_context') !== 'closed-trades') return invalid;
  const filters = {
    from_date: query.get('from_date') ?? '',
    to_date: query.get('to_date') ?? '',
    report_currency: query.get('report_currency') ?? '',
    report_timezone: query.get('report_timezone') ?? '',
  };
  const view = query.get('report_view') ?? 'candidates';
  const rawPage = query.get('report_page') ?? '1';
  const basis = query.get('report_basis');
  if (
    closedFiltersError(filters) ||
    !closedReportViews.includes(view as ClosedReportView) ||
    !/^(?:[1-9][0-9]?|100)$/.test(rawPage) ||
    (basis !== null && !fingerprint.test(basis))
  )
    return invalid;
  return {
    context: { filters, view: view as ClosedReportView, page: Number(rawPage) - 1, basis },
    error: null,
  };
}

export function closedContextQuery(context: ClosedReportContext): URLSearchParams {
  const query = new URLSearchParams({
    report_context: 'closed-trades',
    ...context.filters,
    report_view: context.view,
    report_page: String(context.page + 1),
  });
  if (context.basis !== null) query.set('report_basis', context.basis);
  return query;
}

export function closedListUrl(context: ClosedReportContext): string {
  return `${CLOSED_REPORT_PATH}?${closedContextQuery(context)}`;
}

export function closedTradeSourceLink(tradeId: string, context: ClosedReportContext): string {
  const query = closedContextQuery(context);
  query.set('trade_id', tradeId);
  query.set('view', 'sources');
  return `/trade-management?${query}`;
}

export function preserveClosedContext(from: URLSearchParams, to: URLSearchParams): void {
  // Preserve even an invalid context as invalid when switching historical pins;
  // do not silently turn it into a different, unqualified navigation context.
  for (const key of closedContextKeys) for (const value of from.getAll(key)) to.append(key, value);
}

export function verifyClosedReport(report: ClosedTradeReport, filters: RealizedGrossFilters): void {
  if (
    filterKey(report.filters) !== filterKey(filters) ||
    report.currency.code !== filters.report_currency ||
    report.definition_version !== CLOSED_REPORT_DEFINITION
  ) {
    throw new Error(
      'Die Antwort gehört nicht zur gewählten Abschlussauswertung, Periode, Währung oder Zeitzone. Bitte erneut lesen.',
    );
  }
}
