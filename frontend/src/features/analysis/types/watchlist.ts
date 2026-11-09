/** Workspace-owned membership and setup evidence; no client-side quality policy. */
export interface ChartWatchlistMapping {
  id: string;
  version: number;
  status: string;
  provider_symbol: string;
  provider_exchange_code: string;
  validated_at: string | null;
}

export interface ChartWatchlistRefresh {
  status: string;
  reason: string | null;
  checked_at: string | null;
  last_success_at: string | null;
  next_run_at: string | null;
  scope: 'PROCESS_LOCAL';
}

export interface ChartWatchlistItem {
  code: string;
  kind: 'INDEX' | 'ETF';
  name: string;
  group: string;
  isin: string | null;
  mic: string | null;
  currency: string | null;
  ticker: string | null;
  source_url: string;
  target_key: string | null;
  setup_status: 'PENDING' | 'CONFIGURED' | 'BLOCKED';
  setup_reason: string | null;
  last_attempt_at: string | null;
  setup_completed_at: string | null;
  history: {
    first_date: string | null;
    last_date: string | null;
    observation_count: number;
    last_received_at: string | null;
  };
  mapping: ChartWatchlistMapping | null;
  refresh?: ChartWatchlistRefresh | null;
}

/** Existing refresh-runtime fields exposed by the watchlist owner. */
export interface ChartWatchlistScheduler {
  enabled: boolean;
  running: boolean;
  leader: boolean;
  last_error: string | null;
  provider_enabled?: boolean;
  underlying_price_type?: string;
  settings?: { underlyings_interval_seconds?: number };
}

export interface ChartWatchlist {
  catalog_version: string;
  name: string;
  enabled: boolean;
  items: ChartWatchlistItem[];
  scheduler: ChartWatchlistScheduler;
}
