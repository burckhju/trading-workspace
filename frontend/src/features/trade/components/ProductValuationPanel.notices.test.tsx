import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import type { ProductPositionValuationResponse } from '../types/api';
import { ProductValuationPanel } from './ProductValuationPanel';

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: { position: vi.fn(), productValuation: vi.fn() },
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
    market_value: '25.0000000000',
    unrealized_gross_pnl: '5.0000000000',
    unrealized_pnl_usable: true,
    unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    selected_source: 'SYNTHETIC_QUOTE',
    valuation_usable: true,
    execution_usable: false,
    analysis_usable: true,
    analysis_warning: null,
    analysis_market_value: '25.0000000000',
    analysis_unrealized_gross_pnl: '5.0000000000',
    analysis_unrealized_pnl_usable: true,
    analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
    source_attempts: [],
    ...overrides,
  };
}

function show(value: ProductPositionValuationResponse) {
  api.productValuation.mockResolvedValue(value);
  return render(<ProductValuationPanel tradeId="trade-1" />);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.position.mockResolvedValue({
    id: 'position-1',
    trade_id: 'trade-1',
    product_id: 'product-1',
    open_quantity: 10,
    cost_basis: '20.00',
    average_entry_price: '2.00',
    realized_gross_pnl: '0',
    opened_at: '2026-10-27T08:00:00Z',
    last_execution_at: '2026-10-27T08:00:00Z',
    closed_at: null,
    is_closed: false,
  });
});

