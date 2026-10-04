export interface RiskParameters {
  hysteresis_fraction: string;
  confirmation_sessions: number;
  volatility_high: string;
  volatility_reset: string;
  maximum_age_days: number;
}
export interface RiskView {
  trade_id: string;
  evaluated_at: string;
  snapshot_id: string | null;
  input_fingerprint: string;
  configuration: {
    revision: number;
    enabled: boolean;
    parameters: RiskParameters;
    policy_version: string;
  };
  product: { direction: string | null; isin: string | null; ratio: string | null } | null;
  listing: { symbol: string; currency: string; listing_id: string } | null;
  metrics: {
    status: string;
    reason: string;
    session: string | null;
    window_start: string | null;
    observations: number;
    adjusted_close: string | null;
    sma20: string | null;
    distance_sma20: string | null;
    sma20_slope: string | null;
    realized_volatility20: string | null;
    previous_volatility20: string | null;
    atr14_relative: string | null;
    atr_reason: string;
    policy_version: string;
  };
  assessment: {
    transition: string;
    interpretation: string;
    reason: string;
    policy_version: string;
    state: {
      trend: string;
      pending_sessions: number;
      trend_warning: boolean;
      volatility_warning: boolean;
    };
  };
  quote_quality: {
    status: string;
    reasons: string[];
    bid: string | null;
    ask: string | null;
    spread_mid_percent: string | null;
    observed_at: string | null;
    received_at: string | null;
    provider: string | null;
    bid_volume: number | null;
    ask_volume: number | null;
  };
  comparison: {
    status: string;
    reasons: string[];
    price_type: string;
    underlying_return: string | null;
    warrant_return: string | null;
    descriptive_divergence: boolean | null;
    times: string[];
    normalized_underlying: string[];
    normalized_warrant: string[];
  };
  input_prices: {
    provider: string;
    provider_symbol: string;
    trading_date: string;
    adjusted_close: string | null;
    retrieved_at: string;
    currency: string;
  }[];
}
