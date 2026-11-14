export interface HebeltraderCoverageItem {
  key: string;
  label: string;
  status: 'PRESENT' | 'MISSING' | 'CONFLICT' | 'UNSUITABLE';
  detail: string;
  affected_rules: string[];
  clarification: string | null;
  references: string[];
}

export interface HebeltraderSourceMarks {
  binding: { basis: 'UNDERLYING' | 'WARRANT'; instrument_id: string; currency: string };
  reference_price: string;
  target_1: string;
  target_2: string;
  stop_1: string;
  stop_2: string;
  scale: 'SOURCE_ORIGINAL';
}

export interface HebeltraderSource {
  source_version_id: string;
  observation_id: string;
  version: number;
  supersedes_version_id: string | null;
  currentness: 'CURRENT_SOURCE' | 'SOURCE_SUPERSEDED';
  product_id: string;
  underlying_id: string;
  underlying: HebeltraderSourceMarks;
  product: HebeltraderSourceMarks;
  issue_date: string;
  time_precision: 'DATE_ONLY';
  observed_at: string;
  recorded_at: string;
  imported_at: string;
  source_name: string;
  external_reference: string | null;
  import_row_id: string;
  batch_id: string;
  file_id: string;
  filename: string;
  content_hash: string;
  accepted_at: string;
  accepted_by: string;
}

export interface HebeltraderEvidenceReport {
  definition_version: 'hebeltrader-evidence-v1';
  trade_id: string;
  position_id: string;
  product_id: string;
  underlying_id: string;
  basis_id: string;
  read_started_at: string;
  read_completed_at: string;
  evidence_revision_id: string | null;
  evidence_recorded_at: string | null;
  coverage_status: 'COMPLETE' | 'INCOMPLETE' | 'CONFLICTED';
  items: HebeltraderCoverageItem[];
  original_z1_quantity: number | null;
  assigned_z1_sold_quantity: number | null;
  personal_underlying_entry: string | null;
  underlying_currency: string | null;
  source: HebeltraderSource | null;
  implementation_status: 'F207_4_EVIDENCE_ONLY';
  operation_status: 'NOT_ASSESSED';
  baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE';
  baseline_version: '1.0.0';
}
