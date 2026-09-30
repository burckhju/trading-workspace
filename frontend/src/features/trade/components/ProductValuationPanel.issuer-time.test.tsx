import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import type { ProductPositionValuationResponse } from '../types/api';
import { ProductValuationPanel } from './ProductValuationPanel';

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: { position: vi.fn(), productValuation: vi.fn() },
}));

const api = vi.mocked(tradeManagementApiClient);

const quote: ProductPositionValuationResponse = {
  trade_id: 'trade-1',
  position_id: 'position-1',
  status: 'INDICATIVE',
  reason: 'QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
  warrant_listing_id: 'listing-1',
  symbol: null,
  bid: '0.0230',
  ask: '0.0400',
  currency: 'EUR',
  quote_observed_at: null,
  quote_age_seconds: null,
  max_quote_age_seconds: 3600,
  market_value: null,
  unrealized_gross_pnl: null,
  selected_source: 'MORGAN_STANLEY',
  quote_provider: 'MORGAN_STANLEY',
  valuation_usable: false,
  execution_usable: false,
  analysis_usable: true,
  monitoring_usable: true,
  analysis_warning: 'QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
  analysis_market_value: '0.2300',
  analysis_unrealized_gross_pnl: '-1.7700',
  freshness_policy: 'UNKNOWN_TIMESTAMP_DISCLOSURE_V1',
  source_attempts: [],
  quote_time_text: '21/09/2026 20:12:49.77',
  quote_time_basis: 'LOCAL_DATETIME_TIMEZONE_UNKNOWN',
  bid_volume: 0,
  ask_volume: 0,
};

describe('issuer quote time disclosure', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.position.mockResolvedValue({
      id: 'position-1',
      trade_id: 'trade-1',
      product_id: 'product-1',
      open_quantity: 10,
      cost_basis: '2',
      average_entry_price: '0.2',
      realized_gross_pnl: '0',
      opened_at: '2026-09-01T00:00:00Z',
      last_execution_at: '2026-09-01T00:00:00Z',
      closed_at: null,
      is_closed: false,
    });
  });

  it('keeps the full local timestamp verbatim and discloses zero volumes', async () => {
    api.productValuation.mockResolvedValue(quote);
    render(<ProductValuationPanel tradeId="trade-1" />);
    expect(
      await screen.findAllByText(/Quellzeit 21\/09\/2026 20:12:49.77 \(Zeitzone unbekannt\)/),
    ).toHaveLength(2);
    expect(screen.queryByText(/Datum und Zeitzone unbekannt/)).not.toBeInTheDocument();
    expect(screen.getAllByText('Volumen 0')).toHaveLength(2);
    expect(screen.getByText(/keine handelbare Stückzahl/)).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
  });

  it('preserves the JPMorgan time-only disclosure', async () => {
    api.productValuation.mockResolvedValue({
      ...quote,
      quote_provider: 'JPMORGAN',
      selected_source: 'JPMORGAN',
      reason: 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
      analysis_warning: 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
      quote_time_text: '20:12:49',
      quote_time_basis: 'DATE_AND_TIMEZONE_UNKNOWN',
      bid_volume: 125000,
      ask_volume: 125000,
    });
    render(<ProductValuationPanel tradeId="trade-1" />);
    expect(
      await screen.findAllByText(/Quelluhrzeit 20:12:49 \(Datum und Zeitzone unbekannt\)/),
    ).toHaveLength(2);
    expect(screen.queryByText(/keine handelbare Stückzahl/)).not.toBeInTheDocument();
  });
});
