export type OperationalPriority = 'ACTION' | 'REVIEW' | 'BLOCKED';
export type OperationalState = 'ACTIONABLE' | 'BLOCKED';
export type PositionAttentionState = 'ALERT' | 'DATA_HEALTH' | 'OK';

export interface OperationalAction {
  id: string;
  source_feature: string;
  action_type: string;
  priority: OperationalPriority;
  state: OperationalState;
  title: string;
  detail: string;
  resource_type: string;
  resource_id: string;
  next_action: string;
  target: string;
  occurred_at: string | null;
}

export interface OperationalWorkspaceResponse {
  generated_at: string;
  actions: OperationalAction[];
}

export interface OperationalPosition {
  trade_id: string;
  position_id: string;
  product_name: string;
  opened_at: string;
  open_quantity: number;
  average_entry_price: string;
  cost_basis: string;
  realized_gross_pnl: string;
  stop_price: string | null;
  target_price: string | null;
  monitoring_status: string;
  underlying_symbol: string | null;
  valuation_status: string;
  product_symbol: string | null;
  valuation_currency: string | null;
  market_value: string | null;
  unrealized_gross_pnl: string | null;
  open_alert_count: number;
  open_alert_types: string[];
  attention_state: PositionAttentionState;
  target: string;
}

export interface OperationalPositionsResponse {
  generated_at: string;
  positions: OperationalPosition[];
}
