export interface ChartIdentity {
  key: string;
  name: string;
  instrument_id: string | null;
  instrument_type: string;
  reference_id: string | null;
  reference_code: string | null;
  underlying_id: string | null;
  listing_id: string | null;
  isin: string | null;
  ticker: string | null;
  mic: string | null;
  currency: string | null;
  return_basis: string;
  basis_source: string | null;
  active: boolean;
  mapping_status: string;
  provider_identity: string | null;
  mapping_id: string | null;
  mapping_version: number | null;
  setup_url: string;
}

export interface ChartPoint {
  trading_date: string;
  value: string | null;
  normalized: string | null;
  change_percent: string | null;
  provider: string;
  provider_symbol: string;
  received_at: string;
  source_updated_at: string | null;
  observed_at: null;
  quality: string;
  warnings: string[];
  gap_before: boolean;
}

export interface ChartSeries {
  identity: ChartIdentity;
  currency: string | null;
  return_basis: string;
  points: ChartPoint[];
  first_date: string | null;
  last_date: string | null;
  observation_count: number;
  issues: string[];
  missing_comparison_dates: string[];
}

export interface ChartComparison {
  series: ChartSeries[];
  requested_start: string | null;
  requested_end: string;
  price_field: 'CLOSE' | 'ADJUSTED_CLOSE';
  common_start: string | null;
  common_end: string | null;
  comparison_status: string;
  issues: string[];
  model_version: string;
  resolution: string;
  fx_adjusted: boolean;
  calendar_verified: boolean;
  max_points_per_series: number;
}

export interface SeriesCoverage {
  count: number;
  first_date: string | null;
  last_date: string | null;
}

export interface SectorChartContext {
  id: string;
  code: string;
  name: string;
  classification_system: string;
  classification_version: string;
  active: boolean;
  reference: ChartIdentity | null;
  proxy: ChartIdentity | null;
  status: string;
  setup_url: string;
}

export interface ChartCatalog {
  references: { identity: ChartIdentity; history: SeriesCoverage }[];
  proxies: { identity: ChartIdentity; history: SeriesCoverage }[];
  sectors: {
    context: SectorChartContext;
    reference_history: SeriesCoverage;
    proxy_history: SeriesCoverage;
  }[];
  as_of: string;
  taxonomy_status: string;
}

export interface UnderlyingChartContext {
  underlying_id: string;
  subject: ChartIdentity | null;
  market: ChartIdentity | null;
  sector: ChartIdentity | null;
  issues: string[];
  assignment_date: string;
}
