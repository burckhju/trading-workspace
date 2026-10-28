import { render, screen, within } from '@testing-library/react';
import { tradeManagementApiClient } from '../services/client';
import type { ProductPositionValuationResponse } from '../types/api';
import { ProductValuationPanel } from './ProductValuationPanel';

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    position: vi.fn(),
    productValuation: vi.fn(),
  },
}));

const api = vi.mocked(tradeManagementApiClient);
function valuation(
  overrides: Partial<ProductPositionValuationResponse> = {},
): ProductPositionValuationResponse {
  return {
    trade_id: 'trade-1',
    position_id: 'position-1',
    status: 'AVAILABLE',
    reason: 'WARRANT_BID_AVAILABLE',
    warrant_listing_id: 'listing-1',
    symbol: 'TEST12.STU',
    bid: '2.50',
    ask: '2.55',
    currency: 'EUR',
    quote_observed_at: '2026-10-28T10:00:00Z',
    quote_age_seconds: 30,
    max_quote_age_seconds: 3600,
    market_value: '25',
    unrealized_gross_pnl: '5',
    selected_source: 'SYNTHETIC_QUOTE',
    valuation_usable: true,
    execution_usable: false,
    analysis_usable: true,
    analysis_warning: null,
    analysis_market_value: '25',
    analysis_unrealized_gross_pnl: '5',
    freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
    source_attempts: [],
    unrealized_pnl_usable: true,
    unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    analysis_unrealized_pnl_usable: true,
    analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.position.mockResolvedValue({
    id: 'position-1',
    trade_id: 'trade-1',
    product_id: 'product-1',
    open_quantity: 10,
    cost_basis: '20',
    average_entry_price: '2',
    realized_gross_pnl: '0',
    opened_at: '2026-10-27T08:00:00Z',
    last_execution_at: '2026-10-27T08:00:00Z',
    closed_at: null,
    is_closed: false,
  });
});

describe.each([
  ['COST_BASIS_CURRENCY_UNKNOWN', /Kaufwährung.*nicht.*belegt/i],
  ['COST_BASIS_CURRENCY_MIXED', /unterschiedliche Kaufwährungen/i],
  ['COST_BASIS_CURRENCY_MISMATCH', /Kaufwährung.*Kurswährung/i],
] as const)('%s', (reason, message) => {
  it.each(['AVAILABLE', 'STALE', 'LAST_AVAILABLE', 'INDICATIVE'] as const)(
    'preserves %s quote values and provenance while excluding unqualified PnL',
    async (status) => {
      const analysis = status !== 'AVAILABLE';
      api.productValuation.mockResolvedValue(
        valuation({
          status,
          reason: analysis ? 'WARRANT_QUOTE_STALE' : 'WARRANT_BID_AVAILABLE',
          valuation_usable: status !== 'STALE' && status !== 'INDICATIVE',
          market_value: status === 'STALE' || status === 'INDICATIVE' ? null : '25',
          analysis_warning: analysis ? 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY' : null,
          unrealized_pnl_usable: false,
          unrealized_pnl_reason: reason,
          analysis_unrealized_pnl_usable: false,
          analysis_unrealized_pnl_reason: reason,
        }),
      );
      render(<ProductValuationPanel tradeId="trade-1" />);
      expect(await screen.findByText('25 EUR')).toBeInTheDocument();
      expect(screen.queryByText('5 EUR')).not.toBeInTheDocument();
      expect(screen.getByText(message)).toBeInTheDocument();
      const pnl = screen.getByText(
        analysis ? 'Indikativer unrealized gross P&L' : 'Unrealized gross P&L',
      ).parentElement!;
      expect(within(pnl).getByText('—')).toBeInTheDocument();
      expect(screen.getByText(/Bewertungsquelle: SYNTHETIC_QUOTE/)).toBeInTheDocument();
      if (analysis) expect(screen.getByRole('status')).toHaveTextContent('indikative Analyse');
    },
  );
});

it.each(['5', '-5', '0'])(
  'retains the qualified monetary result %s including exact zero',
  async (pnl) => {
    api.productValuation.mockResolvedValue(
      valuation({ unrealized_gross_pnl: pnl, analysis_unrealized_gross_pnl: pnl }),
    );
    render(<ProductValuationPanel tradeId="trade-1" />);
    expect(await screen.findByText(`${pnl} EUR`)).toBeInTheDocument();
  },
);

it('uses the selected analysis qualification independently from the current quote', async () => {
  api.productValuation.mockResolvedValue(
    valuation({
      status: 'STALE',
      valuation_usable: false,
      market_value: null,
      unrealized_gross_pnl: null,
      unrealized_pnl_usable: false,
      unrealized_pnl_reason: 'WARRANT_QUOTE_STALE',
      analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
    }),
  );
  render(<ProductValuationPanel tradeId="trade-1" />);
  expect(await screen.findByText('25 EUR')).toBeInTheDocument();
  expect(screen.getByText('5 EUR')).toBeInTheDocument();
});
