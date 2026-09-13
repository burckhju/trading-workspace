import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import type { CancellationPreview, TradeResponse } from '../types/api';
import { TradeCancellationPanel } from './TradeCancellationPanel';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: { cancellationPreview: vi.fn(), cancel: vi.fn() },
}));
const trade: TradeResponse = {
  id: 'duplicate',
  product_id: 'warrant',
  origin: 'EXTERNAL',
  created_at: '2026-08-17T08:00:00Z',
  trade_plan_id: null,
  trade_plan_version_id: null,
  product_selection_id: null,
  product_evaluation_id: null,
};
const preview: CancellationPreview = {
  created_at: trade.created_at,
  opened_at: '2026-08-16T22:00:00Z',
  trade_id: 'duplicate',
  product_id: 'warrant',
  state_token: 'a'.repeat(64),
  can_cancel: true,
  blockers: [],
  other_open_trade_ids: ['keep'],
  cancelled_at: null,
  reason: null,
  duplicate_of_trade_id: null,
  open_quantity: 3500,
  cost_basis: '1925',
  executions: [
    {
      id: 'buy',
      side: 'BUY',
      quantity: 3500,
      price_per_unit: '0.55',
      executed_at: '2026-08-16T22:00:00Z',
      executed_on: '2026-08-17',
      execution_timezone: 'Europe/Berlin',
      recorded_at: '2026-08-18T10:00:00Z',
    },
  ],
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(tradeManagementApiClient.cancellationPreview).mockResolvedValue(preview);
  vi.mocked(tradeManagementApiClient.cancel).mockResolvedValue({
    ...preview,
    cancelled_at: '2026-09-12T10:00:00Z',
  });
});

describe('explicit cancellation, not a sale', () => {
  it('requires preview, reason and a target-specific confirmation', async () => {
    const changed = vi.fn().mockResolvedValue(undefined);
    render(<TradeCancellationPanel trade={trade} productName="E7S" onChanged={changed} />);
    expect(tradeManagementApiClient.cancellationPreview).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    const commit = await screen.findByRole('button', {
      name: 'Fehleingabe verbindlich stornieren',
    });
    expect(commit).toBeDisabled();
    expect(screen.getByText(/Uhrzeit unbekannt/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('Stornogrund'), {
      target: { value: 'versehentlich doppelt erfasst' },
    });
    fireEvent.change(screen.getByLabelText('Beizubehaltender Trade'), {
      target: { value: 'keep' },
    });
    expect(commit).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(commit);
    await waitFor(() => expect(changed).toHaveBeenCalledOnce());
    expect(tradeManagementApiClient.cancel).toHaveBeenCalledWith('duplicate', {
      expected_product_id: 'warrant',
      expected_state_token: 'a'.repeat(64),
      reason: 'versehentlich doppelt erfasst',
      duplicate_of_trade_id: 'keep',
      confirmed: true,
    });
    expect(await screen.findByText(/Fehleingabe storniert. Kein Verkauf/)).toBeVisible();
  });
  it('does not mutate on dismiss or when dependencies block cancellation', async () => {
    vi.mocked(tradeManagementApiClient.cancellationPreview).mockResolvedValue({
      ...preview,
      can_cancel: false,
      blockers: ['Verkauf vorhanden'],
    });
    render(<TradeCancellationPanel trade={trade} productName="E7S" onChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Verkauf vorhanden');
    expect(screen.queryByRole('button', { name: 'Fehleingabe verbindlich stornieren' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(tradeManagementApiClient.cancel).not.toHaveBeenCalled();
  });
  it('invalidates stale confirmation after a failure', async () => {
    vi.mocked(tradeManagementApiClient.cancel).mockRejectedValue(new Error('Vorschau veraltet'));
    render(<TradeCancellationPanel trade={trade} productName="E7S" onChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    await screen.findByLabelText('Stornogrund');
    fireEvent.change(screen.getByLabelText('Stornogrund'), { target: { value: 'duplicate' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' }));
    expect(await screen.findByText('Vorschau veraltet')).toBeVisible();
    expect(screen.queryByRole('checkbox')).toBeNull();
  });
  it('shows an already cancelled trade without another write action', () => {
    render(
      <TradeCancellationPanel
        trade={{ ...trade, cancelled_at: '2026-08-18T10:00:00Z', cancellation_reason: 'duplicate' }}
        productName="E7S"
        onChanged={vi.fn()}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('STORNIERT');
    expect(screen.queryByRole('button')).toBeNull();
  });
});
