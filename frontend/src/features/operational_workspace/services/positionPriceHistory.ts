import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { PositionPriceHistoryDays, PositionPriceHistoryReport } from '../positionPriceHistory';

export async function readPositionPriceHistory(
  tradeId: string,
  positionId: string,
  days: PositionPriceHistoryDays,
  signal?: AbortSignal,
): Promise<PositionPriceHistoryReport> {
  const suffix = days === 'all' ? '' : `?days=${days}`;
  const report = await requestJson<PositionPriceHistoryReport>(
    `${environment.apiBaseUrl}/api/v1/trade-position/trades/${encodeURIComponent(tradeId)}/price-history${suffix}`,
    { signal },
  );
  // Bind the response to the expanded position; unknown/stale API shapes are an
  // error, never an empty or apparently successful historical price series.
  if (
    !report ||
    report.trade_id !== tradeId ||
    report.position_id !== positionId ||
    !Array.isArray(report.series) ||
    !Array.isArray(report.events) ||
    !report.excluded ||
    !report.series.every((series) => Array.isArray(series.points))
  ) {
    throw new Error('Die Kursdaten lassen sich dieser Position nicht sicher zuordnen.');
  }
  return report;
}
