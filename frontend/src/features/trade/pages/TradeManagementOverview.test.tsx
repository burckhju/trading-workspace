import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import type {
  PositionResponse,
  ProductPositionValuationResponse,
  TradeManagementStateResponse,
  TradeResponse,
} from '../types/api';
import { TradeManagementPage } from './index';

// Exercise the real route, host, valuation reader, qualification and manual forms.
// Chart internals, historical sources and booking commands have their own integration suites.
vi.mock('../../operational_workspace', () => ({
  PositionPriceHistory: ({ reloadToken }: { reloadToken: number }) => (
    <output aria-label="History revision">{reloadToken}</output>
  ),
}));
vi.mock('../../alert/components/PositionRiskPanel', () => ({ PositionRiskPanel: () => null }));
vi.mock('../../alert/components/TradeAlertsPanel', () => ({ TradeAlertsPanel: () => null }));
vi.mock('../components/AdditionalPurchasePanel', () => ({ AdditionalPurchasePanel: () => null }));
vi.mock('../components/TradeCancellationPanel', () => ({ TradeCancellationPanel: () => null }));
vi.mock('../components/TradeSourcesView', () => ({
  TradeSourcesView: () => <h1>Historical trade sources</h1>,
}));
vi.mock('../components/ExecutionDatesPanel', () => ({
  ExecutionDatesPanel: ({
    tradeId,
    onChanged,
  }: {
    tradeId: string;
    onChanged: () => Promise<void>;
  }) => {
    const [receipt, setReceipt] = useState(false);
    const [readback, setReadback] = useState('');
    return (
      <section id="execution-dates" tabIndex={-1} aria-label="Booking owner test boundary">
        <button
          onClick={() => {
            setReceipt(true);
            window.dispatchEvent(
              new CustomEvent(tradeTimelineChangedEvent, { detail: { tradeId } }),
            );
          }}
        >
          Confirm booking write
        </button>
        <button
          onClick={() => {
            void onChanged().then(
              () => setReadback('Host readback succeeded'),
              (error: unknown) =>
                setReadback(
                  `Host readback failed: ${error instanceof Error ? error.message : 'Unknown'}`,
                ),
            );
          }}
        >
          Read confirmed booking
        </button>
        {receipt && <p>Confirmed booking receipt</p>}
        {readback && <p>{readback}</p>}
      </section>
    );
  },
}));
vi.mock('../../product/services/client', () => ({ warrantApiClient: { get: vi.fn() } }));
vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    trade: vi.fn(),
    position: vi.fn(),
    managementState: vi.fn(),
    productValuation: vi.fn(),
    executionCurrencyPreview: vi.fn(),
    sell: vi.fn(),
    changeStop: vi.fn(),
    changeTarget: vi.fn(),
    updateThesis: vi.fn(),
    addNote: vi.fn(),
  },
}));

const api = vi.mocked(tradeManagementApiClient);
const products = vi.mocked(warrantApiClient);

function fixture(id = 'trade-a') {
  const trade: TradeResponse = {
    id,
    product_id: `product-${id}`,
    origin: 'EXTERNAL',
    trade_plan_id: null,
    trade_plan_version_id: null,
    product_selection_id: null,
    product_evaluation_id: null,
    created_at: '2026-10-01T08:00:00Z',
  };
  const warrant: WarrantResponse = {
    id: trade.product_id,
    workspace_id: 'workspace',
    issuer_id: 'issuer',
    underlying_id: 'underlying',
    product_family: 'WARRANT',
    display_name: `Overview warrant ${id}`,
    isin: 'DE000TEST1234',
    wkn: 'TEST12',
    lifecycle_status: 'ACTIVE',
    version: 1,
    created_at: trade.created_at,
    updated_at: trade.created_at,
  };
  const position: PositionResponse = {
    id: `position-${id}`,
    trade_id: id,
    product_id: trade.product_id,
    open_quantity: 10,
    cost_basis: '8123.45',
    average_entry_price: '812.345',
    realized_gross_pnl: '7123.45',
    opened_at: trade.created_at,
    last_execution_at: trade.created_at,
    closed_at: null,
    is_closed: false,
  };
  const management: TradeManagementStateResponse = {
    trade_id: id,
    stop_price: null,
    target_price: null,
    thesis: 'Stored thesis',
    notes: [],
    last_event_at: null,
  };
  return { trade, warrant, position, management };
}

