export type AlertType = 'STOP_REACHED' | 'TARGET_REACHED';
export type AlertSeverity = 'WARNING' | 'INFO';
export type AlertStatus = 'OPEN' | 'RESOLVED';
export type NotificationChannel = 'TELEGRAM';
export type NotificationStatus = 'PENDING' | 'DELIVERED' | 'FAILED';
export type DeliveryStatus = 'IN_PROGRESS' | 'DELIVERED' | 'FAILED';

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
