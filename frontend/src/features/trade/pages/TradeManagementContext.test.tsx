import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { useRef, useState } from 'react';
import {
  createMemoryRouter,
  MemoryRouter,
  RouterProvider,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../../post_trade/services/client';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient } from '../services/client';
import { localToday } from '../services/capture';
import { useTradePendingChanges } from '../components/TradePendingChanges';
import type {
  PositionResponse,
  SaleResponse,
  TradeManagementStateResponse,
  TradeResponse,
} from '../types/api';
import { TradeManagementPage } from './TradeManagementPage';

// Isolate page/route ownership. The real child workflows remain covered in their
// existing suites and the disposable PostgreSQL browser regression.
vi.mock('../../alert/components/TradeAlertsPanel', () => ({
  TradeAlertsPanel: ({ tradeId }: { tradeId: string }) => <div>Alerts {tradeId}</div>,
}));
vi.mock('../components/ExecutionDatesPanel', () => ({
  ExecutionDatesPanel: ({
    tradeId,
    onChanged,
    reloadToken,
    onWriteBlockedChange,
  }: {
    tradeId: string;
    onChanged: () => Promise<void>;
    reloadToken: number;
    onWriteBlockedChange: (blocked: boolean) => void;
  }) => {
    const [readbacks, setReadbacks] = useState<string[]>([]);
    return (
      <div>
        Dates {tradeId}
        <button
          onClick={() => {
            void onChanged().then(
              () => setReadbacks((previous) => [...previous, 'Booking read succeeded']),
              (error: unknown) =>
                setReadbacks((previous) => [
                  ...previous,
                  `Booking read failed: ${error instanceof Error ? error.message : 'Unknown'}`,
                ]),
            );
          }}
        >
          Booking refresh
        </button>
        <button onClick={() => onWriteBlockedChange(true)}>Booking write begins</button>
        <button onClick={() => onWriteBlockedChange(false)}>Booking checked</button>
        <output aria-label="Booking reload">{reloadToken}</output>
        {readbacks.map((result, index) => (
          <p key={index}>{result}</p>
        ))}
      </div>
    );
  },
}));
vi.mock('../components/AdditionalPurchasePanel', () => ({
  AdditionalPurchasePanel: ({ tradeId }: { tradeId: string }) => {
    const pending = useRef(false);
    const { notify } = useTradePendingChanges('additional-purchase-test', {
      isBusy: () => pending.current,
      isDirty: () => false,
      onDiscard: () => undefined,
    });
    return (
      <div>
        Additional {tradeId}
        <button
          onClick={() => {
            pending.current = true;
            notify();
          }}
        >
          Additional write begins
        </button>
        <button
          onClick={() => {
            pending.current = false;
            notify();
          }}
        >
          Additional write ends
        </button>
      </div>
    );
  },
}));
vi.mock('../components/TradeCancellationPanel', () => ({
  TradeCancellationPanel: ({ trade }: { trade: TradeResponse }) => (
    <div>Cancellation {trade.id}</div>
  ),
}));
vi.mock('../components/TradeTimelinePanel', () => ({
  TradeTimelinePanel: ({ tradeId }: { tradeId: string }) => <div>Timeline {tradeId}</div>,
}));
vi.mock('../../post_trade/services/client', () => ({
  postTradeApiClient: { startObservation: vi.fn() },
}));
vi.mock('../../product/services/client', () => ({ warrantApiClient: { get: vi.fn() } }));
vi.mock('../services/client', () => ({
  tradeManagementApiClient: {
    trade: vi.fn(),
    position: vi.fn(),
    managementState: vi.fn(),
    sell: vi.fn(),
    changeStop: vi.fn(),
    changeTarget: vi.fn(),
    updateThesis: vi.fn(),
    addNote: vi.fn(),
  },
}));

const api = vi.mocked(tradeManagementApiClient);
const warrantApi = vi.mocked(warrantApiClient);
const postTradeApi = vi.mocked(postTradeApiClient);

function fixture(id: string) {
  const trade: TradeResponse = {
    id,
    product_id: `product-${id}`,
    origin: 'EXTERNAL',
    trade_plan_id: null,
    trade_plan_version_id: null,
    product_selection_id: null,
    product_evaluation_id: null,
    created_at: '2026-08-17T08:00:00Z',
  };
  const warrant: WarrantResponse = {
    id: trade.product_id,
    workspace_id: 'workspace',
    issuer_id: 'issuer',
    underlying_id: 'shared-underlying',
    product_family: 'WARRANT',
    display_name: `Synthetic warrant ${id}`,
    isin: null,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    version: 1,
    created_at: trade.created_at,
    updated_at: trade.created_at,
  };
  const position: PositionResponse = {
    id: `position-${id}`,
    trade_id: id,
    product_id: trade.product_id,
    open_quantity: id === 'trade-a' ? 10 : 20,
    cost_basis: '20.00',
    average_entry_price: '2.00',
    realized_gross_pnl: '0',
    opened_at: trade.created_at,
    last_execution_at: trade.created_at,
    closed_at: null,
    is_closed: false,
  };
  const management: TradeManagementStateResponse = {
    trade_id: id,
    stop_price: '1.80',
    target_price: '2.80',
    stop_price_binding: { basis: 'WARRANT', instrument_id: trade.product_id, currency: 'EUR' },
    target_price_binding: { basis: 'WARRANT', instrument_id: trade.product_id, currency: 'EUR' },
    thesis: `Thesis ${id}`,
    notes: [],
    last_event_at: trade.created_at,
  };
  return { trade, warrant, position, management };
}
const a = fixture('trade-a');
const b = fixture('trade-b');

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <nav>
      <button onClick={() => void navigate('/trade-management?trade_id=trade-b')}>Go B</button>
      <button onClick={() => void navigate('/trade-management')}>Clear context</button>
      <button onClick={() => void navigate(`${location.pathname}${location.search}#sale-capture`)}>
        Sale anchor
      </button>
      <button onClick={() => void navigate(-1)}>Back</button>
      <button onClick={() => void navigate(1)}>Forward</button>
      <output aria-label="Current location">
        {location.pathname}
        {location.search}
        {location.hash}
      </output>
    </nav>
  );
}

