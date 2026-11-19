export type IndicativeOutcome =
  | 'BELOW_ENTRY'
  | 'AT_OR_ABOVE_ENTRY'
  | 'NOT_REACHED'
  | 'UNAVAILABLE'
  | 'CLOSED';

export interface IndicativeAssessmentView {
  id: string;
  rule_version?: string | null;
  evaluated_at: string;
  recorded_at: string;
  outcome: IndicativeOutcome;
  reasons: string[];
  evaluation_mode: 'SOURCE_BID' | 'DELAYED_SOURCE_BID' | 'INDICATIVE_ISSUER' | null;
  bid: string | null;
  gross_entry: string;
  currency: string | null;
  remaining_quantity: number;
  original_bid_at: string | null;
  source_quote_at?: string | null;
  source_time_basis?: 'ORIGINAL_BID_TIME' | 'SHARED_QUOTE_TIME' | 'ORIGINAL_TIME_UNKNOWN' | null;
  source_freshness?: 'WITHIN_900_SECONDS' | 'WITHIN_1800_SECONDS' | 'UNKNOWN' | null;
  product_scale_quality?: 'DOCUMENTED' | 'CURRENT_UNIT_HISTORY_ASSUMED' | 'UNAVAILABLE' | null;
  history_continuity_assumed?: boolean | null;
  received_at: string | null;
  completed_sessions: number | null;
  session_count_at: string;
  session_day_precision?: string | null;
  calendar_quality?: string | null;
  calendar_verification?: string | null;
  review_completed_sessions: number | null;
  review_due: boolean | null;
  owner_basis_id: string;
  source: Record<string, string | null>;
}

export interface IndicativeEpisodeView {
  id: string;
  kind: 'ENTRY_LOSS' | 'REVIEW_DUE' | 'DATA_UNAVAILABLE';
  rule_version?: string | null;
  episode_number: number;
  alert_id: string;
  opening_assessment_id: string;
  closing_assessment_id: string | null;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
}

export interface IndicativeEntryReport {
  trade_id: string;
  position_id: string;
  activation_status: 'NOT_ACTIVATED' | 'SCOPE_ENABLED';
  runner_enabled: boolean;
  notifications_enabled: boolean;
  document_readiness?: {
    outcome: string;
    attempted_at: string;
    next_attempt_at: string;
    problems?: string[];
  } | null;
  latest_assessment: IndicativeAssessmentView | null;
  active_episodes: IndicativeEpisodeView[];
  recent_episodes: IndicativeEpisodeView[];
  assessment_count: number;
  episode_count: number;
  read_at: string;
  definition_version: 'indicative-entry-review-v1' | 'indicative-entry-review-v2';
  scope: 'INDICATIVE_ENTRY_V1' | 'INDICATIVE_ENTRY_V2';
  qualified_b04: false;
  full_baseline_activated: false;
  read_status: 'READ_ONLY';
}
