import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrictMode } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import type { UnderlyingDetailResponse } from '../types/api';
import { UnderlyingFormPage } from './UnderlyingFormPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
    getUnderlying: vi.fn(),
    createUnderlying: vi.fn(),
    updateUnderlying: vi.fn(),
  },
}));

const first: UnderlyingDetailResponse = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Testwert A',
  type: 'ETF',
  isin: 'DE0007236101',
  wkn: '723610',
  lifecycle_status: 'ACTIVE',
  quality_status: 'DRAFT',
  version: 7,
  created_at: '2026-10-10T10:00:00Z',
  updated_at: '2026-10-10T10:00:00Z',
  primary_listing: null,
  listings: [],
};
const second: UnderlyingDetailResponse = {
  ...first,
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Testwert B',
  type: 'STOCK',
  isin: null,
  wkn: null,
  version: 3,
};
const edit = (value: UnderlyingDetailResponse) => `/underlyings/${value.id}/edit`;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function mount(path = edit(first), strict = false) {
  const router = createMemoryRouter(
    [
      { path: '/underlyings/new', element: <UnderlyingFormPage /> },
      { path: '/underlyings/:underlyingId/edit', element: <UnderlyingFormPage /> },
      { path: '/underlyings/:underlyingId', element: <h1>Detailseite</h1> },
    ],
    { initialEntries: [path] },
  );
  const view = <RouterProvider router={router} />;
  render(strict ? <StrictMode>{view}</StrictMode> : view);
  return router;
}

async function navigate(router: ReturnType<typeof mount>, path: string) {
  await act(async () => {
    await router.navigate(path);
  });
}

async function settle(callback: () => void) {
  await act(async () => {
    callback();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({
    items: [
      {
        id: '00000000-0000-4000-8001-000000000001',
        mic: 'XETR',
        name: 'Xetra',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: 'TEST',
      },
    ],
  });
  vi.mocked(marketApiClient.listCurrencies).mockResolvedValue({
    items: [
      { code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'TEST' },
      { code: 'USD', name: 'US Dollar', minor_unit: 2, reference_version: 'TEST' },
    ],
  });
  vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
    Promise.resolve(id === first.id ? first : second),
  );
  vi.mocked(marketApiClient.updateUnderlying).mockResolvedValue(second);
  vi.mocked(marketApiClient.createUnderlying).mockResolvedValue(first);
});