describe('cause-faithful valuation notices (TC-49)', () => {
  it('keeps an unknown warning neutral, exposes its original text safely and preserves real zero', async () => {
    const user = userEvent.setup();
    const warning = 'FUTURE_QUOTE_WARNING <img src="not-a-real-source">';
    const { container } = show(
      valuation({
        analysis_warning: warning,
        unrealized_gross_pnl: '0.0000000000',
        analysis_unrealized_gross_pnl: '0.0000000000',
      }),
    );

    expect(
      await screen.findByText('Hinweis zur Kursbasis – Ursache nicht näher erläutert'),
    ).toBeVisible();
    expect(screen.queryByText(/Kursdaten veraltet|Produktkurs veraltet/)).not.toBeInTheDocument();
    expect(screen.getByText('25 EUR')).toBeVisible();
    expect(screen.getByText('0 EUR')).toBeVisible();
    expect(screen.getByText(/Bewertungsquelle: SYNTHETIC_QUOTE/)).toBeVisible();

    const notice = screen.getByRole('status');
    const summary = within(notice).getByText('Originalhinweis zur Kursbasis');
    const details = summary.closest('details')!;
    const originalWarning = within(details).getByText(warning, { exact: false });
    expect(details).not.toHaveAttribute('open');
    expect(originalWarning).not.toBeVisible();
    expect(details).toHaveTextContent('WARRANT_BID_AVAILABLE');
    expect(container.querySelector('img')).toBeNull();

    await user.click(summary);
    expect(details).toHaveAttribute('open');
    expect(originalWarning).toBeVisible();
    expect(api.position).toHaveBeenCalledTimes(1);
    expect(api.productValuation).toHaveBeenCalledTimes(1);
  });

  it.each(['AVAILABLE', 'INDICATIVE'] as const)(
    'does not turn an OUTDATED warning into a stale classification for %s',
    async (status) => {
      show(
        valuation({
          status,
          reason:
            status === 'INDICATIVE'
              ? 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS'
              : 'WARRANT_BID_AVAILABLE',
          bid: status === 'AVAILABLE' ? '2.50' : null,
          ask: status === 'AVAILABLE' ? '2.55' : null,
          reference_price: '2.50',
          reference_price_type: status === 'AVAILABLE' ? 'BID' : 'LAST_TRADE',
          quote_age_seconds: status === 'INDICATIVE' ? 7200 : 30,
          quote_age_limit_exceeded: false,
          valuation_usable: status === 'AVAILABLE',
          market_value: status === 'AVAILABLE' ? '25.0000000000' : null,
          unrealized_gross_pnl: status === 'AVAILABLE' ? '5.0000000000' : null,
          unrealized_pnl_usable: status === 'AVAILABLE',
          unrealized_pnl_reason:
            status === 'AVAILABLE'
              ? 'COST_BASIS_CURRENCY_MATCHED'
              : 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS',
          analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
        }),
      );

      expect(
        await screen.findByText('Hinweis zur Kursbasis – Ursache nicht näher erläutert'),
      ).toBeVisible();
      expect(screen.queryByText(/Kursdaten veraltet|Produktkurs veraltet/)).not.toBeInTheDocument();
      expect(screen.getByText('25 EUR')).toBeVisible();
      expect(screen.getByText('5 EUR')).toBeVisible();
    },
  );

  it('explains an owner-qualified reference-price age limit without classifying it as STALE', async () => {
    show(
      valuation({
        status: 'INDICATIVE',
        reason: 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS',
        bid: null,
        ask: null,
        reference_price: '2.50',
        reference_price_type: 'PREVIOUS_CLOSE',
        quote_age_seconds: 7200,
        quote_age_limit_exceeded: true,
        valuation_usable: false,
        market_value: null,
        unrealized_gross_pnl: null,
        unrealized_pnl_usable: false,
        unrealized_pnl_reason: 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS',
        analysis_usable: true,
        analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
      }),
    );

    expect(
      await screen.findByText(
        'Referenzkurs überschreitet die gemeldete Altersgrenze – indikative Analyse',
      ),
    ).toBeVisible();
    expect(screen.getByText('Indikative Auswertung')).toBeVisible();
    expect(screen.queryByText(/Kursdaten veraltet|Produktkurs veraltet/)).not.toBeInTheDocument();
    expect(screen.getByText('Indikativer Wert (Schlusskurs)')).toBeVisible();
    expect(screen.getByText('25 EUR')).toBeVisible();
    expect(screen.getByText('5 EUR')).toBeVisible();
  });

  it('keeps LAST_AVAILABLE usable without calling it stale or qualifying missing purchase currency', async () => {
    show(
      valuation({
        status: 'LAST_AVAILABLE',
        reason: 'MARKET_CLOSED_LAST_AVAILABLE_QUOTE',
        analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
        quote_age_seconds: 39120,
        quote_age_limit_exceeded: true,
        unrealized_gross_pnl: null,
        unrealized_pnl_usable: false,
        unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
        analysis_unrealized_gross_pnl: null,
        analysis_unrealized_pnl_usable: false,
        analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
      }),
    );

    expect(
      await screen.findByText('Letzter verfügbarer Produktkurs – indikative Analyse'),
    ).toBeVisible();
    expect(screen.queryByText(/Kursdaten veraltet|Produktkurs veraltet/)).not.toBeInTheDocument();
    expect(screen.getByText('25 EUR')).toBeVisible();
    const pnl = screen.getByText('Indikativer unrealized gross P&L').parentElement!;
    expect(within(pnl).getByText('—')).toBeVisible();
    expect(within(pnl).getByText(/Kaufwährung.*nicht.*belegt/)).toBeVisible();
    expect(screen.queryByText('0 EUR')).not.toBeInTheDocument();
  });

  it.each([
    ['MISSING', 'WARRANT_QUOTE_MISSING', 'Produktkurs fehlt'],
    ['UNAVAILABLE', 'WARRANT_QUOTE_CAPABILITY_NOT_CONFIGURED', 'Produktkurs nicht verfügbar'],
    ['ERROR', 'WARRANT_QUOTE_LISTING_MISMATCH', 'Produktkurs prüfen'],
  ] as const)(
    'does not invent a reference quote or monetary values for unusable %s, even with a warning',
    async (status, reason, label) => {
      show(
        valuation({
          status,
          reason,
          bid: null,
          ask: null,
          currency: null,
          quote_observed_at: null,
          quote_age_seconds: null,
          market_value: null,
          unrealized_gross_pnl: null,
          unrealized_pnl_usable: false,
          unrealized_pnl_reason: reason,
          valuation_usable: false,
          analysis_usable: false,
          analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
          analysis_market_value: null,
          analysis_unrealized_gross_pnl: null,
          analysis_unrealized_pnl_usable: false,
          analysis_unrealized_pnl_reason: reason,
          reference_price: null,
          reference_price_type: null,
        }),
      );

      expect(await screen.findByText(label)).toBeVisible();
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
      expect(screen.queryByText('Originalhinweis zur Kursbasis')).not.toBeInTheDocument();
      expect(screen.queryByText(/Referenzkurs|Kursdaten veraltet/)).not.toBeInTheDocument();
      expect(screen.queryAllByRole('definition')).toHaveLength(0);
      expect(screen.queryByText('0 EUR')).not.toBeInTheDocument();
      expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    },
  );
});
