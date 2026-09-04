import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../../post_trade/services/client';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../services/client';
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
    expect(screen.getByRole('heading', { name: /TR-TRADE-1 · DAX Call 19000/ })).toBeInTheDocument();
    expect(screen.getByText(/ISIN DE000TEST123 · WKN TEST12/)).toBeInTheDocument();
    expect(screen.getByText('Workspace-Produktauswahl')).toBeInTheDocument();
    expect(screen.getByText('TP-PLAN-123')).toBeInTheDocument();
    expect(screen.getByText('Alerts prüfen und Stop/Target aktiv managen')).toBeInTheDocument();
    expect(screen.getByText('10 offen')).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole('button', { name: 'SELL speichern' }));

    await waitFor(() =>
      expect(api.sell).toHaveBeenCalledWith('trade-1', {
        quantity: 4,
        price_per_unit: '2.50',
      }),
    );
    await waitFor(() => expect(api.position).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('status')).toHaveTextContent(
      'Verkauf wurde erfasst und die Position neu projiziert.',
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
        'Die Position ist geschlossen. Weitere SELL-Executions sind nicht verfügbar.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'SELL speichern' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nachbeobachtung starten' })).toBeInTheDocument();
  });

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
});
