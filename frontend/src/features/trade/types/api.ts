export type Uuid = string;
export type IsoDateTime = string;

export type ExecutionSide = 'BUY' | 'SELL';
export type TradeOrigin = 'WORKSPACE_SELECTION' | 'EXTERNAL';
export type TradeManagementEventType =
  | 'STOP_CHANGED'
  | 'TARGET_CHANGED'
  | 'THESIS_UPDATED'
  | 'MANAGEMENT_NOTE';
export type TradeTimelineEntryKind = 'EXECUTION' | 'MANAGEMENT_EVENT';
export type ProductValuationStatus =
  | 'AVAILABLE'
  | 'INDICATIVE'
  | 'LAST_AVAILABLE'
  | 'STALE'
  | 'MISSING'
  | 'UNAVAILABLE'
  | 'ERROR';
export type QuoteSourceAttemptStatus =
  | 'AVAILABLE'
  | 'MISSING'
  | 'INSUFFICIENT'
  | 'UNAVAILABLE'
  | 'ERROR';

export interface TradeResponse {
  id: Uuid;
  product_id: Uuid;
  origin: TradeOrigin;
  trade_plan_id: Uuid | null;
  trade_plan_version_id: Uuid | null;
  product_selection_id: Uuid | null;
  product_evaluation_id: Uuid | null;
  created_at: IsoDateTime;
}

export interface ExecutionResponse {
  id: Uuid;
  trade_id: Uuid;
  product_id: Uuid;
  side: ExecutionSide;
  quantity: number;
  price_per_unit: string;
  gross_amount: string;
  executed_at: IsoDateTime;
  recorded_at: IsoDateTime;
}

export interface PositionResponse {
  id: Uuid;
  trade_id: Uuid;
  product_id: Uuid;
  open_quantity: number;
  cost_basis: string;
  average_entry_price: string;
  realized_gross_pnl: string;
  opened_at: IsoDateTime;
  last_execution_at: IsoDateTime;
  closed_at: IsoDateTime | null;
  is_closed: boolean;
}

export interface QuoteSourceAttemptResponse {
  source: string;
  status: QuoteSourceAttemptStatus;
  reason: string;
  delayed: boolean;
  observed_at: IsoDateTime | null;
  bid_available: boolean;
  ask_available: boolean;
  warrant_listing_id?: Uuid | null;
  reference_price?: string | null;
  reference_price_type?: string | null;
  currency?: string | null;
  refresh_error?: string | null;
}

export interface ProductPositionValuationResponse {
  trade_id: Uuid;
  position_id: Uuid;
  status: ProductValuationStatus;
  reason: string;
  warrant_listing_id: Uuid | null;
  symbol: string | null;
  bid: string | null;
  ask: string | null;
  currency: string | null;
  quote_observed_at: IsoDateTime | null;
  quote_age_seconds: number | null;
  max_quote_age_seconds: number | null;
  market_value: string | null;
  unrealized_gross_pnl: string | null;
  selected_source: string | null;
  valuation_usable: boolean;
  execution_usable: boolean;
  analysis_usable: boolean;
  analysis_warning: string | null;
  analysis_market_value: string | null;
  analysis_unrealized_gross_pnl: string | null;
  freshness_policy: string | null;
  source_attempts: QuoteSourceAttemptResponse[];
  monitoring_usable?: boolean;
  reference_price?: string | null;
  reference_price_type?: 'BID' | 'LAST_TRADE' | 'PREVIOUS_CLOSE' | null;
  quote_provider?: string | null;
  provider_identity?: string | null;
  provider_exchange_code?: string | null;
  isin?: string | null;
  wkn?: string | null;
  source_mode?: string | null;
  trading_status?: string | null;
  quote_retrieved_at?: IsoDateTime | null;
  quote_refresh_error?: string | null;
  quote_assessed_at?: IsoDateTime | null;
  quote_delay_seconds?: number | null;
  quote_venue_mic?: string | null;
  quote_age_limit_exceeded?: boolean | null;
  spread_absolute?: string | null;
  spread_percent?: string | null;
  provenance_listing_id?: Uuid | null;
  quote_listing_id?: Uuid | null;
}

export interface InitialPurchaseRequest {
  product_selection_id: Uuid;
  quantity: number;
  price_per_unit: string;
  executed_at?: IsoDateTime | null;
}

export interface InitialPurchaseResponse {
  trade: TradeResponse;
  execution: ExecutionResponse;
  position: PositionResponse;
}

export interface SaleResponse {
  execution: ExecutionResponse;
  position: PositionResponse;
}

export interface TradeManagementEventResponse {
  id: Uuid;
  trade_id: Uuid;
  event_type: TradeManagementEventType;
  effective_at: IsoDateTime;
  recorded_at: IsoDateTime;
  numeric_value: string | null;
  text_value: string | null;
  supersedes_event_id: Uuid | null;
}

export interface TradeManagementStateResponse {
  trade_id: Uuid;
  stop_price: string | null;
  target_price: string | null;
  thesis: string | null;
  notes: string[];
  last_event_at: IsoDateTime | null;
}

export interface TradeTimelineEntryResponse {
  id: Uuid;
  trade_id: Uuid;
  occurred_at: IsoDateTime;
  recorded_at: IsoDateTime;
  kind: TradeTimelineEntryKind;
  execution_side: ExecutionSide | null;
  management_event_type: TradeManagementEventType | null;
  quantity: number | null;
  price_per_unit: string | null;
  numeric_value: string | null;
  text_value: string | null;
  supersedes_id: Uuid | null;
}

export interface SaleRequest {
  quantity: number;
  price_per_unit: string;
  executed_at?: IsoDateTime | null;
}

export interface PriceManagementRequest {
  price: string;
  effective_at?: IsoDateTime | null;
}

export interface TextManagementRequest {
  text: string;
  effective_at?: IsoDateTime | null;
}
