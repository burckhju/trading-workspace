import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import type { CancellationPreview, TradeResponse } from '../types/api';
import { TradeCancellationPanel } from './TradeCancellationPanel';
import { TradePendingChangesProvider, useTradePendingChanges } from './TradePendingChanges';

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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
async function prepare() {
  fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
  await screen.findByLabelText('Stornogrund');
  fireEvent.change(screen.getByLabelText('Stornogrund'), { target: { value: 'duplicate' } });
  fireEvent.click(screen.getByRole('checkbox'));
}
function guarded(changed: () => Promise<void>) {
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <TradePendingChangesProvider>
          <TradeCancellationPanel trade={trade} productName="E7S" onChanged={changed} />
        </TradePendingChangesProvider>
      ),
    },
    { path: '/away', element: <p>Anderer Kontext</p> },
  ]);
  render(<RouterProvider router={router} />);
  return router;
}

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

  it('guards discarding or re-reading its prepared cancellation and route navigation', async () => {
    const router = guarded(vi.fn().mockResolvedValue(undefined));
    await prepare();
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.getByRole('alertdialog', { name: 'Ungespeicherte Änderungen' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByLabelText('Stornogrund')).toHaveValue('duplicate');
    expect(screen.getByRole('checkbox')).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    expect(tradeManagementApiClient.cancellationPreview).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await screen.findByLabelText('Stornogrund');
    expect(tradeManagementApiClient.cancellationPreview).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('Stornogrund')).toHaveValue('');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    fireEvent.change(screen.getByLabelText('Stornogrund'), { target: { value: 'new reason' } });
    await act(() => router.navigate('/away'));
    expect(screen.getByRole('alertdialog', { name: 'Ungespeicherte Änderungen' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    expect(screen.getByText('Anderer Kontext')).toBeVisible();
    expect(tradeManagementApiClient.cancel).not.toHaveBeenCalled();
  });

  it('blocks discard through one cancellation POST and its readback, reporting a confirmed write if that read fails', async () => {
    const write = deferred<CancellationPreview>();
    const read = deferred<void>();
    vi.mocked(tradeManagementApiClient.cancel).mockReturnValue(write.promise);
    const router = guarded(() => read.promise);
    await prepare();
    const commit = screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' });
    fireEvent.click(commit);
    fireEvent.click(commit);
    expect(tradeManagementApiClient.cancel).toHaveBeenCalledOnce();
    await act(() => router.navigate('/away'));
    let dialog = screen.getByRole('alertdialog', { name: 'Speicherung läuft' });
    expect(within(dialog).queryByText('Eingaben verwerfen und wechseln')).not.toBeInTheDocument();
    await act(async () => {
      write.resolve({ ...preview, cancelled_at: '2026-09-12T10:00:00Z' });
      await write.promise;
    });
    dialog = screen.getByRole('alertdialog', { name: 'Speicherung läuft' });
    expect(within(dialog).queryByText('Eingaben verwerfen und wechseln')).not.toBeInTheDocument();
    await act(async () => {
      read.reject(new Error('Position nicht verfügbar'));
      await read.promise.catch(() => undefined);
    });
    expect(screen.getByRole('status')).toHaveTextContent(
      'Stornierung gespeichert, Ansicht noch nicht aktualisiert',
    );
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(tradeManagementApiClient.cancel).toHaveBeenCalledOnce();
  });

  it('ignores an obsolete A preview after A to B to A and pins the newly read token', async () => {
    const old = deferred<CancellationPreview>();
    const fresh = { ...preview, state_token: 'b'.repeat(64) };
    const other = { ...trade, id: 'other', product_id: 'other-product' };
    const previewApi = vi.mocked(tradeManagementApiClient.cancellationPreview);
    previewApi
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce({ ...preview, trade_id: other.id, product_id: other.product_id })
      .mockResolvedValue(fresh);
    const { rerender } = render(
      <TradeCancellationPanel trade={trade} productName="A" onChanged={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    rerender(<TradeCancellationPanel trade={other} productName="B" onChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Stornierung prüfen' }));
    await screen.findByLabelText('Stornogrund');
    rerender(<TradeCancellationPanel trade={trade} productName="A" onChanged={vi.fn()} />);
    await prepare();
    await act(async () => {
      old.resolve(preview);
      await old.promise;
    });
    expect(screen.getByLabelText('Stornogrund')).toHaveValue('duplicate');
    expect(screen.getByRole('checkbox')).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' }));
    await waitFor(() => expect(tradeManagementApiClient.cancel).toHaveBeenCalledOnce());
    expect(tradeManagementApiClient.cancel).toHaveBeenCalledWith(
      trade.id,
      expect.objectContaining({ expected_state_token: fresh.state_token }),
    );
  });

  it('does not refresh or show a late cancellation receipt in a different trade context', async () => {
    const write = deferred<CancellationPreview>();
    const changed = vi.fn().mockResolvedValue(undefined);
    vi.mocked(tradeManagementApiClient.cancel).mockReturnValue(write.promise);
    const { rerender } = render(
      <TradeCancellationPanel trade={trade} productName="A" onChanged={changed} />,
    );
    await prepare();
    fireEvent.click(screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' }));
    rerender(
      <TradeCancellationPanel
        trade={{ ...trade, id: 'other' }}
        productName="B"
        onChanged={changed}
      />,
    );
    await act(async () => {
      write.resolve({ ...preview, cancelled_at: '2026-09-12T10:00:00Z' });
      await write.promise;
    });
    expect(changed).not.toHaveBeenCalled();
    expect(screen.queryByText(/Fehleingabe storniert. Kein Verkauf/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Stornogrund')).not.toBeInTheDocument();
  });

  it('checks another participant write lock before cancellation with the preview still pinned', async () => {
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
            <TradeCancellationPanel trade={trade} productName="A" onChanged={vi.fn()} />
          </TradePendingChangesProvider>
        ),
      },
    ]);
    render(<RouterProvider router={router} />);
    await prepare();
    otherWrite = true;
    fireEvent.click(screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' }));
    expect(tradeManagementApiClient.cancel).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Stornogrund')).toHaveValue('duplicate');
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('allows a read-only preview during booking recovery and checks the synchronous recovery lock before posting', async () => {
    let bookingNeedsReview = true;
    const props = {
      trade,
      productName: 'A',
      onChanged: vi.fn(),
      isWriteBlocked: () => bookingNeedsReview,
    };
    const { rerender } = render(<TradeCancellationPanel {...props} />);
    await prepare();
    expect(tradeManagementApiClient.cancellationPreview).toHaveBeenCalledOnce();
    expect(
      screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' }),
    ).toBeDisabled();
    bookingNeedsReview = false;
    rerender(<TradeCancellationPanel {...props} />);
    const commit = screen.getByRole('button', { name: 'Fehleingabe verbindlich stornieren' });
    expect(commit).toBeEnabled();
    bookingNeedsReview = true;
    fireEvent.click(commit);
    expect(tradeManagementApiClient.cancel).not.toHaveBeenCalled();
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});
