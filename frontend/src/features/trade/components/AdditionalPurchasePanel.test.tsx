import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { tradeManagementApiClient } from '../services/client';
import { localToday } from '../services/capture';
import { AdditionalPurchasePanel } from './AdditionalPurchasePanel';
import { TradePendingChangesProvider, useTradePendingChanges } from './TradePendingChanges';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: { purchaseAdditional: vi.fn(), executionCurrencyPreview: vi.fn() },
}));
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(tradeManagementApiClient.executionCurrencyPreview).mockResolvedValue({
    currency_code: 'EUR',
    source: 'PRIOR_BUYS',
    source_execution_ids: ['synthetic-buy'],
    confirmation_ids: ['synthetic-confirmation'],
  });
  sessionStorage.clear();
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}
function prepare(quantity = '5', price = '0.5') {
  fireEvent.change(screen.getByLabelText('Nachkaufmenge'), { target: { value: quantity } });
  fireEvent.change(screen.getByLabelText('Nachkaufpreis'), { target: { value: price } });
}
it('defaults to today, preserves backdated inputs and reuses key after failed response', async () => {
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockRejectedValue(
    new Error('Antwort verloren'),
  );
  render(
    <AdditionalPurchasePanel tradeId="existing" onChanged={vi.fn().mockResolvedValue(undefined)} />,
  );
  expect(screen.getByLabelText('Nachkaufdatum')).toHaveValue(localToday());
  expect(
    await screen.findByText('Vorhandene Währung: EUR · aus vorherigen Käufen übernommen'),
  ).toBeVisible();
  expect(tradeManagementApiClient.purchaseAdditional).not.toHaveBeenCalled();
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

it('guards its dirty route context and forbids discard until the actual BUY and readback finish', async () => {
  const write = deferred<Awaited<ReturnType<typeof tradeManagementApiClient.purchaseAdditional>>>();
  const read = deferred<void>();
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockReturnValue(write.promise);
  const changed = vi.fn(() => read.promise);
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: (
          <TradePendingChangesProvider>
            <AdditionalPurchasePanel tradeId="existing" onChanged={changed} />
          </TradePendingChangesProvider>
        ),
      },
      { path: '/away', element: <p>Anderer Kontext</p> },
    ],
    { initialEntries: ['/'] },
  );
  render(<RouterProvider router={router} />);
  prepare();
  await act(() => router.navigate('/away'));
  expect(screen.getByRole('alertdialog', { name: 'Ungespeicherte Änderungen' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(5);
  fireEvent.submit(screen.getByRole('form', { name: 'Nachkauf erfassen' }));
  fireEvent.submit(screen.getByRole('form', { name: 'Nachkauf erfassen' }));
  expect(tradeManagementApiClient.purchaseAdditional).toHaveBeenCalledOnce();
  await act(() => router.navigate('/away'));
  let dialog = screen.getByRole('alertdialog', { name: 'Speicherung läuft' });
  expect(within(dialog).queryByText('Eingaben verwerfen und wechseln')).not.toBeInTheDocument();
  await act(async () => {
    write.resolve({} as never);
    await write.promise;
  });
  expect(changed).toHaveBeenCalledOnce();
  dialog = screen.getByRole('alertdialog', { name: 'Speicherung läuft' });
  expect(within(dialog).queryByText('Eingaben verwerfen und wechseln')).not.toBeInTheDocument();
  await act(async () => {
    read.resolve();
    await read.promise;
  });
  fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  await act(() => router.navigate('/away'));
  expect(screen.getByText('Anderer Kontext')).toBeVisible();
  expect(tradeManagementApiClient.purchaseAdditional).toHaveBeenCalledOnce();
});

it('does not let a late first A write clear a second A capture key after A to B to A', async () => {
  const old = deferred<Awaited<ReturnType<typeof tradeManagementApiClient.purchaseAdditional>>>();
  const changed = vi.fn().mockResolvedValue(undefined);
  const api = vi.mocked(tradeManagementApiClient.purchaseAdditional);
  api.mockReturnValueOnce(old.promise).mockRejectedValue(new Error('Antwort verloren'));
  const { rerender } = render(<AdditionalPurchasePanel tradeId="A" onChanged={changed} />);
  prepare();
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  rerender(<AdditionalPurchasePanel tradeId="B" onChanged={changed} />);
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(null);
  rerender(<AdditionalPurchasePanel tradeId="A" onChanged={changed} />);
  prepare('3', '0.7');
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await screen.findByText('Antwort verloren');
  const newAttempt = api.mock.calls[1];
  await act(async () => {
    old.resolve({} as never);
    await old.promise;
  });
  expect(changed).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(3);
  expect(screen.queryByText('Nachkauf beim bestehenden Trade erfasst.')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  await waitFor(() => expect(api).toHaveBeenCalledTimes(3));
  expect(api.mock.calls[2]).toEqual(newAttempt);
});

it('reports a confirmed BUY separately from a failed projection read without resubmitting it', async () => {
  vi.mocked(tradeManagementApiClient.purchaseAdditional).mockResolvedValue({} as never);
  render(
    <AdditionalPurchasePanel
      tradeId="existing"
      onChanged={vi.fn().mockRejectedValue(new Error('Position nicht verfügbar'))}
    />,
  );
  prepare();
  fireEvent.click(screen.getByRole('button', { name: 'Nachkauf speichern' }));
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Nachkauf gespeichert, Ansicht noch nicht aktualisiert',
  );
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(null);
  fireEvent.submit(screen.getByRole('form', { name: 'Nachkauf erfassen' }));
  expect(tradeManagementApiClient.purchaseAdditional).toHaveBeenCalledOnce();
});

it('consults another participant lock before a BUY even without another render', () => {
  let otherWrite = false;
  function OtherWrite() {
    useTradePendingChanges('other', {
      isBusy: () => otherWrite,
      isDirty: () => false,
      onDiscard: () => undefined,
    });
    return null;
  }
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <TradePendingChangesProvider>
          <OtherWrite />
          <AdditionalPurchasePanel tradeId="existing" onChanged={vi.fn()} />
        </TradePendingChangesProvider>
      ),
    },
  ]);
  render(<RouterProvider router={router} />);
  prepare();
  otherWrite = true;
  fireEvent.submit(screen.getByRole('form', { name: 'Nachkauf erfassen' }));
  expect(tradeManagementApiClient.purchaseAdditional).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(5);
});

it('checks a booking recovery lock before posting even if the fieldset has not rerendered', () => {
  let bookingNeedsReview = false;
  render(
    <AdditionalPurchasePanel
      tradeId="existing"
      onChanged={vi.fn()}
      isWriteBlocked={() => bookingNeedsReview}
    />,
  );
  prepare();
  bookingNeedsReview = true;
  fireEvent.submit(screen.getByRole('form', { name: 'Nachkauf erfassen' }));
  expect(tradeManagementApiClient.purchaseAdditional).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Nachkaufmenge')).toHaveValue(5);
});
