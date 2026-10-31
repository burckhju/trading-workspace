import type { ClosedTradeReport, RealizedGrossFilters } from '../types/api';
import { filterKey } from './presentation';

export {
  CLOSED_REPORT_PATH,
  CLOSED_REPORT_PAGE_SIZE,
  closedReportViews,
  type ClosedReportView,
  type ClosedReportContext,
  closedFiltersError,
  parseClosedContext,
  closedContextQuery,
  closedListUrl,
  closedTradeSourceLink,
} from '../../../shared/trade-workspace-navigation/closedReportNavigation';
export {
  closedContextKeys,
  preserveClosedContext,
} from '../../../shared/trade-workspace-navigation/context';

export const CLOSED_REPORT_DEFINITION = 'closed-trade-gross-v1';
export const CLOSED_STATISTICS_DEFINITION = 'closed-trade-statistics-v1';

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

/** Statistics bind to this response without changing the financial-source validator. */
export function verifyClosedStatistics(report: ClosedTradeReport): void {
  if (
    report.statistics?.definition_version !== CLOSED_STATISTICS_DEFINITION ||
    report.statistics.report_basis_id !== report.basis.id ||
    report.statistics.report_status !== report.summary.status
  ) {
    throw new Error(
      'Die Kennzahlen gehören nicht zu dieser Berichtsgrundlage oder Statistikdefinition. Bitte erneut lesen.',
    );
  }
}
