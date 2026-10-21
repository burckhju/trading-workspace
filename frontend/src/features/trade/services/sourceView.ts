import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { JournalVersion } from '../../learning/services/journalClient';
import type { Ft011EvidenceHistoryItem } from '../../learning/types/materialization';
import type { ExitReviewResponse } from '../../post_trade/types/api';
import type {
  TradePlanSummaryResponse,
  TradePlanVersionResponse,
} from '../../trade_plan/types/api';
import type {
  ExecutionCurrencyConfirmation,
  TradeResponse,
  TradeTimelineEntryResponse,
} from '../types/api';

export interface SourceSnapshot<T> {
  data: T;
  read_started_at: string;
  read_completed_at: string;
}
export interface TradeSourceCore {
  trade: TradeResponse;
  product_name: string | null;
  state: string;
  open_quantity: number | null;
  timeline: TradeTimelineEntryResponse[];
  currency_history: ExecutionCurrencyConfirmation[];
}
export interface PlanSource {
  plan: TradePlanSummaryResponse;
  version: TradePlanVersionResponse;
  approval: TradePlanVersionResponse['approval'];
  candidate_evaluation: TradePlanVersionResponse['candidate_evaluation'];
  events: TradePlanVersionResponse['events'];
}
export interface ReviewSource {
  version: Omit<ExitReviewResponse, 'current_version_id'> & { id: string };
}
export interface ReviewSources {
  history: ReviewSource[];
  selected: ReviewSource | null;
  source_currentness: 'CURRENT' | 'STALE' | 'UNKNOWN';
  checked_at: string;
}
export interface JournalSources {
  history: JournalVersion[];
  selected: JournalVersion | null;
  source_currentness: 'CURRENT' | 'STALE' | 'UNKNOWN';
  checked_at: string;
}
export interface EvidenceSource {
  evidence_id: string;
  evidence_type: 'FT011' | 'TRADE_JOURNAL_VERSION';
  created_at: string;
  review_version_id: string | null;
  journal_version_id: string | null;
  source_bound: boolean;
  lesson_links: Ft011EvidenceHistoryItem['lesson_links'];
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const pinKeys = ['review_version_id', 'journal_version_id'] as const;
export type PinKey = (typeof pinKeys)[number];
export function sourceQueryError(query: URLSearchParams): string | null {
  for (const key of ['trade_id', ...pinKeys]) {
    const values = query.getAll(key);
    if (
      (key === 'trade_id' && values.length !== 1) ||
      values.length > 1 ||
      (values.length === 1 && !uuid.test(values[0]))
    ) {
      return 'Ungültiger oder mehrdeutiger Quellenbezug. Kein Wechsel auf eine andere Version.';
    }
  }
  return null;
}
export function sourceLink(query: URLSearchParams, key?: PinKey, value?: string): string {
  const next = new URLSearchParams({ trade_id: query.get('trade_id') ?? '', view: 'sources' });
  for (const pin of pinKeys) {
    const selected = pin === key ? value : query.get(pin);
    if (selected) next.set(pin, selected);
  }
  return `/trade-management?${next.toString()}`;
}
export function sourceUrl(tradeId: string, section = '', pin?: string | null): string {
  return `${environment.apiBaseUrl}/api/v1/trade-position/trades/${encodeURIComponent(tradeId)}/sources${section ? `/${section}` : ''}${pin === null || pin === undefined ? '' : `?version_id=${encodeURIComponent(pin)}`}`;
}
export function readSource<T>(url: string, signal: AbortSignal): Promise<SourceSnapshot<T>> {
  return requestJson<SourceSnapshot<T>>(url, { signal });
}
