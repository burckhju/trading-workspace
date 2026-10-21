import type {
  ClosedTradeItem,
  ClosedTradeReport,
  ClosedTradeSellContribution,
  RealizedGrossFilters,
} from '../features/performance/types/api';
import { realizedGrossReport, reportSource } from './realizedGrossFixtures';

export const closedTradeFilters: RealizedGrossFilters = {
  from_date: '2026-10-01',
  to_date: '2026-10-31',
  report_currency: 'EUR',
  report_timezone: 'Europe/Berlin',
};

export function closedTradeContribution(
  executionId = 'sell-october',
  overrides: Partial<ClosedTradeSellContribution> = {},
): ClosedTradeSellContribution {
  return {
    execution_id: executionId,
    time_precision: 'TIMESTAMP',
    executed_at: '2026-10-03T10:00:00Z',
    executed_on: null,
    execution_timezone: null,
    possible_start_at: null,
    possible_end_at: null,
    recorded_at: '2026-10-17T09:00:00Z',
    quantity: 60,
    price_per_unit: '3.5000000000',
    is_closing: true,
    period_status: 'IN_PERIOD',
    status: 'USABLE',
    reasons: [],
    currency_code: 'EUR',
    average_cost_per_unit: '3.0000000000',
    cost_basis_before: '180.0000000000',
    cost_basis_after: '0',
    realized_gross_pnl_delta: '30.0000000000',
    realized_gross_pnl_delta_display: '30.00',
    cost_basis_before_close_reset: '0',
    open_quantity_before: 60,
    open_quantity_after: 0,
    currency_confirmation_ids: ['currency-buy-august'],
    cost_basis_execution_ids: [
      'buy-august',
      'sell-august',
      'sell-september-1',
      'buy-september',
      'sell-september-2',
    ],
    ...overrides,
  };
}

export function closedTradeItem(
  tradeId = 'trade-1',
  overrides: Partial<ClosedTradeItem> = {},
): ClosedTradeItem {
  const close = closedTradeContribution();
  const previous = realizedGrossReport().items;
  return {
    trade_id: tradeId,
    product_id: 'product-1',
    product_name: 'Synthetischer Optionsschein',
    origin: 'EXTERNAL',
    group: 'QUALIFIED',
    status: 'USABLE',
    reasons: [],
    period_status: 'IN_PERIOD',
    closing_execution_id: close.execution_id,
    closing_time: {
      time_precision: close.time_precision,
      executed_at: close.executed_at,
      executed_on: close.executed_on,
      execution_timezone: close.execution_timezone,
      possible_start_at: close.possible_start_at,
      possible_end_at: close.possible_end_at,
      recorded_at: close.recorded_at,
    },
    currency_code: 'EUR',
    realized_gross_pnl: '50.0000000000',
    realized_gross_pnl_display: '50.00',
    classification: 'POSITIVE',
    execution_ids: [
      'buy-august',
      'sell-august',
      'sell-september-1',
      'buy-september',
      'sell-september-2',
      'sell-october',
    ],
    effective_execution_ids: [
      'buy-august',
      'sell-august',
      'sell-september-1',
      'buy-september',
      'sell-september-2',
      'sell-october',
    ],
    currency_confirmation_ids: ['currency-buy-august'],
    sell_contributions: [
      closedTradeContribution('sell-august', {
        executed_at: '2026-08-12T10:00:00Z',
        quantity: 20,
        price_per_unit: '2.5000000000',
        is_closing: false,
        period_status: 'OUTSIDE_PERIOD',
        average_cost_per_unit: '2.0000000000',
        cost_basis_before: '200.0000000000',
        cost_basis_after: '160.0000000000',
        realized_gross_pnl_delta: '10.0000000000',
        realized_gross_pnl_delta_display: '10.00',
        cost_basis_before_close_reset: null,
        open_quantity_before: 100,
        open_quantity_after: 80,
        cost_basis_execution_ids: ['buy-august'],
      }),
      ...previous.map((sale) =>
        closedTradeContribution(sale.execution_id, {
          executed_at: sale.executed_at,
          quantity: sale.quantity,
          price_per_unit: sale.price_per_unit,
          is_closing: false,
          period_status: 'OUTSIDE_PERIOD',
          average_cost_per_unit: sale.average_cost_per_unit,
          cost_basis_before: sale.cost_basis_before,
          cost_basis_after: sale.cost_basis_after,
          realized_gross_pnl_delta: sale.realized_gross_pnl_delta,
          realized_gross_pnl_delta_display: sale.realized_gross_pnl_delta_display,
          cost_basis_before_close_reset: null,
          open_quantity_before: sale.open_quantity_before!,
          open_quantity_after: sale.open_quantity_after!,
          cost_basis_execution_ids: sale.cost_basis_execution_ids,
          currency_confirmation_ids: ['currency-buy-august'],
        }),
      ),
      close,
    ],
    ...overrides,
  };
}

/** Exact server-shaped examples: the UI never computes trade results or classification. */
export function closedTradeReport(overrides: Partial<ClosedTradeReport> = {}): ClosedTradeReport {
  const existing = realizedGrossReport();
  const sources = [
    ...existing.sources,
    reportSource('sell-october', {
      side: 'SELL',
      quantity: 60,
      price_per_unit: '3.5000000000',
      executed_at: '2026-10-03T10:00:00Z',
    }),
  ].map((source, index) =>
    index === 0
      ? source
      : {
          ...source,
          currency_confirmation: null,
          currency_history: [],
          currency_resolution: {
            currency_code: 'EUR',
            source: 'PRIOR_BUYS' as const,
            source_execution_ids: index >= 4 ? ['buy-august', 'buy-september'] : ['buy-august'],
            confirmation_ids: ['currency-buy-august'],
          },
        },
  );
  return {
    definition_version: 'closed-trade-gross-v1',
    filters: { ...closedTradeFilters },
    interval_start_at: '2026-09-30T22:00:00Z',
    interval_end_at: '2026-10-31T23:00:00Z',
    basis: { ...existing.basis, id: 'closed-basis-original' },
    currency: existing.currency,
    summary: {
      status: 'COMPLETE',
      total: '50.0000000000',
      total_display: '50.00',
      subtotal: null,
      subtotal_display: null,
      rounding_difference: '0.00',
      rounding_difference_display: '0.00',
    },
    counts: {
      examined: 1,
      cancelled: 0,
      history_unresolved: 0,
      open: 0,
      outside_period: 0,
      other_currency: 0,
      period_unresolved: 0,
      monetary_unresolved: 0,
      qualified: 1,
      in_period: 1,
      unresolved: 0,
      positive: 1,
      negative: 0,
      neutral: 0,
    },
    items: [closedTradeItem()],
    sources,
    ...overrides,
  };
}
