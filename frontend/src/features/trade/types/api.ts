export type Uuid = string;
export type IsoDateTime = string;

export type ExecutionSide = 'BUY' | 'SELL';
export type TradeOrigin = 'PRODUCT_SELECTION' | 'EXTERNAL';
export type TradeManagementEventType =
  | 'STOP_CHANGED'
  | 'TARGET_CHANGED'
  | 'THESIS_UPDATED'
  | 'MANAGEMENT_NOTE';

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
