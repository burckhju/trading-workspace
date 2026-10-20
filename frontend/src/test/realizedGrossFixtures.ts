import type {
  RealizedGrossFilters,
  RealizedGrossItem,
  RealizedGrossReport,
  RealizedGrossSource,
  ReportCurrencyConfirmation,
} from '../features/performance/types/api';

export const reportFilters: RealizedGrossFilters = {
  from_date: '2026-09-01',
  to_date: '2026-09-30',
  report_currency: 'EUR',
  report_timezone: 'Europe/Berlin',
};

export function currencyConfirmation(executionId: string): ReportCurrencyConfirmation {
  return {
    id: `currency-${executionId}`,
    execution_id: executionId,
    trade_id: 'trade-1',
    workspace_id: 'workspace-1',
    currency_code: 'EUR',
    source: 'USER_CONFIRMED',
    note: 'Synthetische Abrechnung',
    confirmed_at: '2026-10-17T10:00:00Z',
    confirmed_by: 'test-actor',
    supersedes_confirmation_id: null,
    request_id: `request-${executionId}`,
  };
}

export function reportSource(
  executionId: string,
  overrides: Partial<RealizedGrossSource> = {},
): RealizedGrossSource {
  const confirmation =
    overrides.currency_confirmation === undefined
      ? currencyConfirmation(executionId)
      : overrides.currency_confirmation;
  return {
    execution_id: executionId,
    trade_id: 'trade-1',
    product_id: 'product-1',
    side: 'BUY',
    quantity: 100,
    price_per_unit: '2.0000000000',
    time_precision: 'TIMESTAMP',
    executed_at: '2026-08-05T10:00:00Z',
    executed_on: null,
    execution_timezone: null,
    possible_start_at: null,
    possible_end_at: null,
    recorded_at: '2026-10-17T09:00:00Z',
    recorded_by: 'test-actor',
    supersedes_execution_id: null,
    superseded_by_execution_id: null,
    is_effective: true,
    currency_confirmation: confirmation,
    currency_resolution: {
      currency_code: confirmation?.currency_code ?? null,
      source: confirmation ? 'USER_CONFIRMED' : 'UNKNOWN',
      source_execution_ids: confirmation ? [executionId] : [],
      confirmation_ids: confirmation ? [confirmation.id] : [],
    },
    currency_history: [currencyConfirmation(executionId)],
    ...overrides,
  };
}

export function reportItem(
  executionId = 'sell-september-1',
  overrides: Partial<RealizedGrossItem> = {},
): RealizedGrossItem {
  return {
    execution_id: executionId,
    trade_id: 'trade-1',
    product_id: 'product-1',
    product_name: 'Synthetischer Optionsschein',
    origin: 'EXTERNAL',
    time_precision: 'TIMESTAMP',
    executed_at: '2026-09-02T10:00:00Z',
    executed_on: null,
    execution_timezone: null,
    possible_start_at: null,
    possible_end_at: null,
    recorded_at: '2026-10-17T09:00:00Z',
    quantity: 30,
    price_per_unit: '3.0000000000',
    period_status: 'IN_PERIOD',
    status: 'USABLE',
    reasons: [],
    currency_code: 'EUR',
    average_cost_per_unit: '2.0000000000',
    cost_basis_before: '160.0000000000',
    cost_basis_after: '100.0000000000',
    realized_gross_pnl_delta: '30.0000000000',
    realized_gross_pnl_delta_display: '30.00',
    cost_basis_before_close_reset: null,
    open_quantity_before: 80,
    open_quantity_after: 50,
    currency_confirmation_ids: ['currency-buy-august', `currency-${executionId}`],
    cost_basis_execution_ids: ['buy-august', 'sell-august'],
    ...overrides,
  };
}

/** Server-shaped presentation fixtures; expectations are supplied, never calculated in the UI. */
export function realizedGrossReport(
  overrides: Partial<RealizedGrossReport> = {},
): RealizedGrossReport {
  const first = reportItem();
  const second = reportItem('sell-september-2', {
    executed_at: '2026-09-12T10:00:00Z',
    quantity: 40,
    price_per_unit: '2.5000000000',
    average_cost_per_unit: '3.0000000000',
    cost_basis_before: '300.0000000000',
    cost_basis_after: '180.0000000000',
    realized_gross_pnl_delta: '-20.0000000000',
    realized_gross_pnl_delta_display: '-20.00',
    open_quantity_before: 100,
    open_quantity_after: 60,
    currency_confirmation_ids: [
      'currency-buy-august',
      'currency-buy-september',
      'currency-sell-september-2',
    ],
    cost_basis_execution_ids: ['buy-august', 'sell-august', 'sell-september-1', 'buy-september'],
  });
  return {
    definition_version: 'realized-gross-sell-v2',
    filters: { ...reportFilters },
    interval_start_at: '2026-08-31T22:00:00Z',
    interval_end_at: '2026-09-30T22:00:00Z',
    basis: {
      id: 'basis-original',
      read_started_at: '2026-10-17T11:00:00Z',
      read_completed_at: '2026-10-17T11:00:01Z',
      calculated_at: '2026-10-17T11:00:01Z',
      knowledge: 'CURRENT_EFFECTIVE_FACTS',
    },
    currency: {
      code: 'EUR',
      minor_unit: 2,
      reference_version: 'test-currencies-v1',
      rounding: 'ROUND_HALF_EVEN',
    },
    summary: {
      status: 'COMPLETE',
      total: '10.0000000000',
      total_display: '10.00',
      subtotal: null,
      subtotal_display: null,
      rounding_difference: '0.00',
      rounding_difference_display: '0.00',
    },
    counts: {
      examined: 2,
      in_period: 2,
      outside_period: 0,
      period_ambiguous: 0,
      period_unknown: 0,
      candidates: 2,
      usable: 2,
      unresolved: 0,
      excluded: 0,
      cancelled: 0,
    },
    items: [first, second],
    sources: [
      reportSource('buy-august'),
      reportSource('sell-august', {
        side: 'SELL',
        quantity: 20,
        price_per_unit: '2.5000000000',
        executed_at: '2026-08-12T10:00:00Z',
      }),
      reportSource(first.execution_id, {
        side: 'SELL',
        quantity: first.quantity,
        price_per_unit: first.price_per_unit,
        executed_at: first.executed_at,
      }),
      reportSource('buy-september', {
        quantity: 50,
        price_per_unit: '4.0000000000',
        executed_at: '2026-09-06T10:00:00Z',
      }),
      reportSource(second.execution_id, {
        side: 'SELL',
        quantity: second.quantity,
        price_per_unit: second.price_per_unit,
        executed_at: second.executed_at,
      }),
    ],
    excluded_trades: [],
    ...overrides,
  };
}
