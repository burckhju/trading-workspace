import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { RealizedGrossFilters, RealizedGrossReport } from '../types/api';

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
};
