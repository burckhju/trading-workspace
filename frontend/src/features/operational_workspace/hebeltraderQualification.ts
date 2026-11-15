import type { HebeltraderSource } from './hebeltraderEvidence';
import type {
  HebeltraderTargetAssessment,
  HebeltraderTargetsReport,
  TargetComparisonQualification,
} from './hebeltraderTargets';

export interface TargetQualificationIssue {
  code: string;
  detail: string;
}

export interface HistoricalListingBinding {
  workspace_id: string;
  underlying_id: string;
  listing_id: string;
  trading_venue_id: string;
  venue_mic: string;
  timezone: string;
  currency: string;
  listing_version: number;
  venue_version: number;
  venue_reference_version: string;
  listing_recorded_at: string;
  listing_updated_at: string;
  venue_recorded_at: string;
  venue_updated_at: string;
  fingerprint: string;
  provenance: 'CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED';
}

export interface HistoricalDailyEvidence {
  source_row_id: string;
  workspace_id: string;
  listing_id: string;
  market_data_instrument_id: string | null;
  fingerprint: string;
  trading_date: string;
  open: string;
  high: string;
  low: string;
  close: string;
  adjusted_close: string | null;
  volume: string | null;
  currency: string;
  provider: string;
  provider_symbol: string;
  price_type: string;
  quality_status: string;
  warnings: string[];
  interval_start: string | null;
  interval_end: string | null;
  retrieved_at: string;
  source_updated_at: string | null;
  recorded_at: string;
  last_updated_at: string;
  issues: string[];
  scale_status: 'REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION' | 'ADJUSTMENT_INDICATION_PRESENT';
  time_precision: 'DATE_ONLY';
  interval_basis: 'LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION';
  price_basis: 'UNDERLYING';
}

export interface HebeltraderPriceHistory {
  workspace_id: string;
  underlying_id: string;
  binding: HistoricalListingBinding | null;
  rows: HistoricalDailyEvidence[];
  status: 'AVAILABLE' | 'MISSING' | 'BLOCKED' | 'LIMIT_EXCEEDED';
  reasons: string[];
  fingerprint: string;
  start_date: string;
  end_date: string;
  known_at: string;
  read_at: string;
  stored_range_complete: boolean;
  intervals_complete: boolean;
  rows_observed: number;
  row_limit: number;
  calendar_coverage: 'NOT_ASSESSED';
  qualification_required: 'HISTORICAL_BINDING_AND_COMPARISON_SCALE';
}

export interface TargetQualificationPreview {
  definition_version: 'hebeltrader-qualification-preview-v1';
  operation_status: 'READ_ONLY';
  report: HebeltraderTargetsReport;
  entry: {
    product_id: string;
    underlying_id: string;
    option_direction: 'CALL' | 'PUT' | null;
    opened_at: string | null;
    opened_on: string | null;
    opening_timezone: string | null;
    evidence_revision_id: string | null;
  };
  source: HebeltraderSource | null;
  attempted_source_version_id: string | null;
  source_issues: TargetQualificationIssue[];
  source_scale: {
    review_status: 'UNVERIFIED' | 'UNCHANGED_VERIFIED' | 'ADJUSTMENT_REQUIRED';
    source_scale_reference: string | null;
    review_reference: string | null;
    scope: 'SOURCE_AND_PURCHASE_EVIDENCE_ONLY';
    market_observations_verified: false;
  };
  history: HebeltraderPriceHistory;
  readiness: {
    status: 'REVIEWABLE' | 'BLOCKED' | 'NOT_APPLICABLE';
    issues: TargetQualificationIssue[];
    usable_row_count: number;
    rows: {
      source_row_id: string;
      fingerprint: string;
      status: 'SUITABLE_AFTER_CONFIRMATION' | 'UNSUITABLE';
      issues: TargetQualificationIssue[];
    }[];
  };
  qualification: {
    status: 'MISSING' | 'REUSABLE' | 'STALE';
    value: TargetComparisonQualification | null;
    contained_in_assessment_id: string | null;
    contained_in_recorded_at: string | null;
    origin: 'USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION';
  };
  qualification_binding: Omit<TargetComparisonQualification, 'evidence_reference'> | null;
  notices: string[];
}

export interface TargetRequestStatus {
  definition_version: 'hebeltrader-request-status-v1';
  operation_status: 'READ_ONLY';
  trade_id: string;
  position_id: string;
  request_id: string;
  status: 'RECORDED' | 'UNKNOWN';
  read_started_at: string;
  read_completed_at: string;
  recorded_at: string | null;
  assessment: HebeltraderTargetAssessment | null;
  qualification: TargetComparisonQualification | null;
}
