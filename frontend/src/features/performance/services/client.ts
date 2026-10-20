import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { ClosedTradeReport, RealizedGrossFilters, RealizedGrossReport } from '../types/api';

export const performanceApiClient = {
  realizedGross: (
    filters: RealizedGrossFilters,
    signal?: AbortSignal,
  ): Promise<RealizedGrossReport> => {
    const query = new URLSearchParams({ ...filters });
    return requestJson<RealizedGrossReport>(
      `${environment.apiBaseUrl}/api/v1/performance/realized-gross?${query.toString()}`,
      { signal },
    );
  },
  closedTrades: (
    filters: RealizedGrossFilters,
    signal?: AbortSignal,
  ): Promise<ClosedTradeReport> => {
    const query = new URLSearchParams({ ...filters });
    return requestJson<ClosedTradeReport>(
      `${environment.apiBaseUrl}/api/v1/performance/closed-trades?${query.toString()}`,
      { signal },
    );
  },
};
