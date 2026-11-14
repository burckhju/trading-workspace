export interface HebeltraderTargetEvidence {
  trading_date: string;
  interval_start: string;
  interval_end: string;
  high: string;
  source_row_id: string;
  source_fingerprint: string;
  provider: string;
  provider_symbol: string;
  listing_id: string;
  time_precision: 'DATE_ONLY';
  detected_at: string;
}

export interface HebeltraderTarget {
  target: 'Z1' | 'Z2';
  status: 'PROVEN' | 'NOT_PROVEN' | 'NOT_ASSESSABLE' | 'REVIEW_REQUIRED';
  threshold: string | null;
  currency: string | null;
  event_id: string | null;
  proof_source_version_id: string | null;
  proof_scale_reference: string | null;
  detail: string;
  reasons: string[];
  evidence: HebeltraderTargetEvidence | null;
}

type BasisStatus = 'AVAILABLE' | 'NOT_ASSESSABLE' | 'NOT_APPLICABLE';

export interface HebeltraderTargetAssessment {
  id: string;
  recorded_at: string;
  basis_id: string;
  source_version_id: string | null;
  previous_assessment_id: string | null;
  targets: HebeltraderTarget[];
  orientation: {
    status: BasisStatus;
    original_quantity: number | null;
    assigned_sold_quantity: number | null;
    proportion: '0.5';
    detail: string;
  };
  protection_basis: {
    status: BasisStatus;
    personal_underlying_entry: string | null;
    currency: string | null;
    detail: string;
  };
}

export interface HebeltraderTargetsReport {
  definition_version: 'hebeltrader-targets-v1';
  baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE';
  baseline_version: '1.0.0';
  implementation_status: 'F207_2_TARGET_HISTORY_ONLY';
  operation_status: 'NOT_ACTIVATED';
  trade_id: string;
  position_id: string;
  current_basis_id: string;
  currentness: 'CURRENT' | 'CHANGED_INPUTS' | 'NO_ASSESSMENT';
  position_state: 'OPEN' | 'CLOSED' | 'CANCELLED';
  read_started_at: string;
  read_completed_at: string;
  assessment_count: number;
  inputs: {
    source_version_id: string | null;
    source_scale_reference: string | null;
    price_history_fingerprint: string;
    listing_binding_fingerprint: string | null;
    qualification_reusable: boolean;
    available_price_rows: number;
    issues: string[];
  };
  latest_assessment: HebeltraderTargetAssessment | null;
}

export interface HebeltraderTargetAssessmentRequest {
  position_id: string;
  request_id: string;
  expected_basis_id: string;
  expected_assessment_id: string | null;
  confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE';
}