function valuation(
  id = 'trade-a',
  overrides: Partial<ProductPositionValuationResponse> = {},
): ProductPositionValuationResponse {
  return {
    trade_id: id,
    position_id: `position-${id}`,
    status: 'AVAILABLE',
    reason: 'WARRANT_BID_AVAILABLE',
    warrant_listing_id: 'listing',
    symbol: 'TEST12',
    bid: '2.51',
    ask: '2.60',
    currency: 'EUR',
    quote_observed_at: '2026-10-01T12:00:00Z',
    quote_age_seconds: 60,
    max_quote_age_seconds: 3600,
    market_value: '25.10',
    unrealized_gross_pnl: '5.10',
    unrealized_pnl_usable: true,
    unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    selected_source: 'SYNTHETIC_INITIAL_QUOTE',
    valuation_usable: true,
    execution_usable: false,
    analysis_usable: true,
    analysis_warning: null,
    analysis_market_value: '25.10',
    analysis_unrealized_gross_pnl: '5.10',
    analysis_unrealized_pnl_usable: true,
    analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
    freshness_policy: 'DE_WARRANT_SESSION_FRESHNESS_V1',
    source_attempts: [],
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

async function settle(callback: () => void) {
  await act(async () => {
    callback();
    await Promise.resolve();
  });
}

function show(url = '/trade-management?trade_id=trade-a#trade-overview') {
  const router = createMemoryRouter([{ path: '*', element: <TradeManagementPage /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
  return router;
}

async function loaded(id = 'trade-a') {
  await screen.findByRole('heading', { name: new RegExp(`Overview warrant ${id}`) });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled());
}

async function quoted(source = 'SYNTHETIC_INITIAL_QUOTE') {
  await screen.findByText(new RegExp(`Bewertungsquelle: ${source}`));
}

function drafts() {
  const quantity = screen.getByLabelText('Verkaufsmenge');
  const note = screen.getByLabelText('Neue Management-Notiz');
  fireEvent.change(quantity, { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('Verkaufspreis'), { target: { value: '2.75' } });
  fireEvent.change(note, { target: { value: 'Parallel manual draft' } });
  return () => {
    expect(screen.getByLabelText('Verkaufsmenge')).toBe(quantity);
    expect(quantity).toHaveValue(3);
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.75);
    expect(screen.getByLabelText('Neue Management-Notiz')).toBe(note);
    expect(note).toHaveValue('Parallel manual draft');
  };
}

function reload() {
  fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
}

function confirmWrite() {
  fireEvent.click(screen.getByRole('button', { name: 'Confirm booking write' }));
}

function readback() {
  fireEvent.click(screen.getByRole('button', { name: 'Read confirmed booking' }));
}

beforeEach(() => {
  vi.resetAllMocks();
  api.trade.mockImplementation((id) => Promise.resolve(fixture(id).trade));
  api.position.mockImplementation((id) => Promise.resolve(fixture(id).position));
  api.managementState.mockImplementation((id) => Promise.resolve(fixture(id).management));
  products.get.mockImplementation((id) =>
    Promise.resolve(fixture(id.replace('product-', '')).warrant),
  );
  api.productValuation.mockImplementation((id) => Promise.resolve(valuation(id)));
  api.executionCurrencyPreview.mockResolvedValue({
    currency_code: 'EUR',
    source: 'PRIOR_BUYS',
    source_execution_ids: ['buy'],
    confirmation_ids: [],
  });
});

describe('UX2-B host overview and independent valuation readback', () => {
  it('places the existing valuation in the overview after exactly one validated position read', async () => {
    show();
    await loaded();
    await quoted();
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getByRole('heading', { name: 'Produktbewertung' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { name: 'Produktbewertung' })).toHaveLength(1);
    expect(api.position).toHaveBeenCalledExactlyOnceWith('trade-a', expect.any(AbortSignal));
    expect(api.productValuation).toHaveBeenCalledExactlyOnceWith(
      'trade-a',
      expect.any(AbortSignal),
    );
    expect(overview.getByText('Marktwert (Bid)').nextElementSibling).toHaveTextContent('25,1 EUR');
    expect(overview.getByText('Unrealized gross P&L').nextElementSibling).toHaveTextContent(
      '5,1 EUR',
    );
    for (const rawLabel of ['Cost Basis', 'Average Entry', 'Realized gross P&L']) {
      expect(overview.queryByText(rawLabel)).not.toBeInTheDocument();
    }
    expect(overview.queryByText(/8\.123,45|812,345|7\.123,45/)).not.toBeInTheDocument();
  });

  it('waits for the validated product identity before requesting valuation', async () => {
    const product = deferred<WarrantResponse>();
    products.get.mockReturnValueOnce(product.promise);
    show();
    await waitFor(() => expect(products.get).toHaveBeenCalledOnce());
    expect(api.position).toHaveBeenCalledOnce();
    expect(api.productValuation).not.toHaveBeenCalled();
    await settle(() => product.resolve(fixture().warrant));
    await quoted();
    expect(api.productValuation).toHaveBeenCalledOnce();
  });

  it.each(['CLOSED', 'CANCELLED'] as const)(
    'keeps %s lifecycle explicit without requesting a current product valuation',
    async (status) => {
      if (status === 'CLOSED') {
        api.position.mockResolvedValue({
          ...fixture().position,
          open_quantity: 0,
          is_closed: true,
          closed_at: '2026-10-02T08:00:00Z',
        });
      } else {
        api.trade.mockResolvedValue({ ...fixture().trade, cancelled_at: '2026-10-02T08:00:00Z' });
      }
      show();
      await loaded();
      const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
      expect(overview.getByRole('heading', { name: status })).toBeInTheDocument();
      expect(api.position).toHaveBeenCalledOnce();
      expect(api.productValuation).not.toHaveBeenCalled();
      expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
      expect(overview.queryByText('Nächster Schritt')).not.toBeInTheDocument();
      if (status === 'CLOSED') {
        expect(overview.getByText('Offene Menge').nextElementSibling).toHaveTextContent('0');
      }
    },
  );

  it('does not request current values without a trade or in the historical sources route', async () => {
    const router = show('/trade-management');
    expect(api.position).not.toHaveBeenCalled();
    expect(api.productValuation).not.toHaveBeenCalled();
    await act(async () => {
      await router.navigate(
        '/trade-management?trade_id=trade-a&view=sources&review_version_id=historical-review',
      );
    });
    expect(screen.getByRole('heading', { name: 'Historical trade sources' })).toBeInTheDocument();
    expect(api.position).not.toHaveBeenCalled();
    expect(api.productValuation).not.toHaveBeenCalled();
  });

  it.each(['missing', 'failed', 'foreign'] as const)(
    'does not qualify a valuation when the host position is %s',
    async (outcome) => {
      if (outcome === 'missing') api.position.mockResolvedValue(null as never);
      if (outcome === 'failed') api.position.mockRejectedValue(new Error('Position unreadable'));
      if (outcome === 'foreign')
        api.position.mockResolvedValue({ ...fixture().position, trade_id: 'foreign-trade' });
      show();
      await waitFor(() => expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled());
      expect(api.position).toHaveBeenCalledOnce();
      expect(api.productValuation).not.toHaveBeenCalled();
      expect(screen.queryByRole('region', { name: 'Trade und Position' })).not.toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: 'CLOSED' })).not.toBeInTheDocument();
    },
  );

  it('keeps a missing qualified amount separate from a genuine zero result', async () => {
    api.productValuation.mockResolvedValue(
      valuation('trade-a', {
        analysis_market_value: null,
        analysis_unrealized_gross_pnl: '0',
      }),
    );
    show();
    await quoted();
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getByText('Marktwert (Bid)').nextElementSibling).toHaveTextContent('— EUR');
    expect(overview.getByText('Unrealized gross P&L').nextElementSibling).toHaveTextContent(
      '0 EUR',
    );
  });

  it('keeps valuation and G/V qualification independent from the usable EUR quote', async () => {
    api.productValuation.mockResolvedValue(
      valuation('trade-a', {
        analysis_unrealized_gross_pnl: '9123.45',
        analysis_unrealized_pnl_usable: false,
        analysis_unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
      }),
    );
    show();
    await quoted();
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getByText('Marktwert (Bid)').nextElementSibling).toHaveTextContent('25,1 EUR');
    expect(overview.getByText('Unrealized gross P&L').nextElementSibling).toHaveTextContent('—');
    expect(overview.queryByText(/9\.123,45/)).not.toBeInTheDocument();
    expect(overview.getByText(/Die Kaufwährung ist.*Kostenbasis nicht belegt/)).toBeInTheDocument();
  });

  it('preserves two manual drafts and performs no position or valuation reads on hash and detail changes', async () => {
    const router = show();
    await loaded();
    await quoted();
    const expectDrafts = drafts();
    const positionSignal = api.position.mock.calls[0][1];
    const valueSignal = api.productValuation.mock.calls[0][1];
    for (const hash of ['#execution-dates', '#trade-overview', '#sale-capture']) {
      await act(async () => {
        await router.navigate(`/trade-management?trade_id=trade-a${hash}`);
      });
      expectDrafts();
    }
    for (const details of screen
      .getByRole('region', { name: 'Trade und Position' })
      .querySelectorAll('details')) {
      fireEvent.click(details.querySelector('summary')!);
    }
    expectDrafts();
    expect(api.position).toHaveBeenCalledOnce();
    expect(api.productValuation).toHaveBeenCalledOnce();
    expect(positionSignal?.aborted).toBe(false);
    expect(valueSignal?.aborted).toBe(false);
    expect(api.sell).not.toHaveBeenCalled();
    expect(api.addNote).not.toHaveBeenCalled();
  });

  it('invalidates an already displayed valuation on same-trade reload while preserving draft DOM and the chart revision until success', async () => {
    show();
    await loaded();
    await quoted();
    const expectDrafts = drafts();
    const pendingPosition = deferred<PositionResponse>();
    api.position.mockReturnValueOnce(pendingPosition.promise);
    api.productValuation.mockResolvedValueOnce(
      valuation('trade-a', { selected_source: 'SYNTHETIC_RELOADED_QUOTE' }),
    );
    const originalSignal = api.productValuation.mock.calls[0][1];
    reload();
    expect(screen.queryByText(/SYNTHETIC_INITIAL_QUOTE/)).not.toBeInTheDocument();
    expect(api.productValuation).toHaveBeenCalledOnce();
    expect(originalSignal?.aborted).toBe(true);
    expect(screen.getByLabelText('History revision')).toHaveTextContent('0');
    expectDrafts();
    await settle(() => pendingPosition.resolve({ ...fixture().position, open_quantity: 8 }));
    await quoted('SYNTHETIC_RELOADED_QUOTE');
    expect(api.position).toHaveBeenCalledTimes(2);
    expect(api.productValuation).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('History revision')).toHaveTextContent('1');
    expectDrafts();
  });

  it('invalidates at the confirmed write before readback and does not await a separate valuation result for readback success', async () => {
    show();
    await loaded();
    await quoted();
    const expectDrafts = drafts();
    confirmWrite();
    expect(screen.getByText('Confirmed booking receipt')).toBeInTheDocument();
    expect(screen.queryByText(/SYNTHETIC_INITIAL_QUOTE/)).not.toBeInTheDocument();
    expect(api.position).toHaveBeenCalledOnce();
    expect(api.productValuation).toHaveBeenCalledOnce();
    expect(screen.getByLabelText('History revision')).toHaveTextContent('0');
    const pendingValuation = deferred<ProductPositionValuationResponse>();
    api.productValuation.mockReturnValueOnce(pendingValuation.promise);
    readback();
    await screen.findByText('Host readback succeeded');
    expect(api.position).toHaveBeenCalledTimes(2);
    expect(api.productValuation).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('History revision')).toHaveTextContent('1');
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expectDrafts();
    await settle(() => pendingValuation.reject(new Error('Valuation service unavailable')));
    await screen.findByText('Valuation service unavailable');
    expect(screen.getByText('Confirmed booking receipt')).toBeInTheDocument();
    expect(screen.getByText('Host readback succeeded')).toBeInTheDocument();
    expect(screen.queryByText(/Host readback failed/)).not.toBeInTheDocument();
    expectDrafts();
  });

  it('keeps the receipt and invalidated valuation after failed host readback until a successful later reload', async () => {
    show();
    await loaded();
    await quoted();
    const expectDrafts = drafts();
    confirmWrite();
    api.position.mockRejectedValueOnce(new Error('Host storage unavailable'));
    readback();
    await screen.findByText('Host readback failed: Host storage unavailable');
    expect(screen.getByText('Confirmed booking receipt')).toBeInTheDocument();
    expect(screen.queryByText(/SYNTHETIC_INITIAL_QUOTE/)).not.toBeInTheDocument();
    expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
    expect(api.position).toHaveBeenCalledTimes(2);
    expect(api.productValuation).toHaveBeenCalledOnce();
    expect(screen.getByLabelText('History revision')).toHaveTextContent('0');
    expectDrafts();
    api.productValuation.mockResolvedValueOnce(
      valuation('trade-a', { selected_source: 'SYNTHETIC_RECOVERED_QUOTE' }),
    );
    reload();
    await quoted('SYNTHETIC_RECOVERED_QUOTE');
    expect(api.position).toHaveBeenCalledTimes(3);
    expect(api.productValuation).toHaveBeenCalledTimes(2);
    expect(screen.getByText('Confirmed booking receipt')).toBeInTheDocument();
    expectDrafts();
  });

  it('ignores a foreign timeline event without invalidating the accepted result', async () => {
    show();
    await loaded();
    await quoted();
    await settle(() => {
      window.dispatchEvent(
        new CustomEvent(tradeTimelineChangedEvent, { detail: { tradeId: 'trade-b' } }),
      );
    });
    expect(screen.getByText(/SYNTHETIC_INITIAL_QUOTE/)).toBeInTheDocument();
    expect(api.position).toHaveBeenCalledOnce();
    expect(api.productValuation).toHaveBeenCalledOnce();
  });

  it.each(['success', 'error'] as const)(
    'ignores a late pre-write valuation %s when the confirmed write has no successful host readback',
    async (outcome) => {
      const old = deferred<ProductPositionValuationResponse>();
      api.productValuation.mockReturnValueOnce(old.promise);
      show();
      await loaded();
      await waitFor(() => expect(api.productValuation).toHaveBeenCalledOnce());
      const oldSignal = api.productValuation.mock.calls[0][1];
      confirmWrite();
      api.position.mockRejectedValueOnce(new Error('Readback offline'));
      readback();
      await screen.findByText('Host readback failed: Readback offline');
      await settle(() => {
        if (outcome === 'success') old.resolve(valuation());
        else old.reject(new Error('Obsolete valuation error'));
      });
      expect(oldSignal?.aborted).toBe(true);
      expect(screen.queryByText(/SYNTHETIC_INITIAL_QUOTE/)).not.toBeInTheDocument();
      expect(screen.queryByText('Obsolete valuation error')).not.toBeInTheDocument();
      expect(screen.getByText('Confirmed booking receipt')).toBeInTheDocument();
      expect(api.productValuation).toHaveBeenCalledOnce();
    },
  );

  it.each(['success', 'error'] as const)(
    'keeps the new A result after A → B → A when the first A valuation ends with a late %s',
    async (outcome) => {
      const old = deferred<ProductPositionValuationResponse>();
      api.productValuation
        .mockReturnValueOnce(old.promise)
        .mockResolvedValueOnce(valuation('trade-b', { selected_source: 'SYNTHETIC_B_QUOTE' }))
        .mockResolvedValueOnce(valuation('trade-a', { selected_source: 'SYNTHETIC_NEW_A_QUOTE' }));
      const router = show();
      await loaded();
      await waitFor(() => expect(api.productValuation).toHaveBeenCalledOnce());
      const oldSignal = api.productValuation.mock.calls[0][1];
      await act(async () => router.navigate('/trade-management?trade_id=trade-b'));
      await quoted('SYNTHETIC_B_QUOTE');
      await act(async () => router.navigate('/trade-management?trade_id=trade-a'));
      await quoted('SYNTHETIC_NEW_A_QUOTE');
      await settle(() => {
        if (outcome === 'success') old.resolve(valuation());
        else old.reject(new Error('First A obsolete error'));
      });
      expect(oldSignal?.aborted).toBe(true);
      expect(screen.getByText(/SYNTHETIC_NEW_A_QUOTE/)).toBeInTheDocument();
      expect(
        screen.queryByText(/SYNTHETIC_INITIAL_QUOTE|SYNTHETIC_B_QUOTE/),
      ).not.toBeInTheDocument();
      expect(screen.queryByText('First A obsolete error')).not.toBeInTheDocument();
      expect(api.position).toHaveBeenCalledTimes(3);
      expect(api.productValuation).toHaveBeenCalledTimes(3);
    },
  );

  it.each(['success', 'error'] as const)(
    'does not revive an already completed A %s while the new A result is still loading',
    async (outcome) => {
      const nextA = deferred<ProductPositionValuationResponse>();
      if (outcome === 'success') api.productValuation.mockResolvedValueOnce(valuation());
      else api.productValuation.mockRejectedValueOnce(new Error('Completed old A error'));
      api.productValuation
        .mockResolvedValueOnce(valuation('trade-b', { selected_source: 'SYNTHETIC_B_QUOTE' }))
        .mockReturnValueOnce(nextA.promise);
      const router = show();
      await loaded();
      if (outcome === 'success') await quoted();
      else await screen.findByText('Completed old A error');
      await act(async () => router.navigate('/trade-management?trade_id=trade-b'));
      await quoted('SYNTHETIC_B_QUOTE');
      await act(async () => router.navigate('/trade-management?trade_id=trade-a'));
      await loaded();
      expect(
        screen.queryByText(/SYNTHETIC_INITIAL_QUOTE|SYNTHETIC_B_QUOTE/),
      ).not.toBeInTheDocument();
      expect(screen.queryByText('Completed old A error')).not.toBeInTheDocument();
      expect(screen.queryByText('Marktwert (Bid)')).not.toBeInTheDocument();
      expect(api.position).toHaveBeenCalledTimes(3);
      expect(api.productValuation).toHaveBeenCalledTimes(3);
      await settle(() =>
        nextA.resolve(valuation('trade-a', { selected_source: 'SYNTHETIC_FINAL_A_QUOTE' })),
      );
      await quoted('SYNTHETIC_FINAL_A_QUOTE');
    },
  );
});
