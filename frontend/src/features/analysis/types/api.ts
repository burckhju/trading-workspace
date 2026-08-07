export type Uuid = string;

export type AnalysisSummary = {
  id: Uuid;
  underlying_id: Uuid;
  listing_id: Uuid;
  created_at: string;
  created_by: string;
};

export type AnalysisOverview = AnalysisSummary & {
  underlying_name: string;
  ticker: string;
  trading_venue_mic: string;
  trading_venue_name: string;
  currency_code: string;
  latest_version: number | null;
  latest_status: string | null;
  latest_quality_status: string | null;
  latest_analysis_time: string | null;
};

export type AnalysisOverviewPage = {
  items: AnalysisOverview[];
  total: number;
  offset: number;
  limit: number;
};

export type AnalysisRun = {
  version: number;
  status: string;
  quality_status: string;
  model_id: string;
  model_version: string;
  observation_count: number;
  analysis_time: string;
  input_hash: string;
};

export type AnalysisDetail = {
  analysis: AnalysisSummary;
  runs: AnalysisRun[];
};

export type AnalysisParameters = {
  price_field: 'CLOSE' | 'ADJUSTED_CLOSE';
  short_window: number;
  medium_window: number;
  long_window: number;
  momentum_windows: number[];
  volatility_window: number;
  range_window: number;
  minimum_required_observations: number;
  maximum_data_age_days: number;
  annualization_factor: string;
  rounding_scale: number;
};

export type RunAnalysisRequest = {
  start_date: string;
  end_date: string;
  parameters: AnalysisParameters;
};

export type CriterionResult = {
  code: string;
  classification: string;
  value: string | null;
  explanation: string;
};

export type SnapshotRow = {
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
  quality_status: string;
  warnings: string[];
};

export type SnapshotPage = {
  items: SnapshotRow[];
  total: number;
  offset: number;
  limit: number;
};

export type AnalysisRunDetail = {
  analysis: AnalysisSummary;
  run: AnalysisRun;
  parameters: Record<string, unknown>;
  metrics: Record<string, string | null>;
  notes: string[];
  data_sources: string[];
  criteria: CriterionResult[];
  snapshot: SnapshotRow[];
};

export const defaultAnalysisParameters: AnalysisParameters = {
  price_field: 'ADJUSTED_CLOSE',
  short_window: 20,
  medium_window: 50,
  long_window: 200,
  momentum_windows: [20, 60, 120],
  volatility_window: 20,
  range_window: 52,
  minimum_required_observations: 200,
  maximum_data_age_days: 7,
  annualization_factor: '252',
  rounding_scale: 6,
};

export type AnalysisEvent = {
  id: Uuid;
  version: number | null;
  event_type: string;
  from_status: string | null;
  to_status: string;
  source_version: number | null;
  replacement_version: number | null;
  reason: string | null;
  correlation_id: string | null;
  occurred_at: string;
};

export type AnalysisVerification = {
  verified: boolean;
  model_available: boolean;
  input_hash_matches: boolean;
  metrics_match: boolean;
  criteria_match: boolean;
  quality_status_match: boolean;
  notes_match: boolean;
};
