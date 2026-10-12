export interface IvReadiness {
  status: 'NOT_EVALUABLE';
  reasons: string[];
  quote_side: string | null;
  quote_age_seconds: number | null;
  history_status: string;
  event_status: string;
  policy_version: string;
}

export interface IvModelForm {
  scope: string;
  direction: 'CALL' | 'PUT';
  currency: string;
  mode: 'iv' | 'price';
  spot: string;
  strike: string;
  ratio: string;
  remaining_days: string;
  iv_percent: string;
  calibration_price: string;
  rate_percent: string;
  dividend_yield_percent: string;
  quantity: string;
  underlying_change_percent: string;
  iv_change_pp: string;
  elapsed_days: string;
}

export interface IvModelResult {
  status: 'HYPOTHETICAL';
  model_version: string;
  iv_origin: string;
  inputs: { currency: string; iv_decimal: string };
  scenario: {
    quantity: string;
    underlying_change_percent: string;
    iv_change_pp: string;
    elapsed_days: string;
  };
  baseline_price: string;
  scenario_price: string;
  change_per_warrant: string;
  position_change: string;
  vega_per_warrant_per_pp: string | null;
  position_vega_per_pp: string | null;
  local_iv_change: string | null;
  isolated_iv_change: string;
  isolated_spot_change: string;
  isolated_time_change: string;
  warnings: string[];
}
