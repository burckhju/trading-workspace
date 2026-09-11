export type OperationalPriority = 'ACTION' | 'REVIEW' | 'BLOCKED';
export type OperationalState = 'ACTIONABLE' | 'BLOCKED';
export type PositionAttentionState = 'ALERT' | 'DATA_HEALTH' | 'OK';
export type PositionSignalLevel = 'NORMAL' | 'ATTENTION' | 'CRITICAL';
export type PositionSignalQuality = 'AVAILABLE' | 'INSUFFICIENT' | 'MISSING' | 'STALE' | 'ERROR';

export interface PositionAlertProjection {
  trade_id: string;
  position_id: string;
  alert_level: PositionSignalLevel | null;
  attention_required: boolean;
  quality_status: PositionSignalQuality;
  reason: string;
  candidate_stop: string | null;
  latest_price: string | null;
  phase: 'BUILDING' | 'CONFIRMED' | 'TREND' | 'PEAK_PROTECTION' | null;
  policy_version: string;
  dynamic_stop_policy_version: string;
  analysis_run_id: string | null;
}

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
  position_signal?: PositionAlertProjection | null;
}

export interface OperationalPositionsResponse {
  generated_at: string;
  positions: OperationalPosition[];
}
