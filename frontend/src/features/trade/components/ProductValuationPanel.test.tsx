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
      valuation_usable: false,
      execution_usable: false,
      freshness_policy: null,
      analysis_usable: false,
      analysis_warning: null,
      analysis_market_value: null,
      analysis_unrealized_gross_pnl: null,
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

  it('shows BID-based market value for a fresh valid quote', async () => {
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
      valuation_usable: true,
      execution_usable: false,
      analysis_usable: true,
      analysis_warning: null,
      analysis_market_value: '25.00',
      analysis_unrealized_gross_pnl: '5.00',
      freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
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
    expect(screen.queryByText(/Kursdaten veraltet/)).not.toBeInTheDocument();
  });

  it('shows stale analysis with a warning without presenting a current valuation', async () => {
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
      valuation_usable: false,
      execution_usable: false,
      freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
      analysis_usable: true,
      analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
      analysis_market_value: '25.00',
      analysis_unrealized_gross_pnl: '5.00',
      source_attempts: [],
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Produktkurs veraltet')).toBeInTheDocument();
    const staleMessage = screen.getByText(/zu alt für eine belastbare aktuelle Depotbewertung/);
    expect(staleMessage).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('120 Min.');
    expect(screen.getByRole('status')).toHaveTextContent('Kursdaten veraltet');
    expect(screen.getByRole('status')).toHaveTextContent('Kursstand:');
    expect(screen.getByText('Indikativer Wert (letzter Bid)')).toBeInTheDocument();
    expect(screen.getByText('25 EUR')).toBeInTheDocument();
    expect(screen.getByText('5 EUR')).toBeInTheDocument();
    expect(screen.getByText(/keine Freigabe zur Orderausführung/)).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expect(screen.queryByText('Unrealized gross P&L')).not.toBeInTheDocument();
  });

  it('shows the previous close as an indicative weekend valuation', async () => {
    api.productValuation.mockResolvedValue({
      trade_id: 'trade-1',
      position_id: 'position-1',
      status: 'LAST_AVAILABLE',
      reason: 'MARKET_CLOSED_LAST_AVAILABLE_QUOTE',
      warrant_listing_id: 'listing-1',
      symbol: null,
      bid: '0.24',
      ask: '0.25',
      currency: 'EUR',
      quote_observed_at: '2026-09-11T19:59:13Z',
      quote_age_seconds: 39120,
      max_quote_age_seconds: 3600,
      market_value: '480.00',
      unrealized_gross_pnl: '-540.00',
      selected_source: 'VONTOBEL_MARKETS',
      valuation_usable: true,
      execution_usable: false,
      analysis_usable: true,
      analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
      analysis_market_value: '480.00',
      analysis_unrealized_gross_pnl: '-540.00',
      freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
      source_attempts: [],
    });

    render(<ProductValuationPanel tradeId="trade-1" />);

    expect(await screen.findByText('Letzter verfügbarer Produktkurs')).toBeInTheDocument();
    expect(screen.getByText('Indikativer Wert (letzter Bid)')).toBeInTheDocument();
    expect(screen.getByText('Indikativer unrealized gross P&L')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Kursdaten veraltet');
    expect(screen.getByText(/keine Freigabe zur Orderausführung/)).toBeInTheDocument();
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

  it.each(['LAST_TRADE', 'PREVIOUS_CLOSE'] as const)(
    'shows %s as its own indicative basis with unknown freshness and no invented bid',
    async (kind) => {
      api.productValuation.mockResolvedValue({
        trade_id: 'trade-1',
        position_id: 'position-1',
        status: 'INDICATIVE',
        reason: 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS',
        warrant_listing_id: 'frankfurt-listing',
        symbol: null,
        bid: null,
        ask: null,
        currency: 'EUR',
        quote_observed_at: null,
        quote_age_seconds: null,
        max_quote_age_seconds: 900,
        market_value: null,
        unrealized_gross_pnl: null,
        selected_source: 'FRANKFURT_QUOTES',
        valuation_usable: false,
        execution_usable: false,
        analysis_usable: true,
        monitoring_usable: true,
        analysis_warning: 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
        analysis_market_value: '462.00',
        analysis_unrealized_gross_pnl: '-558.00',
        freshness_policy: 'REFERENCE_PRICE_DISCLOSURE_V1',
        source_attempts: [],
        reference_price: '0.231',
        reference_price_type: kind,
        provider_identity: 'DE000VH2LU21',
        provider_exchange_code: 'XSC',
        quote_venue_mic: 'XFRA',
        quote_delay_seconds: null,
        quote_retrieved_at: '2026-09-12T10:00:00Z',
        quote_assessed_at: '2026-09-12T10:01:00Z',
      });
      render(<ProductValuationPanel tradeId="trade-1" />);
      expect(await screen.findByText('Indikative Auswertung')).toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent('Kurszeitpunkt unbekannt');
      expect(screen.getByRole('status')).toHaveTextContent('Sie entscheiden');
      expect(screen.getByText('0,231 EUR')).toBeInTheDocument();
      expect(screen.getByText('462 EUR')).toBeInTheDocument();
      expect(screen.getByText('-558 EUR')).toBeInTheDocument();
      expect(screen.getByText(/Bewertungsquelle: FRANKFURT_QUOTES/)).toHaveTextContent(
        'DE000VH2LU21',
      );
      expect(screen.getByText(/Handelsplatz: XFRA/)).toHaveTextContent(
        'Feed-Verzögerung: unbekannt',
      );
      expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
      expect(screen.queryByText('Indikativer Wert (letzter Bid)')).not.toBeInTheDocument();
      expect(
        screen.getByText(
          kind === 'LAST_TRADE'
            ? 'Indikativer Wert (letzter Handelspreis)'
            : 'Indikativer Wert (Schlusskurs)',
        ),
      ).toBeInTheDocument();
    },
  );
});
