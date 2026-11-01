import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../../post_trade/services/client';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../services/client';
import { localToday } from '../services/capture';
import type { PositionResponse, TradeTimelineEntryResponse } from '../types/api';

import { TradeManagementPage } from './TradeManagementPage';

// History integration and its readback lifecycle have a dedicated page suite.
vi.mock('../../operational_workspace', () => ({ PositionPriceHistory: () => null }));

vi.mock('../../alert/components/TradeAlertsPanel', () => ({
  TradeAlertsPanel: ({ tradeId }: { tradeId: string }) => <div>Alerts for {tradeId}</div>,
}));

vi.mock('../../post_trade/services/client', () => ({
  postTradeApiClient: {
    startObservation: vi.fn(),
  },
}));

vi.mock('../../product/services/client', () => ({
  warrantApiClient: {
    get: vi.fn(),
  },
}));

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    executionCurrencyPreview: vi.fn(),
    timeline: vi.fn(),
    correctExecution: vi.fn(),
    confirmExecutionCurrency: vi.fn(),
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

const trade = {
  id: 'trade-1',
  product_id: 'product-1',
  origin: 'WORKSPACE_SELECTION' as const,
  trade_plan_id: 'plan-12345678',
  trade_plan_version_id: 'plan-version-1',
  product_selection_id: 'selection-1',
  product_evaluation_id: 'evaluation-1',
  created_at: '2026-08-17T08:00:00Z',
};

const warrant = {
  id: 'product-1',
  workspace_id: 'workspace-1',
  issuer_id: 'issuer-1',
  underlying_id: 'underlying-1',
  product_family: 'WARRANT' as const,
  display_name: 'DAX Call 19000',
  isin: 'DE000TEST123',
  wkn: 'TEST12',
  lifecycle_status: 'ACTIVE' as const,
  version: 1,
  created_at: '2026-08-16T08:00:00Z',
  updated_at: '2026-08-16T08:00:00Z',
};

const position = {
  id: 'position-1',
  trade_id: 'trade-1',
  product_id: 'product-1',
  open_quantity: 10,
  cost_basis: '20.00',
  average_entry_price: '2.00',
  realized_gross_pnl: '3.50',
  opened_at: '2026-08-17T08:00:00Z',
  last_execution_at: '2026-08-17T09:00:00Z',
  closed_at: null,
  is_closed: false,
};

const management = {
  trade_id: 'trade-1',
  stop_price: '1.80',
  target_price: '2.80',
  thesis: 'Trend intact',
  notes: ['Initial note'],
  last_event_at: '2026-08-17T09:00:00Z',
};

const buy: TradeTimelineEntryResponse = {
  id: 'buy-1',
  trade_id: trade.id,
  kind: 'EXECUTION',
  execution_side: 'BUY',
  quantity: 10,
  price_per_unit: '2.0000000000',
  occurred_at: '2026-08-17T08:00:01.123456Z',
  recorded_at: '2026-08-17T08:05:00Z',
  management_event_type: null,
  numeric_value: null,
  text_value: null,
  supersedes_id: null,
  currency_resolution: {
    source: 'USER_CONFIRMED',
    currency_code: 'EUR',
    source_execution_ids: ['buy-1'],
    confirmation_ids: ['currency-1'],
  },
};
const sell: TradeTimelineEntryResponse = {
  ...buy,
  id: 'sell-1',
  execution_side: 'SELL',
  price_per_unit: '3.0000000000',
  occurred_at: '2026-08-18T09:30:02.654321Z',
  recorded_at: '2026-08-18T09:35:00Z',
  currency_resolution: {
    ...buy.currency_resolution!,
    source: 'PRIOR_BUYS',
  },
};
const closed: PositionResponse = {
  ...position,
  open_quantity: 0,
  cost_basis: '0.0000000000',
  average_entry_price: '0.0000000000',
  realized_gross_pnl: '10.0000000000',
  last_execution_at: sell.occurred_at,
  closed_at: sell.occurred_at,
  is_closed: true,
};

