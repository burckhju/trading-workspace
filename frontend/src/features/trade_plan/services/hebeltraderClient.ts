import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { TradePlanContentRequest } from '../types/api';

export interface HebeltraderPreviewRequest {
  as_of: string;
  analysis_date: string;
  source_ref: string;
  quote: {
    bid: string;
    ask: string;
    observed_at: string;
    currency: string;
    source: string;
  };
  gd200: string;
  gd50?: string;
  band_width: string;
  support_source: 'GD200' | 'GD50';
  buffer_fraction: string;
  tick: string;
  fundamental_ok: boolean;
}

export interface HebeltraderPreview {
  policy_id: string;
  execution_enabled: false;
  input_digest: string;
  mode: string;
  levels: { entry: string; stop: string; target1: string; target2: string };
  assessment: {
    eligible: boolean;
    reasons: string[];
    reward_risk: string | null;
    allocation_fraction: string;
    stock_stop_distance: string;
    late_entry: boolean;
  };
  warnings: string[];
  trade_plan_content: TradePlanContentRequest | null;
}

export function previewHebeltrader(body: HebeltraderPreviewRequest): Promise<HebeltraderPreview> {
  return requestJson<HebeltraderPreview>(
    `${environment.apiBaseUrl}/api/v1/trade-plans/strategies/hebeltrader/preview`,
    { method: 'POST', body },
  );
}
