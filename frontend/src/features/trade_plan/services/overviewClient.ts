import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { TradePlanOriginType, TradePlanStatus } from '../types/api';

export type PurchaseStatus = 'NOT_STARTED' | 'OPEN' | 'CLOSED' | 'CANCELLED' | 'UNKNOWN';

export interface PlanTradeOverview {
  trade_id: string;
  trade_plan_version_id: string | null;
  plan_version: number | null;
  product_id: string;
  product_name: string | null;
  product_isin: string | null;
  product_wkn: string | null;
  status: PurchaseStatus;
  open_quantity: number | null;
  purchased_on: string | null;
  purchased_at: string | null;
  closed_on: string | null;
  closed_at: string | null;
}

export interface PlanExecutionOverview {
  status: PurchaseStatus;
  current_version_status: PurchaseStatus;
  trades: PlanTradeOverview[];
}

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
  // Missing execution data on older backends means unknown, never "not purchased".
  execution?: PlanExecutionOverview | null;
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