function openPage() {
  return render(
    <MemoryRouter initialEntries={['/trade-management?trade_id=trade-a']}>
      <Navigation />
      <TradeManagementPage />
    </MemoryRouter>,
  );
}
function openGuardedPage() {
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <>
            <Navigation />
            <TradeManagementPage />
          </>
        ),
      },
    ],
    {
      initialEntries: ['/trade-management?trade_id=trade-b', '/trade-management?trade_id=trade-a'],
      initialIndex: 1,
    },
  );
  render(<RouterProvider router={router} />);
  return router;
}
async function loaded(id: string) {
  await screen.findByRole('heading', { name: new RegExp(`Synthetic warrant ${id}`) });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled());
}
function lookup(id: string) {
  fireEvent.change(screen.getByLabelText('Trade-ID'), { target: { value: id } });
  fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
}
function saleDraft(quantity = '3', price = '2.50') {
  fireEvent.change(screen.getByLabelText('Verkaufsmenge'), { target: { value: quantity } });
  fireEvent.change(screen.getByLabelText('Verkaufspreis'), { target: { value: price } });
}
function expectNoWrites() {
  for (const method of ['sell', 'changeStop', 'changeTarget', 'updateThesis', 'addNote'] as const) {
    expect(api[method]).not.toHaveBeenCalled();
  }
  expect(postTradeApi.startObservation).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  api.trade.mockImplementation((id) => Promise.resolve(fixture(id).trade));
  api.position.mockImplementation((id) => Promise.resolve(fixture(id).position));
  api.managementState.mockImplementation((id) => Promise.resolve(fixture(id).management));
  warrantApi.get.mockImplementation((id) =>
    Promise.resolve(fixture(id.replace('product-', '')).warrant),
  );
  api.sell.mockResolvedValue({} as SaleResponse);
});

