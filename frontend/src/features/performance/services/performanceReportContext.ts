import { todayInZone } from '../../trade/services/executionDateCorrection';
import type { RealizedGrossFilters, RealizedGrossReport } from '../types/api';
import { filterKey } from './presentation';

export {
  REALIZED_REPORT_PATH,
  REALIZED_REPORT_PAGE_SIZE,
  REALIZED_REPORT_MAX_PAGES,
  realizedReportViews,
  reportFiltersErrors,
  parseRealizedContext,
  realizedContextQuery,
  realizedListUrl,
  realizedTradeLink,
} from '../../../shared/trade-workspace-navigation/realizedReportNavigation';
export type {
  PerformanceReportKind,
  RealizedReportView,
  RealizedReportContext,
  ReportFilterErrors,
} from '../../../shared/trade-workspace-navigation/realizedReportNavigation';

export const REALIZED_REPORT_DEFINITION = 'realized-gross-sell-v2';

export function initialPerformanceFilters(): RealizedGrossFilters {
  const today = todayInZone('Europe/Berlin');
  return {
    from_date: `${today.slice(0, 8)}01`,
    to_date: today,
    report_currency: 'EUR',
    report_timezone: 'Europe/Berlin',
  };
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
