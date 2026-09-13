import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { TradePlanOriginType, TradePlanStatus } from '../types/api';

export interface SelectedProductOverview {
  run_id: string;
  product_evaluation_id: string;
  warrant_id: string;
  display_name: string | null;
  isin: string | null;
  wkn: string | null;
}

export interface TradePlanOverviewItem {
  id: string;
  underlying_id: string;
  origin_type: TradePlanOriginType;
  created_at: string;
  latest_version_id: string;
  latest_version: number;
  status: TradePlanStatus;
  // Optional for older backends. These labels are current master data, not snapshots.
  underlying_name?: string | null;
  underlying_isin?: string | null;
  underlying_wkn?: string | null;
  selected_product?: SelectedProductOverview | null;
}

const overviewUrl = `${environment.apiBaseUrl}/api/v1/trade-plans`;

export const tradePlanOverviewApiClient = {
  list: (signal?: AbortSignal): Promise<TradePlanOverviewItem[]> =>
    requestJson<TradePlanOverviewItem[]>(overviewUrl, { signal }),
};