describe('Underlying form request isolation', () => {
  it.each([false, true])(
    'ignores late detail data and saves only B (StrictMode: %s)',
    async (strict) => {
      const user = userEvent.setup();
      const pending = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
        id === first.id ? pending.promise : Promise.resolve(second),
      );
      const router = mount(edit(first), strict);
      await navigate(router, edit(second));
      expect(await screen.findByLabelText('Name *')).toHaveValue(second.name);
      await settle(() => pending.resolve(first));
      expect(screen.getByLabelText('Name *')).toHaveValue(second.name);
      await user.clear(screen.getByLabelText('Name *'));
      await user.type(screen.getByLabelText('Name *'), 'Testwert B bearbeitet');
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(second.id, {
        version: second.version,
        name: 'Testwert B bearbeitet',
        isin: null,
        wkn: null,
      });
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    },
  );

  it('does not show a late failure for A in the successfully loaded B form', async () => {
    const pending = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
      id === first.id ? pending.promise : Promise.resolve(second),
    );
    const router = mount();
    await navigate(router, edit(second));
    await screen.findByDisplayValue(second.name);
    await settle(() => pending.reject(new Error('Late failure for A')));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeEnabled();
  });

  it('hides the previous inputs while loading B and stays closed if B fails', async () => {
    const pending = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
      id === first.id ? Promise.resolve(first) : pending.promise,
    );
    const router = mount();
    await screen.findByDisplayValue(first.name);
    await navigate(router, edit(second));
    expect(screen.getByRole('status')).toHaveTextContent('Formular wird vorbereitet');
    expect(screen.queryByRole('textbox', { name: 'Name *' })).not.toBeInTheDocument();
    await settle(() => pending.reject(new Error('B unavailable')));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByLabelText('Name *')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();
    fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
  });

  it.each(['getUnderlying', 'listTradingVenues', 'listCurrencies'] as const)(
    'never creates or updates after an edit load failure in %s',
    async (method) => {
      vi.mocked(marketApiClient[method]).mockRejectedValue(new Error('Load failed'));
      mount();
      await screen.findByRole('alert');
      const name = screen.getByLabelText('Name *');
      // A programmatic submit must also fail closed, independently of disabled buttons.
      fireEvent.submit(name.closest('form')!);
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
      expect(name).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();
    },
  );

  it('never saves an unexpected response identity', async () => {
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(second);
    mount();
    await screen.findByRole('alert');
    fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();
  });

  it('does not create when creation reference data failed to load', async () => {
    vi.mocked(marketApiClient.listCurrencies).mockRejectedValue(new Error('Currencies failed'));
    mount('/underlyings/new');
    await screen.findByRole('alert');
    fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Ticker *')).toBeDisabled();
  });

  it('resets edit data when moving to creation', async () => {
    const router = mount();
    await screen.findByDisplayValue(first.name);
    await navigate(router, '/underlyings/new');
    expect(await screen.findByLabelText('Name *')).toHaveValue('');
    expect(screen.getByLabelText('ISIN')).toHaveValue('');
    expect(screen.getByLabelText('WKN')).toHaveValue('');
    expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
    expect(screen.getByLabelText('Ticker *')).toHaveValue('');
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
  });

  it('clears optional proposal fields when the proposal query changes', async () => {
    const router = mount(
      '/underlyings/new?name=ETF-Vorschlag&type=ETF&isin=DE0007236101&ticker=ALT&currency=USD',
    );
    await screen.findByDisplayValue('ETF-Vorschlag');
    await navigate(router, '/underlyings/new?name=Neuer+Vorschlag');
    expect(await screen.findByLabelText('Name *')).toHaveValue('Neuer Vorschlag');
    expect(screen.getByLabelText('ISIN')).toHaveValue('');
    expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
    expect(screen.getByLabelText('Ticker *')).toHaveValue('');
    expect(screen.getByLabelText('Währung *')).toHaveValue('EUR');
  });

  it.each(['resolve', 'reject'] as const)(
    'ignores an old proposal reference-data %s after a new query is loaded',
    async (outcome) => {
      const pending = deferred<Awaited<ReturnType<typeof marketApiClient.listCurrencies>>>();
      vi.mocked(marketApiClient.listCurrencies).mockReturnValueOnce(pending.promise);
      const router = mount('/underlyings/new?name=Alter+Vorschlag&type=ETF');
      await navigate(router, '/underlyings/new?name=Neuer+Vorschlag');
      await screen.findByDisplayValue('Neuer Vorschlag');
      await settle(() => {
        if (outcome === 'resolve') pending.resolve({ items: [] });
        else pending.reject(new Error('Old proposal failed'));
      });
      expect(screen.getByLabelText('Name *')).toHaveValue('Neuer Vorschlag');
      expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    },
  );

  it.each(['resolve', 'reject'] as const)(
    'ignores a late save %s after navigating from A to B',
    async (outcome) => {
      const user = userEvent.setup();
      const pendingA = deferred<UnderlyingDetailResponse>();
      const pendingB = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.updateUnderlying)
        .mockReturnValueOnce(pendingA.promise)
        .mockReturnValueOnce(pendingB.promise);
      const router = mount();
      await screen.findByDisplayValue(first.name);
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      await navigate(router, edit(second));
      await screen.findByDisplayValue(second.name);
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      await settle(() => {
        if (outcome === 'resolve') pendingA.resolve(first);
        else pendingA.reject(new Error('Old save failed'));
      });
      expect(router.state.location.pathname).toBe(edit(second));
      expect(screen.getByLabelText('Name *')).toHaveValue(second.name);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Speichern …' })).toBeDisabled();
      await settle(() => pendingB.resolve(second));
      expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
    },
  );

  it.each(['resolve', 'reject'] as const)(
    'does not redirect or report an old creation %s after leaving the form',
    async (outcome) => {
      const user = userEvent.setup();
      const pending = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.createUnderlying).mockReturnValue(pending.promise);
      const router = mount('/underlyings/new');
      await user.type(await screen.findByLabelText('Name *'), 'Neuer Testwert');
      await user.type(screen.getByLabelText('Ticker *'), 'TEST');
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      await navigate(router, `/underlyings/${second.id}`);
      await settle(() => {
        if (outcome === 'resolve') pending.resolve(first);
        else pending.reject(new Error('Old creation failed'));
      });
      expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
      expect(screen.getByRole('heading', { name: 'Detailseite' })).toBeInTheDocument();
      expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(1);
    },
  );

  it('does not let an old A save affect a new A form after an A-B-A round trip', async () => {
    const user = userEvent.setup();
    const pending = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.updateUnderlying).mockReturnValue(pending.promise);
    const router = mount();
    await screen.findByDisplayValue(first.name);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await navigate(router, edit(second));
    await screen.findByDisplayValue(second.name);
    await navigate(router, edit(first));
    const name = await screen.findByLabelText('Name *');
    await user.clear(name);
    await user.type(name, 'Neue Bearbeitung von A');
    await settle(() => pending.resolve(first));
    expect(router.state.location.pathname).toBe(edit(first));
    expect(screen.getByLabelText('Name *')).toHaveValue('Neue Bearbeitung von A');
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeEnabled();
  });

  it('does not end the B loading state when an older A request completes', async () => {
    const pendingA = deferred<UnderlyingDetailResponse>();
    const pendingB = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
      id === first.id ? pendingA.promise : pendingB.promise,
    );
    const router = mount();
    await navigate(router, edit(second));
    await settle(() => pendingA.resolve(first));
    expect(screen.getByRole('status')).toHaveTextContent('Formular wird vorbereitet');
    expect(screen.queryByRole('textbox', { name: 'Name *' })).not.toBeInTheDocument();
    await settle(() => pendingB.resolve(second));
    expect(await screen.findByLabelText('Name *')).toHaveValue(second.name);
  });

  it('guards duplicate submits and disables inputs while the current save is pending', async () => {
    const pending = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.updateUnderlying).mockReturnValue(pending.promise);
    mount();
    const name = await screen.findByLabelText('Name *');
    act(() => {
      fireEvent.submit(name.closest('form')!);
      fireEvent.submit(name.closest('form')!);
    });
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(1);
    expect(name).toBeDisabled();
    await settle(() => pending.resolve(first));
  });

  it('preserves edited inputs after a current save error and allows a deliberate retry', async () => {
    const user = userEvent.setup();
    vi.mocked(marketApiClient.updateUnderlying).mockRejectedValueOnce(
      new Error('Version conflict'),
    );
    mount();
    const name = await screen.findByLabelText('Name *');
    await user.clear(name);
    await user.type(name, 'Bewusst bearbeitet');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('alert');
    expect(name).toHaveValue('Bewusst bearbeitet');
    expect(name).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(2);
  });
});
