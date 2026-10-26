import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../../post_trade/services/client';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../services/client';
import { localToday } from '../services/capture';

import { TradeManagementPage } from './TradeManagementPage';

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
    timeline: vi.fn(),
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

describe('TradeManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.timeline.mockResolvedValue([]);
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
      expect(form.getByText(/Die Währung wird aus den vorherigen Käufen übernommen/)).toBeVisible();
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
});
