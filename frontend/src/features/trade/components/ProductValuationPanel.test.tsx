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

  it('shows fail-closed provider capability instead of inventing a product price', async () => {
    api.productValuation.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'UNAVAILABLE',
      reason: 'WARRANT_QUOTE_CAPABILITY_NOT_CONFIGURED',
      warrant_listing_id: 'listing-1',
      symbol: 'TEST12.STU',
      bid: null,
      ask: null,
      currency: null,
      quote_observed_at: null,
      market_value: null,
      unrealized_gross_pnl: null,
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Produktkurs nicht verfügbar')).toBeInTheDocument();
    expect(screen.getByText(/kein verifizierter Bid\/Ask-Transport/)).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
  });

  it('shows BID-based market value and unrealized gross pnl when a valid quote exists', async () => {
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
      market_value: '25.00',
      unrealized_gross_pnl: '5.00',
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Produktkurs verfügbar')).toBeInTheDocument();
    expect(screen.getByText('Marktwert (Bid)')).toBeInTheDocument();
    expect(screen.getByText('Unrealized gross P&L')).toBeInTheDocument();
    expect(screen.getByText(/Stop und Target werden weiterhin ausschließlich/)).toBeInTheDocument();
  });

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
