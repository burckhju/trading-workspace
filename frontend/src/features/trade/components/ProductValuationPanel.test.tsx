import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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

const qualifiedValue: ProductPositionValuationResponse = {
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
  unrealized_pnl_usable: true,
  unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
  selected_source: 'SECONDARY',
  valuation_usable: true,
  execution_usable: false,
  analysis_usable: false,
  analysis_warning: null,
  analysis_market_value: null,
  analysis_unrealized_gross_pnl: null,
  analysis_unrealized_pnl_usable: false,
  analysis_unrealized_pnl_reason: 'NO_USABLE_WARRANT_QUOTE',
  freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
  source_attempts: [],
};

function panel(props: Partial<ComponentProps<typeof ProductValuationPanel>> = {}) {
  return (
    <ProductValuationPanel
      tradeId="trade-1"
      productId="product-1"
      position={openPosition}
      cancelled={false}
      positionRead={{ status: 'ready', revision: 1 }}
      {...props}
    />
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function metric(label: string) {
  const term = screen.getByText(label);
  return within(term.parentElement!).getAllByRole('definition')[0];
}

describe('ProductValuationPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.productValuation.mockResolvedValue(qualifiedValue);
  });

  afterEach(() => {
    expect(api.position).not.toHaveBeenCalled();
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
      unrealized_pnl_usable: false,
      unrealized_pnl_reason: 'NO_USABLE_WARRANT_QUOTE',
      selected_source: null,
      valuation_usable: false,
      execution_usable: false,
      freshness_policy: null,
      analysis_usable: false,
      analysis_warning: null,
      analysis_market_value: null,
      analysis_unrealized_gross_pnl: null,
      analysis_unrealized_pnl_usable: false,
      analysis_unrealized_pnl_reason: 'NO_USABLE_WARRANT_QUOTE',
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

    render(panel());

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
      unrealized_pnl_usable: true,
      unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
      selected_source: 'SECONDARY',
      valuation_usable: true,
      execution_usable: false,
      analysis_usable: true,
      analysis_warning: null,
      analysis_market_value: '25.00',
      analysis_unrealized_gross_pnl: '5.00',
      analysis_unrealized_pnl_usable: true,
      analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
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

    render(panel());

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
      unrealized_pnl_usable: false,
      unrealized_pnl_reason: 'WARRANT_QUOTE_STALE',
      selected_source: 'SECONDARY',
      valuation_usable: false,
      execution_usable: false,
      freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
      analysis_usable: true,
      analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
      analysis_market_value: '25.00',
      analysis_unrealized_gross_pnl: '5.00',
      analysis_unrealized_pnl_usable: true,
      analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
      source_attempts: [],
    });

    render(panel());

    expect(await screen.findByText('Produktkurs veraltet')).toBeInTheDocument();
    const staleMessage = screen.getByText(/zu alt für eine belastbare aktuelle Depotbewertung/);
    expect(staleMessage).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('2 Std. 0 Min.');
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
      unrealized_pnl_usable: true,
      unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
      selected_source: 'VONTOBEL_MARKETS',
      valuation_usable: true,
      execution_usable: false,
      analysis_usable: true,
      analysis_warning: 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY',
      analysis_market_value: '480.00',
      analysis_unrealized_gross_pnl: '-540.00',
      analysis_unrealized_pnl_usable: true,
      analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
      freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
      source_attempts: [],
    });

    render(panel());

    expect(await screen.findByText('Letzter verfügbarer Produktkurs')).toBeInTheDocument();
    expect(screen.getByText('Indikativer Wert (letzter Bid)')).toBeInTheDocument();
    expect(screen.getByText('Indikativer unrealized gross P&L')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Letzter verfügbarer Produktkurs – indikative Analyse',
    );
    expect(screen.getByText(/keine Freigabe zur Orderausführung/)).toBeInTheDocument();
  });

  it('uses the validated host position to exclude current valuation for a closed position', () => {
    render(
      panel({
        position: {
          ...openPosition,
          open_quantity: 0,
          closed_at: '2026-09-06T12:00:00Z',
          is_closed: true,
        },
      }),
    );

    expect(screen.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expect(api.productValuation).not.toHaveBeenCalled();
  });

  it.each(
    (['LAST_TRADE', 'PREVIOUS_CLOSE'] as const).flatMap((kind) =>
      [false, true].map((refreshFailed) => ({ kind, refreshFailed })),
    ),
  )(
    'shows $kind with refreshFailed=$refreshFailed as disclosed indicative analysis',
    async ({ kind, refreshFailed }) => {
      api.productValuation.mockResolvedValue({
        trade_id: 'trade-1',
        position_id: 'position-1',
        status: 'INDICATIVE',
        reason: refreshFailed
          ? 'LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED'
          : 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS',
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
        unrealized_pnl_usable: false,
        unrealized_pnl_reason: 'MARKET_CLOSED_LAST_AVAILABLE_QUOTE',
        selected_source: 'FRANKFURT_QUOTES',
        valuation_usable: false,
        execution_usable: false,
        analysis_usable: true,
        monitoring_usable: true,
        analysis_warning: refreshFailed
          ? 'QUOTE_REFRESH_FAILED_INDICATIVE_ANALYSIS_ONLY'
          : 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY',
        quote_refresh_error: refreshFailed ? 'FRANKFURT_HTTP_503' : null,
        quote_retained: refreshFailed,
        analysis_market_value: '462.00',
        analysis_unrealized_gross_pnl: '-558.00',
        analysis_unrealized_pnl_usable: true,
        analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
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
      render(panel());
      expect(await screen.findByText('Indikative Auswertung')).toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent(
        refreshFailed ? 'letzter erfolgreicher Abruf' : 'Kurszeitpunkt unbekannt',
      );
      if (refreshFailed) {
        expect(screen.getByRole('status')).toHaveTextContent('FRANKFURT_HTTP_503');
        expect(screen.getByText(/Gespeicherter Kurs:/)).toBeInTheDocument();
      }
      expect(screen.getByRole('status')).toHaveTextContent('Sie entscheiden');
      expect(screen.getByText('0,231 EUR')).toBeInTheDocument();
      expect(screen.getByText('462 EUR')).toBeInTheDocument();
      expect(screen.getByText('-558 EUR')).toBeInTheDocument();
      expect(screen.getByText(/Bewertungsquelle: FRANKFURT_QUOTES/)).toBeInTheDocument();
      expect(screen.getByText(/Feed-Verzögerung: unbekannt/)).toBeVisible();
      fireEvent.click(screen.getByText('Kursherkunft und Zeitbezüge anzeigen'));
      expect(screen.getByText(/Handelsplatz: XFRA/)).toHaveTextContent('DE000VH2LU21');
      expect(screen.getByText(/Handelsplatz: XFRA/)).toBeVisible();
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

  it.each(['loading', 'invalidated', 'error'] as const)(
    'waits for a validated host position while its read is %s',
    (status) => {
      render(panel({ positionRead: { status, revision: 2 } }));

      expect(screen.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
      expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
      expect(api.productValuation).not.toHaveBeenCalled();
    },
  );

  it.each([
    { name: 'trade cancellation', cancelled: true, position: openPosition },
    {
      name: 'position cancellation',
      cancelled: false,
      position: { ...openPosition, is_cancelled: true },
    },
  ])('does not request current valuation after $name', ({ cancelled, position }) => {
    render(panel({ cancelled, position }));

    expect(screen.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expect(api.productValuation).not.toHaveBeenCalled();
  });

  it.each([
    { name: 'trade', position: { ...openPosition, trade_id: 'other-trade' } },
    { name: 'product', position: { ...openPosition, product_id: 'other-product' } },
  ])('does not read against a host position with a different $name identity', ({ position }) => {
    render(panel({ position }));

    expect(screen.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expect(api.productValuation).not.toHaveBeenCalled();
  });

  it('makes one valuation read and no position read across unrelated renders and disclosure changes', async () => {
    api.productValuation.mockResolvedValue({
      ...qualifiedValue,
      position_basis: {
        definition_version: 'valuation-v1',
        basis_id: 'basis-1',
        position: openPosition,
        cost_basis_currency: 'EUR',
        currency_status: 'KNOWN',
        effective_execution_ids: ['buy-1'],
        buy_currency_evidence: [],
      },
      source_attempts: [
        {
          source: 'SECONDARY',
          status: 'AVAILABLE',
          reason: 'VALID_BID_AVAILABLE',
          delayed: false,
          observed_at: qualifiedValue.quote_observed_at,
          bid_available: true,
          ask_available: true,
        },
      ],
    });
    const { container, rerender } = render(panel());
    await screen.findByText('25 EUR');
    const signal = api.productValuation.mock.calls[0][1];
    expect(signal).toBeInstanceOf(AbortSignal);
    expect(api.productValuation).toHaveBeenCalledWith('trade-1', signal);

    for (const summary of container.querySelectorAll('summary')) {
      fireEvent.click(summary);
      fireEvent.click(summary);
    }
    rerender(panel({ position: { ...openPosition } }));

    expect(screen.getByText('25 EUR')).toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(1);
    expect(signal?.aborted).toBe(false);
  });

  it.each(['loading', 'invalidated', 'error'] as const)(
    'hides an already completed valuation when the host read becomes %s',
    async (status) => {
      const { rerender } = render(panel());
      await screen.findByText('25 EUR');

      rerender(panel({ positionRead: { status, revision: 2 } }));

      expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
      expect(screen.queryByText('5 EUR')).not.toBeInTheDocument();
      expect(api.productValuation).toHaveBeenCalledTimes(1);
    },
  );

  it('keeps a confirmed-write invalidation unavailable through failed host readback until a successful retry', async () => {
    const { rerender } = render(panel());
    await screen.findByText('25 EUR');

    rerender(panel({ positionRead: { status: 'invalidated', revision: 2 } }));
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    rerender(panel({ positionRead: { status: 'loading', revision: 3 } }));
    rerender(panel({ positionRead: { status: 'error', revision: 3 } }));
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(1);

    api.productValuation.mockResolvedValue({ ...qualifiedValue, market_value: '31.00' });
    rerender(panel({ positionRead: { status: 'ready', revision: 4 } }));
    expect(await screen.findByText('31 EUR')).toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(2);
  });

  it('clears completed results before a same-trade reload can resolve', async () => {
    const next = deferred<ProductPositionValuationResponse>();
    const { rerender } = render(panel());
    await screen.findByText('25 EUR');
    api.productValuation.mockReturnValueOnce(next.promise);

    rerender(panel({ positionRead: { status: 'ready', revision: 2 } }));

    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(2);
    await act(async () => {
      next.resolve({ ...qualifiedValue, market_value: '31.00' });
      await Promise.resolve();
    });
    expect(screen.getByText('31 EUR')).toBeInTheDocument();
  });

  it.each(['success', 'error'] as const)(
    'ignores a late %s from the previous same-trade read even if transport ignores abort',
    async (outcome) => {
      const old = deferred<ProductPositionValuationResponse>();
      api.productValuation.mockReturnValueOnce(old.promise);
      const { rerender } = render(panel());
      const oldSignal = api.productValuation.mock.calls[0][1];

      rerender(panel({ positionRead: { status: 'loading', revision: 2 } }));
      expect(oldSignal?.aborted).toBe(true);
      api.productValuation.mockResolvedValue({ ...qualifiedValue, market_value: '31.00' });
      rerender(panel({ positionRead: { status: 'ready', revision: 2 } }));
      await screen.findByText('31 EUR');

      await act(async () => {
        if (outcome === 'success') old.resolve({ ...qualifiedValue, market_value: '999.00' });
        else old.reject(new Error('Old valuation error'));
        await Promise.resolve();
      });

      expect(screen.getByText('31 EUR')).toBeInTheDocument();
      expect(screen.queryByText('999 EUR')).not.toBeInTheDocument();
      expect(screen.queryByText('Old valuation error')).not.toBeInTheDocument();
      expect(api.productValuation).toHaveBeenCalledTimes(2);
    },
  );

  it('does not restore old values when the replacement valuation fails', async () => {
    const old = deferred<ProductPositionValuationResponse>();
    api.productValuation.mockReturnValueOnce(old.promise);
    const { rerender } = render(panel());
    api.productValuation.mockRejectedValueOnce(new Error('Current valuation unavailable'));
    rerender(panel({ positionRead: { status: 'ready', revision: 2 } }));
    await screen.findByText('Current valuation unavailable');

    await act(async () => {
      old.resolve({ ...qualifiedValue, market_value: '999.00' });
      await Promise.resolve();
    });

    expect(screen.getByText('Current valuation unavailable')).toBeInTheDocument();
    expect(screen.queryByText('999 EUR')).not.toBeInTheDocument();
  });

  it.each(['success', 'error'] as const)(
    'isolates a late A %s through A→B→A without relying on a remount',
    async (outcome) => {
      const oldA = deferred<ProductPositionValuationResponse>();
      const newA = deferred<ProductPositionValuationResponse>();
      api.productValuation.mockReturnValueOnce(oldA.promise);
      const { rerender } = render(panel());
      const oldSignal = api.productValuation.mock.calls[0][1];
      api.productValuation.mockResolvedValueOnce({
        ...qualifiedValue,
        trade_id: 'trade-b',
        position_id: 'position-b',
        market_value: '42.00',
      });
      rerender(
        panel({
          tradeId: 'trade-b',
          productId: 'product-b',
          position: {
            ...openPosition,
            id: 'position-b',
            trade_id: 'trade-b',
            product_id: 'product-b',
          },
        }),
      );
      await screen.findByText('42 EUR');
      api.productValuation.mockReturnValueOnce(newA.promise);
      rerender(panel());
      expect(screen.queryByText('42 EUR')).not.toBeInTheDocument();
      expect(oldSignal?.aborted).toBe(true);

      await act(async () => {
        if (outcome === 'success') oldA.resolve({ ...qualifiedValue, market_value: '999.00' });
        else oldA.reject(new Error('Detached A error'));
        await Promise.resolve();
      });
      expect(screen.queryByText('999 EUR')).not.toBeInTheDocument();
      expect(screen.queryByText('Detached A error')).not.toBeInTheDocument();
      await act(async () => {
        newA.resolve({ ...qualifiedValue, market_value: '31.00' });
        await Promise.resolve();
      });
      expect(screen.getByText('31 EUR')).toBeInTheDocument();
      expect(api.productValuation).toHaveBeenCalledTimes(3);
    },
  );

  it('does not redisplay an already completed A result when returning from B with the same revision number', async () => {
    const pendingB = deferred<ProductPositionValuationResponse>();
    const newA = deferred<ProductPositionValuationResponse>();
    const { rerender } = render(panel());
    await screen.findByText('25 EUR');
    api.productValuation.mockReturnValueOnce(pendingB.promise);
    rerender(
      panel({
        tradeId: 'trade-b',
        productId: 'product-b',
        position: {
          ...openPosition,
          id: 'position-b',
          trade_id: 'trade-b',
          product_id: 'product-b',
        },
      }),
    );
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    api.productValuation.mockReturnValueOnce(newA.promise);
    rerender(panel());
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();

    await act(async () => {
      pendingB.reject(new Error('Detached B error'));
      await Promise.resolve();
    });
    expect(screen.queryByText('Detached B error')).not.toBeInTheDocument();
    await act(async () => {
      newA.resolve({ ...qualifiedValue, market_value: '31.00' });
      await Promise.resolve();
    });
    expect(screen.getByText('31 EUR')).toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(3);
  });

  it('keeps valuation errors independent and can read the next validated host revision', async () => {
    api.productValuation.mockRejectedValueOnce(new Error('Valuation service unavailable'));
    const { rerender } = render(panel());
    await screen.findByText('Valuation service unavailable');
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();

    rerender(panel({ positionRead: { status: 'ready', revision: 2 } }));

    expect(await screen.findByText('25 EUR')).toBeInTheDocument();
    expect(screen.queryByText('Valuation service unavailable')).not.toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(2);
  });

  it.each([
    { field: 'missing response', value: null as unknown as ProductPositionValuationResponse },
    {
      field: 'missing source attempts',
      value: {
        ...qualifiedValue,
        source_attempts: undefined,
      } as unknown as ProductPositionValuationResponse,
    },
    {
      field: 'missing basis position',
      value: {
        ...qualifiedValue,
        position_basis: {},
      } as unknown as ProductPositionValuationResponse,
    },
    { field: 'response trade', value: { ...qualifiedValue, trade_id: 'other-trade' } },
    { field: 'response position', value: { ...qualifiedValue, position_id: 'other-position' } },
    ...(['id', 'trade_id', 'product_id'] as const).map((field) => ({
      field: `basis ${field}`,
      value: {
        ...qualifiedValue,
        position_basis: {
          definition_version: 'valuation-v1',
          basis_id: 'basis-1',
          position: { ...openPosition, [field]: 'other-identity' },
          cost_basis_currency: 'EUR',
          currency_status: 'KNOWN' as const,
          effective_execution_ids: [],
          buy_currency_evidence: [],
        },
      },
    })),
  ])('rejects an unverified valuation: $field', async ({ field, value }) => {
    api.productValuation.mockResolvedValueOnce(value);
    await act(async () => {
      render(panel());
      await Promise.resolve();
    });

    expect(screen.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
    expect(
      screen.getByText(
        field.startsWith('missing')
          ? /Produktbewertung konnte nicht vollständig gelesen werden/
          : /Produktbewertung gehört nicht zu diesem Trade/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('Produktkurs verfügbar')).not.toBeInTheDocument();
    expect(screen.queryByText('25 EUR')).not.toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledTimes(1);
  });

  it.each([false, true])(
    'distinguishes missing amounts from genuine zero with analysis_usable=%s',
    async (analysis) => {
      api.productValuation.mockResolvedValueOnce({
        ...qualifiedValue,
        valuation_usable: !analysis,
        analysis_usable: analysis,
        analysis_warning: analysis ? 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY' : null,
        market_value: null,
        unrealized_gross_pnl: null,
        analysis_market_value: null,
        analysis_unrealized_gross_pnl: null,
        analysis_unrealized_pnl_usable: analysis,
      });
      const marketLabel = analysis ? 'Indikativer Wert (letzter Bid)' : 'Marktwert (Bid)';
      const pnlLabel = analysis ? 'Indikativer unrealized gross P&L' : 'Unrealized gross P&L';
      const { rerender } = render(panel());
      await screen.findByText(marketLabel);
      expect(metric(marketLabel)).toHaveTextContent('—');
      expect(metric(pnlLabel)).toHaveTextContent(/^—$/);
      expect(screen.queryByText('0 EUR')).not.toBeInTheDocument();

      api.productValuation.mockResolvedValueOnce({
        ...qualifiedValue,
        valuation_usable: !analysis,
        analysis_usable: analysis,
        analysis_warning: analysis ? 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY' : null,
        market_value: '0',
        unrealized_gross_pnl: '0',
        analysis_market_value: '0',
        analysis_unrealized_gross_pnl: '0',
        analysis_unrealized_pnl_usable: analysis,
      });
      rerender(panel({ positionRead: { status: 'ready', revision: 2 } }));
      await waitFor(() => expect(metric(marketLabel)).toHaveTextContent(/^0 EUR$/));
      expect(metric(pnlLabel)).toHaveTextContent(/^0 EUR$/);
    },
  );

  it.each([false, true])(
    'requires the independent P/L qualification with analysis_usable=%s even for KNOWN basis currency',
    async (analysis) => {
      api.productValuation.mockResolvedValueOnce({
        ...qualifiedValue,
        valuation_usable: !analysis,
        analysis_usable: analysis,
        analysis_warning: analysis ? 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY' : null,
        unrealized_gross_pnl: '999',
        unrealized_pnl_usable: false,
        analysis_market_value: '25',
        analysis_unrealized_gross_pnl: '999',
        analysis_unrealized_pnl_usable: false,
        position_basis: {
          definition_version: 'valuation-v1',
          basis_id: 'basis-1',
          position: openPosition,
          cost_basis_currency: 'EUR',
          currency_status: 'KNOWN',
          effective_execution_ids: [],
          buy_currency_evidence: [],
        },
      });
      render(panel());
      const pnlLabel = analysis ? 'Indikativer unrealized gross P&L' : 'Unrealized gross P&L';
      await screen.findByText(pnlLabel);

      expect(metric(pnlLabel)).toHaveTextContent(/^—$/);
      expect(screen.queryByText('999 EUR')).not.toBeInTheDocument();
      expect(screen.getByText('25 EUR')).toBeInTheDocument();
    },
  );
});
