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
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
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

it('allows a deliberately opened currency exception and confirms it with the additional BUY', async () => {
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockResolvedValue({} as never);
  render(
    <AdditionalPurchasePanel
      tradeId="with-currency"
      onChanged={vi.fn().mockResolvedValue(undefined)}
    />,
  );
  fireEvent.change(screen.getByLabelText('Nachkaufmenge'), { target: { value: '5' } });
  fireEvent.change(screen.getByLabelText('Nachkaufpreis'), { target: { value: '0.5000000001' } });
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'USD' },
  });
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await screen.findByText('Nachkauf beim bestehenden Trade erfasst.');
  expect(tradeManagementApiClient.purchaseAdditional).toHaveBeenCalledWith(
    'with-currency',
    expect.objectContaining({
      price_per_unit: '0.5000000001',
      currency_confirmation: { currency_code: 'USD', source: 'USER_CONFIRMED', note: null },
    }),
  );
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
});

it('rejects an invalid currency exception before booking and can discard it to use the owner inheritance', async () => {
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockResolvedValue({} as never);
  render(
    <AdditionalPurchasePanel tradeId="existing" onChanged={vi.fn().mockResolvedValue(undefined)} />,
  );
  fireEvent.change(screen.getByLabelText('Nachkaufmenge'), { target: { value: '5' } });
  fireEvent.change(screen.getByLabelText('Nachkaufpreis'), { target: { value: '0.5' } });
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), { target: { value: 'EU' } });
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  expect(await screen.findByRole('status')).toHaveTextContent('dreistelligen Währungscode');
  expect(tradeManagementApiClient.purchaseAdditional).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung verwerfen' }));
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await screen.findByText('Nachkauf beim bestehenden Trade erfasst.');
  expect(
    vi.mocked(tradeManagementApiClient.purchaseAdditional).mock.calls[0][1],
  ).not.toHaveProperty('currency_confirmation');
});
