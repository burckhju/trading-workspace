import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import { ProductValuationPanel } from './ProductValuationPanel';

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    position: vi.fn(),
    productValuation: vi.fn(),
  },
}));

const api = vi.mocked(tradeManagementApiClient);

const openPosition = {
  id: 'position-1',
  trade_id: 'trade-1',
  product_id: 'product-1',
  open_quantity: 10,
  cost_basis: '20.00',
  average_entry_price: '2.00',
  realized_gross_pnl: '0',
  opened_at: '2026-09-06T08:00:00Z',
  last_execution_at: '2026-09-06T08:00:00Z',
  closed_at: null,
  is_closed: false,
};

describe('ProductValuationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.position.mockResolvedValue(openPosition);
  });

  it('documents each unavailable source instead of inventing a product price', async () => {
    api.productValuation.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'UNAVAILABLE',
      reason: 'NO_USABLE_WARRANT_QUOTE',
      warrant_listing_id: 'listing-1',
      symbol: 'TEST12.STU',
      bid: null,
      ask: null,
      currency: null,
      quote_observed_at: null,
      quote_age_seconds: null,
      max_quote_age_seconds: null,
      market_value: null,
      unrealized_gross_pnl: null,
      selected_source: null,
      source_attempts: [
        {
          source: 'EODHD',
          status: 'UNAVAILABLE',
          reason: 'capability not configured',
          delayed: false,
          observed_at: null,
          bid_available: false,
          ask_available: false,
        },
        {
          source: 'BOERSE_STUTTGART_DELAYED',
          status: 'UNAVAILABLE',
          reason: 'schema not verified',
          delayed: true,
          observed_at: null,
          bid_available: false,
          ask_available: false,
        },
      ],
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Produktkurs nicht verfügbar')).toBeInTheDocument();
    expect(screen.getByText(/Keine der geprüften Kursquellen/)).toBeInTheDocument();
    expect(screen.getByText(/Geprüfte Kursquellen anzeigen/)).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
  });

  it('shows BID-based market value and selected source when a fresh valid quote exists', async () => {
    api.productValuation.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'AVAILABLE',
      reason: 'WARRANT_BID_AVAILABLE',
      warrant_listing_id: 'listing-1',
      symbol: 'TEST12.STU',
      bid: '2.50',
      ask: '2.55',
      currency: 'EUR',
      quote_observed_at: '2026-09-06T12:00:00Z',
      quote_age_seconds: 900,
      max_quote_age_seconds: 3600,
      market_value: '25.00',
      unrealized_gross_pnl: '5.00',
      selected_source: 'SECONDARY',
      source_attempts: [
        {
          source: 'EODHD',
          status: 'UNAVAILABLE',
          reason: 'not configured',
          delayed: false,
          observed_at: null,
          bid_available: false,
          ask_available: false,
        },
        {
          source: 'SECONDARY',
          status: 'AVAILABLE',
          reason: 'VALID_BID_AVAILABLE',
          delayed: true,
          observed_at: '2026-09-06T12:00:00Z',
          bid_available: true,
          ask_available: true,
        },
      ],
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Produktkurs verfügbar')).toBeInTheDocument();
    expect(screen.getByText('Marktwert (Bid)')).toBeInTheDocument();
    expect(screen.getByText('Unrealized gross P&L')).toBeInTheDocument();
    expect(screen.getByText(/Bewertungsquelle: SECONDARY/)).toHaveTextContent('15 Min.');
  });

  it(
    'shows a stale quote as data problem and does not render market value or unrealized pnl',
    async () => {
      api.productValuation.mockResolvedValue({
        trade_id: 'trade-1',
        position_id: 'position-1',
        status: 'STALE',
        reason: 'WARRANT_QUOTE_STALE',
        warrant_listing_id: 'listing-1',
        symbol: 'TEST12.STU',
        bid: '2.50',
        ask: '2.55',
        currency: 'EUR',
        quote_observed_at: '2026-09-06T10:00:00Z',
        quote_age_seconds: 7200,
        max_quote_age_seconds: 3600,
        market_value: null,
        unrealized_gross_pnl: null,
        selected_source: 'SECONDARY',
        source_attempts: [],
      });

      render(<ProductValuationPanel tradeId="trade-1" />);

      expect(await screen.findByText('Produktkurs veraltet')).toBeInTheDocument();
      expect(
        screen.getByText(/zu alt für eine belastbare aktuelle Depotbewertung/),
      ).toBeInTheDocument();
      expect(screen.getByText(/120 Min\./)).toBeInTheDocument();
      expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
      expect(screen.queryByText('Unrealized gross P&L')).not.toBeInTheDocument();
    },
  );

  it('does not request a quote for a closed position', async () => {
    api.position.mockResolvedValue({
      ...openPosition,
      open_quantity: 0,
      closed_at: '2026-09-06T12:00:00Z',
      is_closed: true,
    });

    const { container } = render(<ProductValuationPanel tradeId="trade-1" />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(api.position).toHaveBeenCalled();
    expect(api.productValuation).not.toHaveBeenCalled();
  });
});