describe('Trade Management transaction context', () => {
  it.each(['trade', 'position', 'managementState', 'warrant'] as const)(
    'does not expose A actions for B when the %s read fails',
    async (stage) => {
      openPage();
      await loaded(a.trade.id);
      saleDraft();
      if (stage === 'warrant') warrantApi.get.mockRejectedValueOnce(new Error('B unavailable'));
      else api[stage].mockRejectedValueOnce(new Error('B unavailable'));
      lookup(b.trade.id);
      await screen.findByText('B unavailable');
      // On the old implementation the still-visible A form submits to B.
      const staleButton = screen.queryByRole('button', { name: 'Teilverkauf erfassen' });
      if (staleButton)
        await act(() => {
          fireEvent.click(staleButton);
          return Promise.resolve();
        });
      expectNoWrites();
      expect(screen.queryByText(/Synthetic warrant trade-a/)).not.toBeInTheDocument();
      expect(screen.queryByRole('form', { name: 'Verkauf erfassen' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop speichern' })).not.toBeInTheDocument();
      expect(screen.queryByText('Additional trade-b')).not.toBeInTheDocument();
    },
  );

  it('removes A data immediately while B is loading, before the result is known', async () => {
    const pending = deferred<TradeResponse>();
    openPage();
    await loaded(a.trade.id);
    api.trade.mockReturnValueOnce(pending.promise);
    lookup(b.trade.id);
    expect(screen.queryByText(/Synthetic warrant trade-a/)).not.toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Verkauf erfassen' })).not.toBeInTheDocument();
    expect(screen.queryByText('Dates trade-a')).not.toBeInTheDocument();
    await act(() => {
      pending.resolve(b.trade);
      return Promise.resolve();
    });
    await loaded(b.trade.id);
    expectNoWrites();
  });

  it('resets sale and management drafts on a successful trade change', async () => {
    openPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
    fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
      target: { value: 'USD' },
    });
    fireEvent.change(screen.getByLabelText('Verkaufsdatum'), { target: { value: '2026-08-20' } });
    fireEvent.change(screen.getByLabelText('Neue Management-Notiz'), {
      target: { value: 'Only for A' },
    });
    lookup(b.trade.id);
    await loaded(b.trade.id);
    expect(screen.getByLabelText('Verkaufsmenge')).toHaveValue(null);
    expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(null);
    expect(screen.getByLabelText('Verkaufsdatum')).toHaveValue(localToday());
    expect(screen.getByLabelText('Neue Management-Notiz')).toHaveValue('');
    expect(screen.getByLabelText('Aktuelle These')).toHaveValue('Thesis trade-b');
    expect(screen.getByText('Dates trade-b')).toBeInTheDocument();
    expect(screen.getByText('Additional trade-b')).toBeInTheDocument();
    expectNoWrites();
    saleDraft('2', '3.25');
    fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
    await waitFor(() =>
      expect(api.sell).toHaveBeenCalledWith(
        'trade-b',
        expect.objectContaining({
          quantity: 2,
          price_per_unit: '3.25',
          request_id: expect.any(String),
        }),
      ),
    );
    expect(api.sell.mock.calls[0][1]).not.toHaveProperty('currency_confirmation');
  });

  it('uses the URL for SPA navigation and browser back/forward', async () => {
    openPage();
    await loaded(a.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    expect(screen.getByLabelText('Trade-ID')).toHaveValue('trade-b');
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await loaded(a.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }));
    await loaded(b.trade.id);
    expectNoWrites();
  });

  it('does not show an old position after the URL loses its trade context', async () => {
    openPage();
    await loaded(a.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Clear context' }));
    expect(screen.getByLabelText('Trade-ID')).toHaveValue('');
    expect(screen.queryByRole('form', { name: 'Verkauf erfassen' })).not.toBeInTheDocument();
    expect(screen.queryByText('Dates trade-a')).not.toBeInTheDocument();
    expectNoWrites();
  });

  it('ignores a late old product read even when its transport ignores cancellation', async () => {
    const oldProduct = deferred<WarrantResponse>();
    warrantApi.get.mockImplementation(async (id) =>
      id === a.warrant.id ? oldProduct.promise : b.warrant,
    );
    openPage();
    await waitFor(() =>
      expect(warrantApi.get).toHaveBeenCalledWith(a.warrant.id, expect.any(AbortSignal)),
    );
    const oldSignal = warrantApi.get.mock.calls[0][1]!;
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    await act(() => {
      oldProduct.resolve(a.warrant);
      return Promise.resolve();
    });
    expect(oldSignal.aborted).toBe(true);
    expect(screen.getByRole('heading', { name: /Synthetic warrant trade-b/ })).toBeInTheDocument();
    expect(screen.queryByText(/Synthetic warrant trade-a/)).not.toBeInTheDocument();
    expectNoWrites();
  });

  it('can retry the same failed lookup without booking anything', async () => {
    openPage();
    await loaded(a.trade.id);
    api.position.mockRejectedValueOnce(new Error('Temporary read failure'));
    lookup(b.trade.id);
    await screen.findByText('Temporary read failure');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
    await loaded(b.trade.id);
    expectNoWrites();
  });

  it('preserves the draft for same-trade hash navigation', async () => {
    openPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.click(screen.getByRole('button', { name: 'Sale anchor' }));
    expect(screen.getByLabelText('Verkaufsmenge')).toHaveValue(3);
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);
    expect(api.trade).toHaveBeenCalledTimes(1);
    expectNoWrites();
  });

  it.each(['resolve', 'reject'] as const)(
    'keeps a pending A sale isolated when it later %ss after navigation to B',
    async (outcome) => {
      const sale = deferred<SaleResponse>();
      api.sell.mockReturnValueOnce(sale.promise);
      openPage();
      await loaded(a.trade.id);
      saleDraft();
      fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
      await waitFor(() => expect(api.sell).toHaveBeenCalledTimes(1));
      fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
      await loaded(b.trade.id);
      saleDraft('2', '3.25');
      await act(() => {
        if (outcome === 'resolve') sale.resolve({} as SaleResponse);
        else sale.reject(new Error('Old A error'));
        return Promise.resolve();
      });
      expect(
        screen.getByRole('heading', { name: /Synthetic warrant trade-b/ }),
      ).toBeInTheDocument();
      expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(3.25);
      expect(screen.queryByText('Old A error')).not.toBeInTheDocument();
      expect(screen.queryByText(/Teilverkauf wurde erfasst/)).not.toBeInTheDocument();
      expect(api.sell).toHaveBeenCalledTimes(1);
      expect(api.sell.mock.calls[0][0]).toBe(a.trade.id);
    },
  );

  it('keeps the new A retry key when a detached older A sale succeeds late', async () => {
    const oldSale = deferred<SaleResponse>();
    const newSale = deferred<SaleResponse>();
    api.sell.mockReturnValueOnce(oldSale.promise).mockReturnValueOnce(newSale.promise);
    // This isolation harness intentionally permits forced detachment while a write
    // is pending; the data-router cases separately verify normal navigation blocks.
    openPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
    await waitFor(() => expect(api.sell).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await loaded(a.trade.id);
    saleDraft('2', '3.25');
    fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
    await waitFor(() => expect(api.sell).toHaveBeenCalledTimes(2));
    const currentKey = api.sell.mock.calls[1][1].request_id;
    expect(currentKey).not.toBe(api.sell.mock.calls[0][1].request_id);
    await act(() => {
      oldSale.resolve({} as SaleResponse);
      newSale.reject(new Error('New A response lost'));
      return Promise.resolve();
    });
    await screen.findByText('New A response lost');
    fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));
    await waitFor(() => expect(api.sell).toHaveBeenCalledTimes(3));
    expect(api.sell.mock.calls[2][1].request_id).toBe(currentKey);
  });

  it('saves a management change only for the loaded B instrument binding', async () => {
    api.changeStop.mockResolvedValue({} as never);
    openPage();
    await loaded(a.trade.id);
    fireEvent.change(screen.getByLabelText('Stop'), { target: { value: '1.95' } });
    lookup(b.trade.id);
    await loaded(b.trade.id);
    expect(screen.getByLabelText('Stop')).toHaveValue(1.8);
    fireEvent.change(screen.getByLabelText('Stop'), { target: { value: '1.90' } });
    fireEvent.click(screen.getByRole('button', { name: 'Stop speichern' }));
    await screen.findByText('Stop wurde aktualisiert.');
    expect(api.changeStop).toHaveBeenCalledWith(b.trade.id, {
      price: '1.90',
      price_binding: b.management.stop_price_binding,
    });
    expect(api.sell).not.toHaveBeenCalled();
  });

  it('retains cancellation protections after selecting a cancelled trade', async () => {
    api.trade.mockImplementation((id) =>
      Promise.resolve({
        ...fixture(id).trade,
        cancelled_at: id === b.trade.id ? '2026-08-18T09:00:00Z' : null,
      }),
    );
    openPage();
    await loaded(a.trade.id);
    saleDraft();
    lookup(b.trade.id);
    await loaded(b.trade.id);
    expect(screen.getByRole('heading', { name: 'CANCELLED' })).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Verkauf erfassen' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Stop speichern' })).not.toBeInTheDocument();
    expect(screen.queryByText('Additional trade-b')).not.toBeInTheDocument();
    expect(screen.getByText('Dates trade-b')).toBeInTheDocument();
    expectNoWrites();
  });

  it('does not redirect B when a previously requested post-trade observation for A completes', async () => {
    const observation = deferred<Awaited<ReturnType<typeof postTradeApi.startObservation>>>();
    postTradeApi.startObservation.mockReturnValueOnce(observation.promise);
    api.position.mockImplementation((id) =>
      Promise.resolve({
        ...fixture(id).position,
        is_closed: id === a.trade.id,
        open_quantity: id === a.trade.id ? 0 : 20,
      }),
    );
    openPage();
    await loaded(a.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Nachbeobachtung starten' }));
    await waitFor(() => expect(postTradeApi.startObservation).toHaveBeenCalledWith(a.trade.id));
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    await act(() => {
      observation.resolve({} as never);
      return Promise.resolve();
    });
    expect(screen.getByLabelText('Current location')).toHaveTextContent(
      '/trade-management?trade_id=trade-b',
    );
    expect(screen.getByRole('heading', { name: /Synthetic warrant trade-b/ })).toBeInTheDocument();
  });

  it('preserves parallel management and sale drafts when bookings refresh the backend projection', async () => {
    openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.change(screen.getByLabelText('Stop'), { target: { value: '1.95' } });
    fireEvent.change(screen.getByLabelText('Instrument für Stop'), {
      target: { value: 'UNDERLYING' },
    });
    fireEvent.change(screen.getByLabelText('Währung für Stop'), { target: { value: 'USD' } });
    fireEvent.change(screen.getByLabelText('Aktuelle These'), {
      target: { value: 'Prepared thesis' },
    });
    fireEvent.change(screen.getByLabelText('Neue Management-Notiz'), {
      target: { value: 'Prepared note' },
    });
    api.managementState.mockResolvedValueOnce({
      ...a.management,
      stop_price: '1.70',
      target_price: '3.10',
      target_price_binding: {
        basis: 'UNDERLYING',
        instrument_id: a.warrant.underlying_id,
        currency: 'CHF',
      },
      thesis: 'Fresh backend thesis',
    });
    api.position.mockResolvedValueOnce({ ...a.position, open_quantity: 7 });
    fireEvent.click(screen.getByRole('button', { name: 'Booking refresh' }));
    await waitFor(() => expect(screen.getByLabelText('Target')).toHaveValue(3.1));
    expect(screen.getByLabelText('Instrument für Target')).toHaveValue('UNDERLYING');
    expect(screen.getByLabelText('Währung für Target')).toHaveValue('CHF');
    expect(screen.getByLabelText('Stop')).toHaveValue(1.95);
    expect(screen.getByLabelText('Instrument für Stop')).toHaveValue('UNDERLYING');
    expect(screen.getByLabelText('Währung für Stop')).toHaveValue('USD');
    expect(screen.getByLabelText('Aktuelle These')).toHaveValue('Prepared thesis');
    expect(screen.getByLabelText('Neue Management-Notiz')).toHaveValue('Prepared note');
    expect(screen.getByLabelText('Verkaufsmenge')).toHaveValue(3);
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);
    expect(
      within(screen.getByRole('region', { name: 'Trade und Position' })).getByText('7'),
    ).toBeInTheDocument();
    expectNoWrites();
  });

  it('reloads the same trade without remounting drafts or replacing the booking editor', async () => {
    openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.change(screen.getByLabelText('Target'), { target: { value: '3.25' } });
    fireEvent.change(screen.getByLabelText('Instrument für Target'), {
      target: { value: 'UNDERLYING' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
    await waitFor(() => expect(api.position).toHaveBeenCalledTimes(2));
    await loaded(a.trade.id);
    expect(screen.getByLabelText('Booking reload')).toHaveTextContent('1');
    expect(screen.getByLabelText('Verkaufsmenge')).toHaveValue(3);
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);
    expect(screen.getByLabelText('Target')).toHaveValue(3.25);
    expect(screen.getByLabelText('Instrument für Target')).toHaveValue('UNDERLYING');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expectNoWrites();
  });

  it('keeps the most recent same-trade projection when an older refresh finishes last', async () => {
    const oldPosition = deferred<PositionResponse>();
    openGuardedPage();
    await loaded(a.trade.id);
    api.position
      .mockReturnValueOnce(oldPosition.promise)
      .mockResolvedValueOnce({ ...a.position, open_quantity: 7 });
    fireEvent.click(screen.getByRole('button', { name: 'Booking refresh' }));
    fireEvent.click(screen.getByRole('button', { name: 'Booking refresh' }));
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    await overview.findByText('7');
    await act(() => {
      oldPosition.resolve({ ...a.position, open_quantity: 99 });
      return Promise.resolve();
    });
    expect(overview.getByText('7')).toBeInTheDocument();
    expect(overview.queryByText('99')).not.toBeInTheDocument();
  });

  it('does not acknowledge a superseded booking readback when the newer projection read fails', async () => {
    const older = deferred<PositionResponse>();
    const newer = deferred<PositionResponse>();
    openGuardedPage();
    await loaded(a.trade.id);
    api.position.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.click(screen.getByRole('button', { name: 'Booking refresh' }));
    fireEvent.click(screen.getByRole('button', { name: 'Booking refresh' }));
    await act(() => {
      newer.reject(new Error('Current projection unavailable'));
      return Promise.resolve();
    });
    await screen.findByText('Booking read failed: Current projection unavailable');
    await act(() => {
      older.resolve({ ...a.position, open_quantity: 99 });
      return Promise.resolve();
    });
    await screen.findByText(/Booking read failed: Ein neuerer Trade-Leseversuch/);
    expect(screen.queryByText('Booking read succeeded')).not.toBeInTheDocument();
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getByText('10')).toBeInTheDocument();
    expect(overview.queryByText('99')).not.toBeInTheDocument();
  });

  it('guards lookup, query and browser navigation with one page guard and keeps hash drafts', async () => {
    const router = openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    lookup(b.trade.id);
    const dialog = await screen.findByRole('alertdialog');
    expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
    expect(within(dialog).getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);

    await act(() =>
      router.navigate('/trade-management?trade_id=trade-a&view=sources&review_id=exact-review'),
    );
    await screen.findByRole('alertdialog');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    fireEvent.click(screen.getByRole('button', { name: 'Sale anchor' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(2.5);
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await screen.findByRole('alertdialog');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await screen.findByRole('alertdialog');
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await loaded(b.trade.id);
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(null);
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await loaded(a.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }));
    await loaded(b.trade.id);
    expectNoWrites();
  });

  it('blocks discard navigation and duplicate submits while the page write is pending', async () => {
    const sale = deferred<SaleResponse>();
    api.sell.mockReturnValueOnce(sale.promise);
    openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    const form = screen.getByRole('form', { name: 'Verkauf erfassen' });
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(api.sell).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Verkaufspreis')).toBeDisabled();
    expect(screen.getByLabelText('Verkaufsdatum')).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('heading', { name: 'Speicherung läuft' })).toBeInTheDocument();
    expect(
      within(dialog).queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
    ).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
    await act(() => {
      sale.resolve({} as SaleResponse);
      return Promise.resolve();
    });
    await screen.findByText('Teilverkauf wurde erfasst und die Position neu projiziert.');
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('prevents page writes until an uncertain booking result has been consciously checked', async () => {
    openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.click(screen.getByRole('button', { name: 'Booking write begins' }));
    expect(screen.getByRole('button', { name: 'Teilverkauf erfassen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Position vollständig schließen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Stop speichern' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled();
    fireEvent.submit(screen.getByRole('form', { name: 'Verkauf erfassen' }));
    expectNoWrites();
    fireEvent.click(screen.getByRole('button', { name: 'Booking checked' }));
    expect(screen.getByRole('button', { name: 'Teilverkauf erfassen' })).toBeEnabled();
  });

  it('reads another page participant lock synchronously before sale or management writes', async () => {
    openGuardedPage();
    await loaded(a.trade.id);
    saleDraft();
    fireEvent.click(screen.getByRole('button', { name: 'Additional write begins' }));
    expect(screen.getByRole('button', { name: 'Teilverkauf erfassen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Stop speichern' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Laden' })).toBeDisabled();
    fireEvent.submit(screen.getByRole('form', { name: 'Verkauf erfassen' }));
    fireEvent.submit(screen.getByRole('button', { name: 'Stop speichern' }).closest('form')!);
    expectNoWrites();
    fireEvent.click(screen.getByRole('button', { name: 'Additional write ends' }));
    expect(screen.getByRole('button', { name: 'Teilverkauf erfassen' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Laden' })).toBeEnabled();
  });

  it('ignores the first A read after a complete A to B to A round trip', async () => {
    const firstA = deferred<TradeResponse>();
    api.trade.mockReturnValueOnce(firstA.promise);
    openGuardedPage();
    await waitFor(() =>
      expect(api.trade).toHaveBeenCalledWith(a.trade.id, expect.any(AbortSignal)),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Go B' }));
    await loaded(b.trade.id);
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await loaded(a.trade.id);
    saleDraft('2', '3.75');
    await act(() => {
      firstA.resolve({ ...a.trade, product_id: 'obsolete-product-a' });
      return Promise.resolve();
    });
    expect(screen.getByRole('heading', { name: /Synthetic warrant trade-a/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Verkaufspreis')).toHaveValue(3.75);
    expect(warrantApi.get).not.toHaveBeenCalledWith('obsolete-product-a', expect.anything());
    expectNoWrites();
  });
});
