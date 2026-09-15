export type AlertType = 'STOP_REACHED' | 'TARGET_REACHED';
export type AlertSeverity = 'WARNING' | 'INFO';
export type AlertStatus = 'OPEN' | 'RESOLVED' | 'INVALIDATED';
export type NotificationChannel = 'TELEGRAM';
export type NotificationStatus = 'PENDING' | 'DELIVERED' | 'FAILED';
export type DeliveryStatus = 'IN_PROGRESS' | 'DELIVERED' | 'FAILED';
export type MonitoringHealthStatus = 'OK' | 'MISSING' | 'STALE' | 'ERROR';

export interface DeliveryAttemptResponse {
  status: DeliveryStatus;
  attempted_at: string;
  completed_at: string | null;
  retryable: boolean;
  error_code: string | null;
  error_message: string | null;
}

export interface NotificationResponse {
  id: string;
  channel: NotificationChannel;
  destination_key: string;
  status: NotificationStatus;
  created_at: string;
  last_delivery: DeliveryAttemptResponse | null;
}

export interface AlertResponse {
  price_context?: Record<string, string | null> | null;
  invalidated_at?: string | null;
  invalidation_reason?: string | null;
  id: string;
  position_id: string;
  trade_id: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  rule_key: string;
  reason: string;
  observed_value: string;
  threshold_value: string;
  market_data_observed_at: string;
  detected_at: string;
  status: AlertStatus;
  resolved_at: string | null;
  notifications: NotificationResponse[];
}

export interface PositionMonitoringHealthResponse {
  trade_id: string;
  position_id: string;
  status: MonitoringHealthStatus;
  reason: string;
  symbol: string | null;
  trading_date: string | null;
  market_data_observed_at: string | null;
  age_days: number | null;
  basis?: {
    underlying_id: string;
    name: string;
    isin: string | null;
    listing_id: string;
    venue_mic: string;
    currency: string;
  } | null;
  daily_price?: {
    listing_id: string;
    trading_date: string;
    close: string;
    low: string;
    high: string;
    currency: string;
    provider: string;
    provider_symbol: string;
    source_updated_at: string | null;
    retrieved_at: string;
  } | null;
}

export interface MonitoringRuntimeStatusResponse {
  enabled: boolean;
  running: boolean;
  cycle_running: boolean;
  interval_seconds: number;
  scope: 'PROCESS_LOCAL_ALL_WORKSPACES';
  price_basis: 'EXPLICIT_INSTRUMENT_AND_CURRENCY' | 'COMPLETED_UNDERLYING_DAILY_LOW_HIGH';
  last_rule_checks?: Record<string, string | null>[];
  last_cycle_started_at: string | null;
  last_cycle_completed_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  last_result: Record<string, number> | null;
}
