import type {
  ExecutionCurrencyConfirmation,
  ExecutionCurrencyResolution,
  TradeOrigin,
} from '../../trade/types/api';

export interface RealizedGrossFilters {
  from_date: string;
  to_date: string;
  report_currency: string;
  report_timezone: string;
}

export interface ReportExecutionTime {
  time_precision: 'TIMESTAMP' | 'DATE_ONLY' | 'UNKNOWN';
  executed_at: string | null;
  executed_on: string | null;
  execution_timezone: string | null;
  recorded_at: string;
  possible_start_at: string | null;
  possible_end_at: string | null;
}

export interface ReportCurrencyConfirmation extends ExecutionCurrencyConfirmation {
  workspace_id: string;
  trade_id: string;
  request_id: string | null;
}

export interface RealizedGrossSource extends ReportExecutionTime {
  execution_id: string;
  trade_id: string;
  product_id: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price_per_unit: string | null;
  recorded_by: string;
  supersedes_execution_id: string | null;
  superseded_by_execution_id: string | null;
  is_effective: boolean;
  currency_confirmation: ReportCurrencyConfirmation | null;
  currency_resolution?: ExecutionCurrencyResolution;
  currency_history: ReportCurrencyConfirmation[];
}

export interface RealizedGrossItem extends ReportExecutionTime {
  execution_id: string;
  trade_id: string;
  product_id: string;
  product_name: string | null;
  origin: TradeOrigin;
  quantity: number;
  price_per_unit: string | null;
  period_status: 'IN_PERIOD' | 'OUTSIDE_PERIOD' | 'PERIOD_AMBIGUOUS' | 'PERIOD_UNKNOWN';
  status: 'USABLE' | 'NOT_COMPUTABLE' | 'EXCLUDED';
  reasons: string[];
  currency_code: string | null;
  average_cost_per_unit: string | null;
  cost_basis_before: string | null;
  cost_basis_after: string | null;
  realized_gross_pnl_delta: string | null;
  realized_gross_pnl_delta_display: string | null;
  cost_basis_before_close_reset: string | null;
  open_quantity_before: number | null;
  open_quantity_after: number | null;
  currency_confirmation_ids: string[];
  cost_basis_execution_ids: string[];
}

export interface RealizedGrossReport {
  definition_version: string;
  filters: RealizedGrossFilters;
  interval_start_at: string;
  interval_end_at: string;
  basis: {
    id: string;
    read_started_at: string;
    read_completed_at: string;
    calculated_at: string;
    knowledge: 'CURRENT_EFFECTIVE_FACTS';
  };
  currency: {
    code: string;
    minor_unit: number;
    reference_version: string;
    rounding: 'ROUND_HALF_EVEN';
  };
  summary: {
    status: 'EMPTY' | 'COMPLETE' | 'PARTIAL' | 'NOT_COMPUTABLE';
    total: string | null;
    total_display: string | null;
    subtotal: string | null;
    subtotal_display: string | null;
    rounding_difference: string | null;
    rounding_difference_display: string | null;
  };
  counts: {
    examined: number;
    in_period: number;
    outside_period: number;
    period_ambiguous: number;
    period_unknown: number;
    candidates: number;
    usable: number;
    unresolved: number;
    excluded: number;
    cancelled: number;
  };
  items: RealizedGrossItem[];
  sources: RealizedGrossSource[];
  excluded_trades: {
    trade_id: string;
    product_id: string;
    product_name: string | null;
    origin: TradeOrigin;
    reason: 'TRADE_CANCELLED';
    execution_ids: string[];
  }[];
}

export type ClosedTradeGroup =
  | 'CANCELLED'
  | 'HISTORY_UNRESOLVED'
  | 'OPEN'
  | 'OUTSIDE_PERIOD'
  | 'OTHER_CURRENCY'
  | 'PERIOD_UNRESOLVED'
  | 'MONETARY_UNRESOLVED'
  | 'QUALIFIED';

export interface ClosedTradeSellContribution
  extends Omit<RealizedGrossItem, 'trade_id' | 'product_id' | 'product_name' | 'origin'> {
  is_closing: boolean;
  open_quantity_before: number;
  open_quantity_after: number;
}

export interface ClosedTradeItem {
  trade_id: string;
  product_id: string;
  product_name: string | null;
  origin: TradeOrigin;
  group: ClosedTradeGroup;
  status: 'USABLE' | 'NOT_COMPUTABLE' | 'EXCLUDED';
  reasons: string[];
  period_status: RealizedGrossItem['period_status'] | null;
  closing_execution_id: string | null;
  closing_time: ReportExecutionTime | null;
  currency_code: string | null;
  realized_gross_pnl: string | null;
  realized_gross_pnl_display: string | null;
  classification: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | null;
  execution_ids: string[];
  effective_execution_ids: string[];
  currency_confirmation_ids: string[];
  sell_contributions: ClosedTradeSellContribution[];
}

export interface ClosedTradeStatistic {
  raw: string | null;
  display: string | null;
  reason: string | null;
}

export interface ClosedTradeStatistics {
  definition_version: string;
  report_basis_id: string;
  report_status: RealizedGrossReport['summary']['status'];
  population: number | null;
  win_rate: ClosedTradeStatistic;
  average_gross_pnl: ClosedTradeStatistic;
  median_gross_pnl: ClosedTradeStatistic;
  gross_profit_factor: ClosedTradeStatistic;
}

export interface ClosedTradeReport
  extends Omit<RealizedGrossReport, 'counts' | 'items' | 'excluded_trades'> {
  statistics: ClosedTradeStatistics;
  counts: {
    examined: number;
    cancelled: number;
    history_unresolved: number;
    open: number;
    outside_period: number;
    other_currency: number;
    period_unresolved: number;
    monetary_unresolved: number;
    qualified: number;
    in_period: number;
    unresolved: number;
    positive: number;
    negative: number;
    neutral: number;
  };
  items: ClosedTradeItem[];
}
