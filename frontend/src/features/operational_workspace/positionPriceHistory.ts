export type PositionPriceKind = 'BID' | 'ASK' | 'LAST_TRADE' | 'PREVIOUS_CLOSE';

export interface PositionPricePoint {
  id: string;
  observed_at: string;
  price: string;
  captured_at: string | null;
  retrieved_at: string;
  status: string;
  storage: 'SAMPLE' | 'RETAINED';
  quote_time_basis: string | null;
}

export interface PositionPriceSeries {
  id: string;
  provider: string;
  identity_key: string;
  warrant_listing_id: string;
  isin: string;
  currency: string;
  price_kind: PositionPriceKind;
  source_mode: string | null;
  points: PositionPricePoint[];
}

export interface PositionPriceEvent {
  id: string;
  side: 'BUY' | 'SELL';
  occurred_at: string | null;
  executed_on: string | null;
  execution_timezone: string | null;
  price: string;
  currency: string | null;
  currency_source: string;
  quantity: number;
  plottable: boolean;
  reason: string | null;
}

export interface PositionPriceHistoryReport {
  trade_id: string;
  position_id: string;
  warrant_id: string;
  isin: string | null;
  window_start: string | null;
  window_end: string;
  sampling_policy: string;
  sample_limit: number;
  samples_considered: number;
  samples_available: number;
  truncated: boolean;
  collection_started_at: string | null;
  excluded: Record<string, number>;
  series: PositionPriceSeries[];
  events: PositionPriceEvent[];
}

export type PositionPriceHistoryDays = 'all' | '7' | '31' | '90';
