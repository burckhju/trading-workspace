import type {
  CompletedSessionCount,
  SessionBinding,
  SessionEntry,
  SessionEvidenceCurrent,
  SessionPeriodView,
} from './hebeltraderSessions';
import type { OperationalPosition } from './types';

export const originalBidCheckKeys = [
  'HELD_INSTRUMENT',
  'ORIGINAL_BID_TIME_AND_AGE',
  'EXECUTION_CURRENCY',
  'PRODUCT_SESSION_AT_BID',
  'PRODUCT_SESSION_AT_READ',
  'TWENTY_UNDERLYING_SESSIONS_AT_BID',
  'PRICE_SCALE',
  'VERIFIED_LIVE_MARKET_STATUS',
] as const;

export interface OriginalBidCheck {
  key: (typeof originalBidCheckKeys)[number];
  label: string;
  status: 'SATISFIED' | 'MISSING' | 'UNSUITABLE' | 'NOT_REACHED' | 'NOT_APPLICABLE';
  detail: string;
  reasons: string[];
  affected_rules: Array<'B04' | 'B58'>;
}

export interface OriginalQuoteSideEvidence {
  price: string;
  observed_at: string;
  original_time_text: string;
  source_field: string;
  time_basis: 'SEPARATE_SIDE_TIMESTAMP';
}

export interface OriginalQuoteEvidence {
  version: 'original-quote-evidence-v1';
  source_contract: string;
  source_reference: string;
  generated_at: string;
  isin: string;
  currency: string;
  venue_mic: string;
  bid: OriginalQuoteSideEvidence | null;
  ask: OriginalQuoteSideEvidence | null;
}

export interface SavedQuoteEvidence {
  reason: string;
  provider: string | null;
  retrieved_at: string | null;
  identity_key: string | null;
  refresh_status: string;
  history_observations: number;
  quote: null | {
    warrant_listing_id: string;
    bid: string | null;
    ask: string | null;
    currency: string;
    provider_symbol: string;
    provider_exchange_code: string;
    observed_at: string | null;
    isin: string | null;
    wkn: string | null;
    source_mode: string | null;
    trading_status: string | null;
    reference_price: string | null;
    reference_price_type: 'LAST_TRADE' | 'PREVIOUS_CLOSE' | null;
    assessed_at: string | null;
    feed_delay_seconds: number | null;
    venue_mic: string | null;
    max_quote_age_seconds: number | null;
    refresh_error: string | null;
    retained: boolean;
    quote_time_text: string | null;
    quote_time_basis: string | null;
    bid_volume: number | null;
    ask_volume: number | null;
    original_evidence: OriginalQuoteEvidence | null;
  };
  route: null | {
    workspace_id: string;
    position_id: string;
    warrant_id: string;
    warrant_listing_id: string;
    trading_venue_id: string;
    venue_mic: string;
    currency: string;
    identity_key: string;
    selection_id: string;
    selected_at: string;
  };
  provenance: null | {
    read_at: string;
    raw_payload_fingerprint: string;
    retrieved_at: string | null;
    quality_status: string | null;
    warnings: string[];
    reason_code: string | null;
    stored_at: null;
    stored_at_status: 'NOT_RECORDED_BY_LAST_SUCCESS_STORE';
    storage_kind: 'LAST_SUCCESS';
    mutable: true;
    historical_read: false;
  };
}

export interface OriginalBidAssessment {
  status: 'AVAILABLE' | 'MISSING' | 'UNSUITABLE' | 'NOT_APPLICABLE';
  price: string | null;
  currency: string | null;
  original_bid_at: string | null;
  age_seconds: string | null;
  evaluated_at: string;
  reasons: string[];
  maximum_age_seconds: 900;
  price_axis: 'WARRANT_BID';
}

export interface DocumentedSessionMatch {
  status: 'IN_DOCUMENTED_INTERVAL' | 'OUTSIDE_DOCUMENTED_INTERVAL' | 'NOT_ASSESSABLE';
  event_at: string | null;
  session_date: string | null;
  interval: { opens_at: string; closes_at: string } | null;
  reasons: string[];
}

export type ProductSessionCalendar = Omit<SessionEvidenceCurrent, 'instrument_kind' | 'binding'> & {
  instrument_kind: 'WARRANT';
  binding: (Omit<SessionBinding, 'instrument_kind'> & { instrument_kind: 'WARRANT' }) | null;
};

export interface HebeltraderOriginalBidReport {
  trade_id: string;
  position_id: string;
  product_id: string;
  underlying_id: string;
  position_state: 'OPEN' | 'CLOSED' | 'CANCELLED';
  basis_id: string;
  read_started_at: string;
  read_completed_at: string;
  evaluated_at: string;
  economic_basis: NonNullable<OperationalPosition['position_basis']>;
  entry: SessionEntry | null;
  saved_quote: SavedQuoteEvidence;
  bid: OriginalBidAssessment;
  product_sessions: {
    calendar: ProductSessionCalendar | null;
    period: SessionPeriodView;
    at_bid: DocumentedSessionMatch;
    at_read: DocumentedSessionMatch;
    interval_relation: 'SAME_INTERVAL' | 'DIFFERENT_INTERVALS' | 'NOT_ASSESSABLE';
  };
  underlying_sessions: {
    calendar: SessionEvidenceCurrent;
    period: SessionPeriodView;
    count: CompletedSessionCount | null;
  };
  coverage_status: 'PARTIAL' | 'UNSUITABLE' | 'NOT_APPLICABLE';
  checks: OriginalBidCheck[];
  notices: string[];
  definition_version: 'hebeltrader-original-bid-v1';
  baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE';
  baseline_version: '1.0.0';
  implementation_status: 'F207_3_ORIGINAL_BID_EVIDENCE_ONLY';
  rule_evaluation_status: 'B04_B05_B06_B58_NOT_EVALUATED';
  operation_status: 'NOT_ACTIVATED';
  read_status: 'READ_ONLY';
}
