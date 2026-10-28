import { todayInZone } from '../../trade/services/executionDateCorrection';
import type { RealizedGrossFilters, RealizedGrossReport } from '../types/api';
import { closedContextKeys, closedFiltersError } from './closedReportContext';
import { filterKey } from './presentation';

export type PerformanceReportKind = 'realized-gross' | 'closed-trades';
export const REALIZED_REPORT_PATH = '/performance/realized-gross';
export const REALIZED_REPORT_DEFINITION = 'realized-gross-sell-v2';
export const REALIZED_REPORT_PAGE_SIZE = 20;
// reader.py limits the snapshot to 20,000 executions, not 2,000 trades.
// SELL pages therefore must not inherit the closed report's 100-page limit.
export const REALIZED_REPORT_MAX_PAGES = 20_000 / REALIZED_REPORT_PAGE_SIZE;
export const realizedReportViews = [
  'candidates',
  'usable',
  'unresolved',
  'excluded',
  'all',
] as const;
export type RealizedReportView = (typeof realizedReportViews)[number];
export interface RealizedReportContext {
  filters: RealizedGrossFilters;
  view: RealizedReportView;
  page: number;
  basis: string | null;
}

const fingerprint = /^[0-9a-f]{64}$/;
const invalidContext =
  'Ungültiger oder mehrdeutiger Verkaufsberichtskontext. Keine Ersatzperiode und kein fremdes Rücksprungziel.';

export function initialPerformanceFilters(): RealizedGrossFilters {
  const today = todayInZone('Europe/Berlin');
  return {
    from_date: `${today.slice(0, 8)}01`,
    to_date: today,
    report_currency: 'EUR',
    report_timezone: 'Europe/Berlin',
  };
}

export type ReportFilterErrors = Partial<Record<keyof RealizedGrossFilters, string>>;

function isCalendarDate(value: string): boolean {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) || value.startsWith('0000')) return false;
  // Calendar validation only. Period boundaries remain exclusively backend-owned.
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function reportFiltersErrors(filters: RealizedGrossFilters): ReportFilterErrors {
  const errors: ReportFilterErrors = {};
  if (!isCalendarDate(filters.from_date))
    errors.from_date = 'Bitte ein gültiges Von-Datum angeben.';
  if (!isCalendarDate(filters.to_date)) errors.to_date = 'Bitte ein gültiges Bis-Datum angeben.';
  if (!errors.from_date && !errors.to_date && filters.from_date > filters.to_date) {
    errors.from_date = 'Von darf nicht nach Bis liegen.';
    errors.to_date = 'Bis darf nicht vor Von liegen.';
  }
  if (!/^[A-Z]{3}$/.test(filters.report_currency)) {
    errors.report_currency = 'Bitte eine gültige Berichtswährung auswählen.';
  }
  const zone = filters.report_timezone;
  // Modern Intl also accepts fixed offsets; the report API requires an IANA
  // identifier. Named zones such as Etc/GMT+1 remain valid.
  if (!zone || zone.length > 64 || /^[+-]/.test(zone) || /[\s\\?#]/.test(zone)) {
    errors.report_timezone = 'Bitte eine gültige Berichtszeitzone (IANA) auswählen.';
  } else {
    try {
      new Intl.DateTimeFormat('de-DE', { timeZone: zone });
    } catch {
      errors.report_timezone = 'Bitte eine gültige Berichtszeitzone (IANA) auswählen.';
    }
  }
  return errors;
}

export function parseRealizedContext(query: URLSearchParams): {
  context: RealizedReportContext | null;
  error: string | null;
} {
  if (!closedContextKeys.some((key) => query.has(key))) return { context: null, error: null };
  const invalid = { context: null, error: invalidContext };
  if (closedContextKeys.some((key) => query.getAll(key).length > 1)) return invalid;
  if (query.get('report_context') !== 'realized-gross') return invalid;
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
    Object.keys(reportFiltersErrors(filters)).length > 0 ||
    !realizedReportViews.includes(view as RealizedReportView) ||
    !/^[1-9][0-9]{0,3}$/.test(rawPage) ||
    Number(rawPage) > REALIZED_REPORT_MAX_PAGES ||
    (basis !== null && !fingerprint.test(basis))
  )
    return invalid;
  return {
    context: { filters, view: view as RealizedReportView, page: Number(rawPage) - 1, basis },
    error: null,
  };
}

export function realizedContextQuery(context: RealizedReportContext): URLSearchParams {
  const query = new URLSearchParams({
    report_context: 'realized-gross',
    ...context.filters,
    report_view: context.view,
    report_page: String(context.page + 1),
  });
  if (context.basis !== null) query.set('report_basis', context.basis);
  return query;
}

export function verifyRealizedReport(
  report: RealizedGrossReport,
  filters: RealizedGrossFilters,
): void {
  if (
    filterKey(report.filters) !== filterKey(filters) ||
    report.currency.code !== filters.report_currency ||
    report.definition_version !== REALIZED_REPORT_DEFINITION
  ) {
    throw new Error(
      'Die Antwort gehört nicht zum gewählten Verkaufsbericht, zur Periode, Währung oder Zeitzone. Bitte erneut lesen.',
    );
  }
}
