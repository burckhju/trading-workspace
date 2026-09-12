import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { tradeManagementApiClient } from '../services/client';
import { localToday } from '../services/capture';
import { AdditionalPurchasePanel } from './AdditionalPurchasePanel';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: { purchaseAdditional: vi.fn() },
}));
beforeEach(() => vi.resetAllMocks());
it('defaults to today, preserves backdated inputs and reuses key after failed response', async () => {
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockRejectedValue(
    new Error('Antwort verloren'),
  );
  render(
    <AdditionalPurchasePanel tradeId="existing" onChanged={vi.fn().mockResolvedValue(undefined)} />,
  );
  expect(screen.getByLabelText('Nachkaufdatum')).toHaveValue(localToday());
  fireEvent.change(screen.getByLabelText('Nachkaufdatum'), { target: { value: '2026-08-18' } });
  fireEvent.change(screen.getByLabelText('Nachkaufmenge'), { target: { value: '5' } });
  fireEvent.change(screen.getByLabelText('Nachkaufpreis'), { target: { value: '0.5' } });
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await screen.findByText('Antwort verloren');
  const first = vi.mocked(tradeManagementApiClient.purchaseAdditional).mock.calls[0];
  expect(first).toEqual([
    'existing',
    {
      quantity: 5,
      price_per_unit: '0.5',
      executed_on: '2026-08-18',
      execution_timezone: expect.any(String),
      request_id: expect.any(String),
    },
  ]);
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(5);
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await waitFor(() => expect(tradeManagementApiClient.purchaseAdditional).toHaveBeenCalledTimes(2));
  expect(vi.mocked(tradeManagementApiClient.purchaseAdditional).mock.calls[1]).toEqual(first);
});