function openIntegratedPage() {
  const router = createMemoryRouter(
    [
      { path: '/trade-management', element: <TradeManagementPage /> },
      { path: '/elsewhere', element: <h1>Andere Seite</h1> },
    ],
    {
      initialEntries: [
        '/elsewhere',
        '/trade-management?trade_id=trade-1',
        '/trade-management?trade_id=trade-2',
      ],
      initialIndex: 1,
    },
  );
  render(<RouterProvider router={router} />);
  return router;
}

function expectNoOtherWrites() {
  for (const method of [
    'sell',
    'changeStop',
    'changeTarget',
    'updateThesis',
    'addNote',
    'confirmExecutionCurrency',
  ] as const) {
    expect(api[method]).not.toHaveBeenCalled();
  }
  expect(postTradeApi.startObservation).not.toHaveBeenCalled();
}

describe('TradeManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.executionCurrencyPreview.mockResolvedValue({
      currency_code: 'EUR',
      source: 'PRIOR_BUYS',
      source_execution_ids: [buy.id],
      confirmation_ids: ['currency-1'],
    });
    api.timeline.mockResolvedValue([]);
    api.correctExecution.mockReset();
    api.trade.mockResolvedValue(trade);
    api.position.mockResolvedValue(position);
    api.managementState.mockResolvedValue(management);
    warrantApi.get.mockResolvedValue(warrant);
    api.sell.mockResolvedValue({} as never);
    api.changeStop.mockResolvedValue({} as never);
    api.changeTarget.mockResolvedValue({} as never);
    api.updateThesis.mockResolvedValue({} as never);
    api.addNote.mockResolvedValue({} as never);
    postTradeApi.startObservation.mockResolvedValue({} as never);
  });

  it('loads visible product, TradePlan, position and management context from a trade_id query parameter', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'OPEN' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /TR-TRADE-1 · DAX Call 19000/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/ISIN DE000TEST123 · WKN TEST12/)).toBeInTheDocument();
    expect(screen.getByText('Workspace-Produktauswahl')).toBeInTheDocument();
    expect(screen.getByText('TP-PLAN-123')).toBeInTheDocument();
    expect(screen.getByText('Alerts prüfen und Stop/Target aktiv managen')).toBeInTheDocument();
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getAllByText('OPEN')).toHaveLength(1);
    expect(overview.getAllByText('Offene Menge')).toHaveLength(1);
    expect(overview.getByText('10')).toBeInTheDocument();
    expect(overview.getByText('Cost Basis')).toBeInTheDocument();
    expect(overview.getByText('Average Entry')).toBeInTheDocument();
    expect(overview.getByText('Realized gross P&L')).toBeInTheDocument();
    expect(screen.queryByText('10 offen')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('1.80')).toBeInTheDocument();
    expect(screen.getByDisplayValue('2.80')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Trend intact')).toBeInTheDocument();
    expect(screen.getByText('Initial note')).toBeInTheDocument();
    expect(screen.getByText('Alerts for trade-1')).toBeInTheDocument();

    expect(api.trade).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
    expect(api.position).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
    expect(api.managementState).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
    expect(warrantApi.get).toHaveBeenCalledWith('product-1', expect.any(AbortSignal));
  });

  it('records a SELL and refreshes the projected position', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'OPEN' });

    fireEvent.change(screen.getByLabelText('Verkaufsmenge'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Verkaufspreis'), { target: { value: '2.50' } });
    fireEvent.click(screen.getByRole('button', { name: 'Teilverkauf erfassen' }));

    await waitFor(() =>
      expect(api.sell).toHaveBeenCalledWith('trade-1', {
        quantity: 4,
        price_per_unit: '2.50',
        executed_on: localToday(),
        execution_timezone: expect.any(String),
        request_id: expect.any(String),
      }),
    );
    await waitFor(() => expect(api.position).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('status')).toHaveTextContent(
      'Teilverkauf wurde erfasst und die Position neu projiziert.',
    );
  });

  it('disables further SELL interaction for a closed position', async () => {
    api.position.mockResolvedValue({
      ...position,
      open_quantity: 0,
      cost_basis: '0',
      closed_at: '2026-08-17T10:00:00Z',
      is_closed: true,
    });

    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'CLOSED' })).toBeInTheDocument();
    expect(screen.getAllByText('Nachbeobachtung starten')).toHaveLength(2);
    expect(
      screen.getByText(
        'Die Position ist geschlossen. Weitere Verkäufe können nicht erfasst werden.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Teilverkauf erfassen' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nachbeobachtung starten' })).toBeInTheDocument();
  });

  it('preserves a pending booking-source read when its parallel position readback finishes first', async () => {
    api.timeline.mockResolvedValue([buy]);
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );
    await screen.findByRole('article', { name: 'Buchung buy-1' });
    let finish!: (entries: TradeTimelineEntryResponse[]) => void;
    api.timeline.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Buchungsdaten neu laden' }));
    await waitFor(() => expect(warrantApi.get).toHaveBeenCalledTimes(2));
    const pendingSignal = api.timeline.mock.calls[1][1]!;
    expect(api.timeline).toHaveBeenCalledTimes(2);
    expect(pendingSignal.aborted).toBe(false);
    await act(async () => {
      finish([buy]);
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Buchungsdaten neu laden' })).toBeEnabled(),
    );
    expect(api.timeline).toHaveBeenCalledTimes(2);
    expect(pendingSignal.aborted).toBe(false);
    expect(
      screen.queryByText(/Buchungsstand noch nicht vollständig geprüft/),
    ).not.toBeInTheDocument();
    expectNoOtherWrites();
  });

  it('allows a deliberately opened currency exception for a full SELL without another affirmation', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'OPEN' });
    const form = within(screen.getByRole('form', { name: 'Verkauf erfassen' }));
    expect(form.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
    fireEvent.change(form.getByLabelText('Verkaufspreis'), { target: { value: '2.5000000001' } });
    fireEvent.click(form.getByRole('button', { name: 'Abweichende Währung angeben' }));
    fireEvent.change(form.getByLabelText('Ausführungswährung (Code)'), {
      target: { value: 'EUR' },
    });
    expect(
      form.queryByRole('checkbox', { name: /als tatsächliche Währung/ }),
    ).not.toBeInTheDocument();
    fireEvent.click(form.getByRole('button', { name: 'Position vollständig schließen' }));
    await waitFor(() =>
      expect(api.sell).toHaveBeenCalledWith(
        'trade-1',
        expect.objectContaining({
          quantity: 10,
          price_per_unit: '2.5000000001',
          currency_confirmation: { currency_code: 'EUR', source: 'USER_CONFIRMED', note: null },
        }),
      ),
    );
    await waitFor(() => expect(form.getByLabelText('Ausführungswährung (Code)')).toHaveValue(''));
  });

  it.each(['WORKSPACE_SELECTION', 'EXTERNAL'] as const)(
    'submits a normal full SELL for %s without re-entering its purchase currency',
    async (origin) => {
      api.trade.mockResolvedValue({ ...trade, origin });
      render(
        <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
          <TradeManagementPage />
        </MemoryRouter>,
      );
      await screen.findByRole('heading', { name: 'OPEN' });
      const form = within(screen.getByRole('form', { name: 'Verkauf erfassen' }));
      expect(form.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
      expect(form.queryByRole('checkbox')).not.toBeInTheDocument();
      expect(
        await form.findByText('Vorhandene Währung: EUR · aus vorherigen Käufen übernommen'),
      ).toBeVisible();
      expect(api.sell).not.toHaveBeenCalled();
      fireEvent.change(form.getByLabelText('Verkaufspreis'), { target: { value: '2.5000000001' } });
      fireEvent.click(form.getByRole('button', { name: 'Position vollständig schließen' }));
      await waitFor(() => expect(api.sell).toHaveBeenCalledOnce());
      expect(api.sell.mock.calls[0][1]).toMatchObject({
        quantity: 10,
        price_per_unit: '2.5000000001',
      });
      expect(api.sell.mock.calls[0][1]).not.toHaveProperty('currency_confirmation');
    },
  );

  it('does not show the post-trade start action for an open position', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );

    await screen.findByRole('heading', { name: 'OPEN' });

    expect(
      screen.queryByRole('button', { name: 'Nachbeobachtung starten' }),
    ).not.toBeInTheDocument();
  });

  it('starts post-trade observation for a closed trade', async () => {
    api.position.mockResolvedValue({
      ...position,
      open_quantity: 0,
      cost_basis: '0',
      closed_at: '2026-08-17T10:00:00Z',
      is_closed: true,
    });

    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );

    const button = await screen.findByRole('button', {
      name: 'Nachbeobachtung starten',
    });

    fireEvent.click(button);

    await waitFor(() => expect(postTradeApi.startObservation).toHaveBeenCalledWith('trade-1'));
  });

  it('preserves date-only precision and does not turn unavailable projection amounts into zero', async () => {
    api.position.mockResolvedValue({
      ...position,
      opened_on: '2026-08-17',
      closed_on: '2026-08-18',
      cost_basis: '',
      average_entry_price: '',
      realized_gross_pnl: '',
      closed_at: '2026-08-18T00:00:00Z',
      is_closed: true,
      open_quantity: 0,
    });
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'CLOSED' });
    const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
    expect(overview.getByText('2026-08-17 (Uhrzeit unbekannt)')).toBeInTheDocument();
    expect(overview.getByText('2026-08-18 (Uhrzeit unbekannt)')).toBeInTheDocument();
    expect(overview.getAllByText('Nicht verfügbar')).toHaveLength(3);
    expect(overview.getAllByText('0')).toHaveLength(1);
  });

  it.each([
    {
      field: 'Menge',
      value: '12',
      quantity: 12,
      price: buy.price_per_unit!,
      nextPosition: {
        ...closed,
        open_quantity: 2,
        cost_basis: '4.0000000000',
        average_entry_price: '2.0000000000',
        closed_at: null,
        is_closed: false,
      },
    },
    {
      field: 'Preis je Einheit',
      value: '2,50',
      quantity: 10,
      price: '2.5',
      nextPosition: { ...closed, realized_gross_pnl: '5.0000000000' },
    },
  ])(
    'corrects $field in the real booking editor and preserves all open management drafts on readback',
    async ({ field, value, quantity, price, nextPosition }) => {
      api.timeline.mockResolvedValue([buy, sell]);
      api.position.mockResolvedValue(closed);
      api.managementState.mockResolvedValue({
        ...management,
        stop_price_binding: { basis: 'WARRANT', instrument_id: warrant.id, currency: 'EUR' },
        target_price_binding: { basis: 'WARRANT', instrument_id: warrant.id, currency: 'EUR' },
      });
      openIntegratedPage();
      await screen.findByRole('heading', { name: 'CLOSED' });
      const booking = within(await screen.findByRole('article', { name: 'Buchung buy-1' }));
      fireEvent.click(booking.getByRole('button', { name: 'Kauf korrigieren' }));
      const form = within(screen.getByRole('form', { name: 'Buchung korrigieren' }));
      expect(form.getByLabelText('Menge')).toHaveValue('10');
      expect(form.getByLabelText('Preis je Einheit')).toHaveValue(buy.price_per_unit);

      fireEvent.change(screen.getByLabelText('Stop'), { target: { value: '105.25' } });
      fireEvent.change(screen.getByLabelText('Instrument für Stop'), {
        target: { value: 'UNDERLYING' },
      });
      fireEvent.change(screen.getByLabelText('Währung für Stop'), { target: { value: 'USD' } });
      fireEvent.change(screen.getByLabelText('Target'), { target: { value: '130.75' } });
      fireEvent.change(screen.getByLabelText('Instrument für Target'), {
        target: { value: 'UNDERLYING' },
      });
      fireEvent.change(screen.getByLabelText('Währung für Target'), { target: { value: 'GBP' } });
      fireEvent.change(screen.getByLabelText('Aktuelle These'), {
        target: { value: 'Ungespeicherte These bleibt erhalten' },
      });
      fireEvent.change(screen.getByLabelText('Neue Management-Notiz'), {
        target: { value: 'Ungespeicherte Notiz bleibt erhalten' },
      });

      const stopInput = screen.getByLabelText('Stop');
      const thesisInput = screen.getByLabelText('Aktuelle These');
      const replacement: TradeTimelineEntryResponse = {
        ...buy,
        id: 'buy-corrected',
        supersedes_id: buy.id,
        quantity,
        price_per_unit: price,
        recorded_at: '2026-08-19T10:00:00Z',
        currency_resolution: { ...buy.currency_resolution!, source: 'REPLACED_EXECUTION' },
      };
      api.correctExecution.mockImplementation(() => {
        api.timeline.mockResolvedValue([buy, sell, replacement]);
        api.position.mockResolvedValue(nextPosition);
        api.managementState.mockResolvedValue({
          ...management,
          stop_price: '1.70',
          target_price: '2.90',
          stop_price_binding: { basis: 'WARRANT', instrument_id: warrant.id, currency: 'EUR' },
          target_price_binding: { basis: 'WARRANT', instrument_id: warrant.id, currency: 'EUR' },
          thesis: 'Frisch gelesene Managementbasis',
        });
        return Promise.resolve({
          execution: {
            id: replacement.id,
            trade_id: trade.id,
            product_id: warrant.id,
            side: 'BUY',
            quantity,
            price_per_unit: price,
            gross_amount: field === 'Menge' ? '24' : '25',
            executed_at: buy.occurred_at,
            recorded_at: replacement.recorded_at,
          },
          // The visible projection must come from the fresh GET, never this receipt.
          position: closed,
        });
      });

      fireEvent.change(form.getByLabelText(field), { target: { value } });
      fireEvent.click(
        form.getByRole('checkbox', {
          name: 'Ich bestätige die geänderten Buchungsdaten dieser Buchung.',
        }),
      );
      fireEvent.click(form.getByRole('button', { name: 'Korrektur speichern' }));
      await screen.findByText(
        'Buchung korrigiert. Die ursprüngliche Buchung bleibt in der Historie erhalten.',
      );
      expect(api.correctExecution).toHaveBeenCalledExactlyOnceWith(trade.id, buy.id, {
        side: 'BUY',
        quantity,
        price_per_unit: price,
        executed_at: buy.occurred_at,
      });
      expect(api.position).toHaveBeenCalledTimes(2);
      expect(api.managementState).toHaveBeenCalledTimes(2);
      expect(screen.getAllByRole('region', { name: 'Trade und Position' })).toHaveLength(1);
      const overview = within(screen.getByRole('region', { name: 'Trade und Position' }));
      const projected = (label: string) => overview.getByText(label).nextElementSibling;
      expect(projected('Offene Menge')?.textContent).toBe(String(nextPosition.open_quantity));
      expect(projected('Cost Basis')?.textContent).toBe(nextPosition.is_closed ? '0' : '4');
      expect(projected('Average Entry')?.textContent).toBe(nextPosition.is_closed ? '0' : '2');
      expect(projected('Realized gross P&L')).toHaveTextContent(
        nextPosition.is_closed ? '5' : '10',
      );
      expect(
        overview.getByRole('heading', { name: nextPosition.is_closed ? 'CLOSED' : 'OPEN' }),
      ).toBeInTheDocument();
      if (!nextPosition.is_closed) {
        expect(
          screen.queryByRole('button', { name: 'Nachbeobachtung starten' }),
        ).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Teilverkauf erfassen' })).toBeInTheDocument();
      }
      expect(screen.getByLabelText('Stop')).toBe(stopInput);
      expect(screen.getByLabelText('Aktuelle These')).toBe(thesisInput);
      expect(stopInput).toHaveValue(105.25);
      expect(screen.getByLabelText('Instrument für Stop')).toHaveValue('UNDERLYING');
      expect(screen.getByLabelText('Währung für Stop')).toHaveValue('USD');
      expect(screen.getByLabelText('Target')).toHaveValue(130.75);
      expect(screen.getByLabelText('Instrument für Target')).toHaveValue('UNDERLYING');
      expect(screen.getByLabelText('Währung für Target')).toHaveValue('GBP');
      expect(thesisInput).toHaveValue('Ungespeicherte These bleibt erhalten');
      expect(screen.getByLabelText('Neue Management-Notiz')).toHaveValue(
        'Ungespeicherte Notiz bleibt erhalten',
      );
      expectNoOtherWrites();
    },
  );

  it.each([
    ['Menge', '12'],
    ['Preis je Einheit', '2,5000000001'],
  ])(
    'protects a changed %s through real route, query, history and unload navigation',
    async (field, value) => {
      api.timeline.mockResolvedValue([buy]);
      const router = openIntegratedPage();
      const booking = within(await screen.findByRole('article', { name: 'Buchung buy-1' }));
      fireEvent.click(booking.getByRole('button', { name: 'Kauf korrigieren' }));
      const form = within(screen.getByRole('form', { name: 'Buchung korrigieren' }));
      const input = form.getByLabelText(field);
      fireEvent.change(input, { target: { value } });

      for (const target of [
        '/trade-management?trade_id=trade-2',
        '/trade-management?trade_id=trade-1&view=sources&review_id=exact-review&review_version_id=exact-version',
        '/elsewhere',
        -1,
        1,
      ]) {
        await act(() =>
          typeof target === 'number' ? router.navigate(target) : router.navigate(target),
        );
        const dialog = await screen.findByRole('alertdialog');
        expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
        const stay = within(dialog).getByRole('button', { name: 'Hier bleiben' });
        expect(stay).toHaveFocus();
        fireEvent.click(stay);
        expect(input).toHaveValue(value);
        expect(router.state.location.pathname).toBe('/trade-management');
        expect(router.state.location.search).toBe('?trade_id=trade-1');
      }
      fireEvent.change(screen.getByLabelText('Trade-ID'), { target: { value: 'trade-2' } });
      fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
      let dialog = await screen.findByRole('alertdialog');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
      expect(input).toHaveValue(value);

      await act(() => router.navigate('/trade-management?trade_id=trade-1#sale-capture'));
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(input).toHaveValue(value);
      const unload = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(unload);
      expect(unload.defaultPrevented).toBe(true);

      fireEvent.click(form.getByRole('button', { name: 'Abbrechen' }));
      dialog = await screen.findByRole('alertdialog');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
      expect(input).toHaveValue(value);
      fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
      dialog = await screen.findByRole('alertdialog');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
      expect(input).toHaveValue(value);

      await act(() => router.navigate('/elsewhere'));
      dialog = await screen.findByRole('alertdialog');
      fireEvent.click(
        within(dialog).getByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
      );
      await screen.findByRole('heading', { name: 'Andere Seite' });
      expect(screen.queryByRole('form', { name: 'Buchung korrigieren' })).not.toBeInTheDocument();
      expect(api.correctExecution).not.toHaveBeenCalled();
      expectNoOtherWrites();
    },
  );
});
