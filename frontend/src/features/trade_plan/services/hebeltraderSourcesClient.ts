import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { HebeltraderPreview } from './hebeltraderClient';

export interface SourceAxis {
  currency: string | null;
  values: Record<string, string | null>;
  reward_risk: string | null;
  band_deviation: string | null;
  issues: string[];
}

export interface HebeltraderSource {
  version_id: string;
  underlying_id: string;
  label: string;
  issue_date: string | null;
  filename: string | null;
  content_hash: string | null;
  stock: SourceAxis;
  warrant: SourceAxis;
  source_issues: string[];
  scope: 'PUBLISHED_SNAPSHOT_NOT_LIVE';
}

export interface SourceList {
  items: HebeltraderSource[];
  has_more: boolean;
  next_offset: number | null;
}

export interface SourceReviewRequest {
  underlying_id: string;
  source_version_id: string;
  quote?: {
    bid: string;
    ask: string;
    currency: string;
    observed_at: string;
    source: string;
  };
  fundamental_ok: boolean;
  target_history: 'UNKNOWN' | 'NOT_REACHED' | 'TARGET1_REACHED' | 'TARGET2_REACHED';
}

export interface SourceReview {
  source: HebeltraderSource;
  current_preview: HebeltraderPreview | null;
  missing_data: string[];
  execution_enabled: false;
}

const baseUrl = `${environment.apiBaseUrl}/api/v1/trade-plans/strategies/hebeltrader`;

export function loadHebeltraderSources(
  underlyingId: string,
  offset = 0,
  signal?: AbortSignal,
): Promise<SourceList> {
  const params = new URLSearchParams({ underlying_id: underlyingId, offset: String(offset) });
  return requestJson<SourceList>(`${baseUrl}/sources?${params.toString()}`, { signal });
}

export function reviewHebeltraderSource(body: SourceReviewRequest): Promise<SourceReview> {
  return requestJson<SourceReview>(`${baseUrl}/source-preview`, { method: 'POST', body });
}
