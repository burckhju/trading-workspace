export type AlertType = 'STOP_REACHED' | 'TARGET_REACHED';
export type AlertSeverity = 'WARNING' | 'INFO';
export type AlertStatus = 'OPEN' | 'RESOLVED';
export type NotificationChannel = 'TELEGRAM';
export type NotificationStatus = 'PENDING' | 'DELIVERED' | 'FAILED';
export type DeliveryStatus = 'IN_PROGRESS' | 'DELIVERED' | 'FAILED';
export type MonitoringHealthStatus = 'OK' | 'MISSING' | 'STALE' | 'ERROR';
export type PositionValuationStatus = 'OK' | 'MISSING' | 'UNAVAILABLE' | 'ERROR';

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
}

export interface PositionValuationResponse {
  trade_id: string;
  position_id: string;
  status: PositionValuationStatus;
  reason: string;
  warrant_listing_id: string | null;
  bid: string | null;
  ask: string | null;
  currency: string | null;
  observed_at: string | null;
  mark_price: string | null;
  mark_price_type: string | null;
  market_value: string | null;
  unrealized_gross_pnl: string | null;
}
