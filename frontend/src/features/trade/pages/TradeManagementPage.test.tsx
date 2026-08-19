import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../../post_trade/services/client';
import { tradeManagementApiClient } from '../services/client';
import { TradeManagementPage } from './TradeManagementPage';

vi.mock('../../post_trade/services/client', () => ({
  postTradeApiClient: {
    startObservation: vi.fn(),
  },
}));

vi.mock('../services/client', () => ({
  tradeManagementApiClient: {
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
const postTradeApi = vi.mocked(postTradeApiClient);

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
    api.position.mockResolvedValue(position);
    api.managementState.mockResolvedValue(management);
    api.sell.mockResolvedValue({} as never);
    api.changeStop.mockResolvedValue({} as never);
    api.changeTarget.mockResolvedValue({} as never);
    api.updateThesis.mockResolvedValue({} as never);
    api.addNote.mockResolvedValue({} as never);
    postTradeApi.startObservation.mockResolvedValue({} as never);
  });

  it('loads position and current management state from a trade_id query parameter', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-management?trade_id=trade-1']}>
        <TradeManagementPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'OPEN' })).toBeInTheDocument();
    expect(screen.getByText('10 offen')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1.80')).toBeInTheDocument();
    expect(screen.getByDisplayValue('2.80')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Trend intact')).toBeInTheDocument();
    expect(screen.getByText('Initial note')).toBeInTheDocument();

    expect(api.position).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
    expect(api.managementState).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
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
