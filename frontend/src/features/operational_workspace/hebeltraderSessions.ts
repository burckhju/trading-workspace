export interface SessionEntry {
  execution_id: string;
  executed_at: string | null;
  executed_on: string | null;
  execution_timezone: string | null;
  time_precision: 'EXACT' | 'DATE_ONLY';
}

export interface SessionBinding {
  instrument_kind: 'UNDERLYING';
  instrument_id: string;
  listing_id: string;
  trading_venue_id: string;
  venue_mic: string;
  timezone: string;
  market_segment: string;
  valid_from: string;
  valid_through: string;
}

export interface SessionDay {
  session_date: string;
  status: 'SESSION' | 'CLOSED' | 'UNKNOWN';
  intervals: Array<{ opens_at: string; closes_at: string }>;
  source_reference: string;
}

export interface SessionSourceProvenance {
  manifest_sha256: string;
  document_sha256: string;
  document_filename: string;
  document_media_type: string;
  publisher: string;
  reference: string;
  published_at: string | null;
  published_on: string | null;
  retrieved_at: string | null;
  reviewed_at: string;
  review_reference: string;
  recorded_by: string;
}

export interface SessionEvidenceCurrent {
  workspace_id: string;
  instrument_kind: 'UNDERLYING';
  instrument_id: string;
  known_at: string;
  revision_id: string | null;
  supersedes_revision_id: string | null;
  revision_number: number | null;
  calendar_id: string | null;
  calendar_version: string | null;
  binding: SessionBinding | null;
  coverage_start: string | null;
  coverage_end: string | null;
  evidence_status: 'ACTIVE' | 'WITHDRAWN' | null;
  source: SessionSourceProvenance | null;
  recorded_at: string | null;
  read_at: string;
  status: 'AVAILABLE' | 'MISSING' | 'UNSUITABLE';
  reasons: string[];
  verification: 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION';
  operation_status: 'READ_ONLY';
}

export interface SessionPeriodView {
  start_date: string | null;
  end_date: string | null;
  status: 'COMPLETE' | 'INCOMPLETE' | 'MISSING' | 'UNSUITABLE' | 'LIMIT_EXCEEDED' | 'NOT_REQUESTED';
  fingerprint: string | null;
  missing_dates: string[];
  days: SessionDay[];
}

export interface CompletedSessionCount {
  status: 'AVAILABLE' | 'NOT_ASSESSABLE' | 'NOT_APPLICABLE';
  anchor_date: string | null;
  evaluated_at: string;
  completed_sessions: number | null;
  completed_session_dates: string[];
  twentieth_session_date: string | null;
  twentieth_closes_at: string | null;
  threshold_reached: boolean | null;
  reasons: string[];
  threshold_sessions: 20;
}

export interface HebeltraderSessionsReport {
  trade_id: string;
  position_id: string;
  product_id: string;
  underlying_id: string;
  position_state: 'OPEN' | 'CLOSED' | 'CANCELLED';
  basis_id: string;
  read_started_at: string;
  read_completed_at: string;
  evaluated_at: string;
  entry: SessionEntry | null;
  calendar: SessionEvidenceCurrent;
  period: SessionPeriodView;
  count: CompletedSessionCount;
  issues: Array<{ code: string; detail: string }>;
  notices: string[];
  definition_version: 'hebeltrader-sessions-v1';
  baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE';
  baseline_version: '1.0.0';
  implementation_status: 'F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY';
  rule_evaluation_status: 'B04_B05_B06_B58_NOT_EVALUATED';
  operation_status: 'NOT_ACTIVATED';
  read_status: 'READ_ONLY';
}
