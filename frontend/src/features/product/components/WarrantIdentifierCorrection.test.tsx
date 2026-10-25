import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useLayoutEffect } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import { warrantApiClient } from '../services/client';
import { MarketApiError } from '../../market/services/http';
import type { WarrantResponse } from '../types/api';
import { WarrantIdentifierCorrection } from './WarrantIdentifierCorrection';

vi.mock('../services/client', () => ({ warrantApiClient: { correctIdentifiers: vi.fn() } }));
const warrant: WarrantResponse = {
  id: 'warrant',
  workspace_id: 'workspace',
  issuer_id: 'issuer',
  underlying_id: 'stock',
  display_name: 'BNP Deere Call',
  isin: 'DE000PK72H6',
  wkn: null,
  product_family: 'WARRANT',
  lifecycle_status: 'ACTIVE',
  version: 1,
  created_at: '',
  updated_at: '',
};
beforeEach(() => vi.clearAllMocks());

it('corrects the same product with version and evidence, without writing trading data', async () => {
  const updated = { ...warrant, isin: 'DE000VH2LU21', version: 2 };
  vi.mocked(warrantApiClient.correctIdentifiers).mockResolvedValue(updated);
  const onSaved = vi.fn();
  render(<WarrantIdentifierCorrection warrant={warrant} onSaved={onSaved} />);
  fireEvent.click(screen.getByText('Kennungen korrigieren'));
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), { target: { value: updated.isin } });
  fireEvent.change(screen.getByLabelText('Beleg / Quelle der Korrektur'), {
    target: { value: 'Testbeleg' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Kennungen speichern' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(updated));
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledWith('warrant', {
    expected_version: 1,
    isin: updated.isin,
    wkn: null,
    evidence: 'Testbeleg',
  });
  expect(screen.getByRole('status')).toHaveTextContent('erneut geprüft');
});

it('shows a conflicting correction without replacing the selected product', async () => {
  vi.mocked(warrantApiClient.correctIdentifiers).mockRejectedValue(new Error('Version geändert'));
  const onSaved = vi.fn();
  const { container } = render(<WarrantIdentifierCorrection warrant={warrant} onSaved={onSaved} />);
  fireEvent.submit(container.querySelector('form')!);
  expect(await screen.findByText('Version geändert')).toBeInTheDocument();
  expect(onSaved).not.toHaveBeenCalled();
});

it('pins the correction to the loaded product version across a background refresh', async () => {
  const onSaved = vi.fn();
  const onDirtyChange = vi.fn();
  const updated = { ...warrant, isin: 'DE000VH2LU21', version: 2 };
  vi.mocked(warrantApiClient.correctIdentifiers).mockResolvedValue(updated);
  const { rerender } = render(
    <WarrantIdentifierCorrection
      warrant={warrant}
      embedded
      onSaved={onSaved}
      onDirtyChange={onDirtyChange}
    />,
  );
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), { target: { value: updated.isin } });
  fireEvent.change(screen.getByLabelText('Beleg / Quelle der Korrektur'), {
    target: { value: 'Korrigiert nach Produktdokument' },
  });
  expect(onDirtyChange).toHaveBeenLastCalledWith(true);
  rerender(
    <WarrantIdentifierCorrection
      warrant={{ ...warrant, version: 9, isin: 'DE000PAH0038' }}
      embedded
      onSaved={onSaved}
      onDirtyChange={onDirtyChange}
    />,
  );
  expect(screen.getByLabelText('Verifizierte ISIN')).toHaveValue(updated.isin);
  fireEvent.click(screen.getByRole('button', { name: 'Kennungen speichern' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(updated));
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledWith(warrant.id, {
    expected_version: 1,
    isin: updated.isin,
    wkn: null,
    evidence: 'Korrigiert nach Produktdokument',
  });
  expect(onDirtyChange).toHaveBeenLastCalledWith(false);
});

it('locks submission and all inputs synchronously until the command completes', async () => {
  let resolve!: (value: WarrantResponse) => void;
  vi.mocked(warrantApiClient.correctIdentifiers).mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const onSaved = vi.fn();
  const onBusyChange = vi.fn();
  const { container } = render(
    <WarrantIdentifierCorrection
      warrant={warrant}
      embedded
      onSaved={onSaved}
      onBusyChange={onBusyChange}
    />,
  );
  act(() => {
    fireEvent.submit(container.querySelector('form')!);
    fireEvent.submit(container.querySelector('form')!);
  });
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledTimes(1);
  expect(onBusyChange).toHaveBeenLastCalledWith(true);
  expect(screen.getByLabelText('Verifizierte ISIN')).toBeDisabled();
  expect(screen.getByLabelText('Beleg / Quelle der Korrektur')).toBeDisabled();
  await act(async () => {
    resolve({ ...warrant, version: 2 });
    await Promise.resolve();
  });
  expect(onSaved).toHaveBeenCalledTimes(1);
  expect(onBusyChange).toHaveBeenLastCalledWith(false);
  fireEvent.submit(container.querySelector('form')!);
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledTimes(1);
});

it('preserves inputs on a version conflict and reloads only on explicit request', async () => {
  vi.mocked(warrantApiClient.correctIdentifiers).mockRejectedValue(
    new MarketApiError(409, {
      code: 'WARRANT_CONCURRENT_MODIFICATION',
      message: 'Produkt wurde inzwischen geändert.',
      details: [],
      timestamp: '',
    }),
  );
  const onReload = vi.fn();
  render(
    <WarrantIdentifierCorrection
      warrant={warrant}
      embedded
      onSaved={vi.fn()}
      onReload={onReload}
    />,
  );
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), {
    target: { value: 'DE000VH2LU21' },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Quelle der Korrektur'), {
    target: { value: 'Bestätigte Originalabrechnung' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Kennungen speichern' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('inzwischen geändert');
  expect(screen.getByLabelText('Verifizierte ISIN')).toHaveValue('DE000VH2LU21');
  expect(screen.getByLabelText('Beleg / Quelle der Korrektur')).toHaveValue(
    'Bestätigte Originalabrechnung',
  );
  expect(onReload).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Produkt neu laden und prüfen' }));
  expect(onReload).toHaveBeenCalledTimes(1);
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledTimes(1);
});

it('does not apply a late correction response after the editor was unmounted', async () => {
  let resolve!: (value: WarrantResponse) => void;
  vi.mocked(warrantApiClient.correctIdentifiers).mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const onSaved = vi.fn();
  const onDirtyChange = vi.fn();
  const onBusyChange = vi.fn();
  const { container, unmount } = render(
    <WarrantIdentifierCorrection
      warrant={warrant}
      embedded
      onSaved={onSaved}
      onDirtyChange={onDirtyChange}
      onBusyChange={onBusyChange}
    />,
  );
  fireEvent.submit(container.querySelector('form')!);
  unmount();
  await act(async () => {
    resolve({ ...warrant, version: 2 });
    await Promise.resolve();
  });
  expect(onSaved).not.toHaveBeenCalled();
  expect(onDirtyChange).not.toHaveBeenCalled();
  expect(onBusyChange.mock.calls).toEqual([[true]]);
});

it('cancels an embedded correction without a mutation', () => {
  const onCancel = vi.fn();
  render(
    <WarrantIdentifierCorrection
      warrant={warrant}
      embedded
      onSaved={vi.fn()}
      onCancel={onCancel}
    />,
  );
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), {
    target: { value: 'DE000VH2LU21' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Korrektur abbrechen' }));
  expect(onCancel).toHaveBeenCalledTimes(1);
  expect(warrantApiClient.correctIdentifiers).not.toHaveBeenCalled();
});

it('keeps the draft locked while the parent reloads the product', () => {
  const onSaved = vi.fn();
  const { rerender, container } = render(
    <WarrantIdentifierCorrection warrant={warrant} embedded onSaved={onSaved} />,
  );
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), {
    target: { value: 'DE000VH2LU21' },
  });
  rerender(<WarrantIdentifierCorrection warrant={warrant} embedded disabled onSaved={onSaved} />);
  expect(screen.getByLabelText('Verifizierte ISIN')).toBeDisabled();
  fireEvent.submit(container.querySelector('form')!);
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), {
    target: { value: 'DE000PAH0038' },
  });
  expect(warrantApiClient.correctIdentifiers).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Verifizierte ISIN')).toHaveValue('DE000VH2LU21');
});

