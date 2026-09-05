import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { TradePlanOriginType, TradePlanStatus } from '../types/api';

export interface TradePlanOverviewItem {
  id: string;
  underlying_id: string;
  origin_type: TradePlanOriginType;
  created_at: string;
  latest_version_id: string;
  latest_version: number;
  status: TradePlanStatus;
}

const overviewUrl = `${environment.apiBaseUrl}/api/v1/trade-plans`;

export const tradePlanOverviewApiClient = {
  list: (signal?: AbortSignal): Promise<TradePlanOverviewItem[]> =>
    requestJson<TradePlanOverviewItem[]>(overviewUrl, { signal }),
};