it('ignores completion between destination commit and passive cleanup', async () => {
  let resolve!: (value: WarrantResponse) => void;
  let committed!: () => void;
  const afterCommit = new Promise<void>((done) => {
    committed = done;
  });
  vi.mocked(warrantApiClient.correctIdentifiers).mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const onSaved = vi.fn();
  function Destination() {
    useLayoutEffect(() => {
      resolve({ ...warrant, version: 2 });
      queueMicrotask(committed);
    }, []);
    return <h1>Anderes Produkt</h1>;
  }
  const router = createMemoryRouter(
    [
      {
        path: '/edit',
        element: <WarrantIdentifierCorrection warrant={warrant} embedded onSaved={onSaved} />,
      },
      { path: '/next', element: <Destination /> },
    ],
    { initialEntries: ['/edit'] },
  );
  const view = render(<RouterProvider router={router} />);
  fireEvent.submit(view.container.querySelector('form')!);
  // Exercise a real route commit; act would eagerly flush passive cleanup first.
  const environment = globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean };
  const previous = environment.IS_REACT_ACT_ENVIRONMENT;
  environment.IS_REACT_ACT_ENVIRONMENT = false;
  try {
    await router.navigate('/next');
    await afterCommit;
    expect(router.state.location.pathname).toBe('/next');
    expect(onSaved).not.toHaveBeenCalled();
  } finally {
    view.unmount();
    router.dispose();
    environment.IS_REACT_ACT_ENVIRONMENT = previous;
  }
});
