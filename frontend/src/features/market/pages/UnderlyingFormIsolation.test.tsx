import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrictMode, useLayoutEffect } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import { MarketApiError } from '../services/http';
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
  primary_listing: {
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    ticker: 'ALT',
    trading_venue_id: '00000000-0000-4000-8001-000000000002',
    trading_venue_mic: 'XNAS',
    trading_venue_name: 'Nasdaq',
    currency_code: 'USD',
  },
  listings: [
    {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      underlying_id: '11111111-1111-4111-8111-111111111111',
      trading_venue_id: '00000000-0000-4000-8001-000000000002',
      trading_venue_mic: 'XNAS',
      trading_venue_name: 'Nasdaq',
      ticker: 'ALT',
      currency_code: 'USD',
      lifecycle_status: 'ACTIVE',
      is_primary: true,
      version: 2,
      created_at: '2026-10-10T10:00:00Z',
      updated_at: '2026-10-10T10:00:00Z',
    },
  ],
};
const second: UnderlyingDetailResponse = {
  ...first,
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Testwert B',
  type: 'STOCK',
  isin: null,
  wkn: null,
  version: 3,
  primary_listing: null,
  listings: [],
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
      { path: '/underlyings', element: <h1>Basiswertliste</h1> },
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
      {
        id: '00000000-0000-4000-8001-000000000002',
        mic: 'XNAS',
        name: 'Nasdaq',
        country_code: 'US',
        timezone: 'America/New_York',
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
      expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
    },
  );

  it.each(['resolve', 'reject'] as const)(
    'ignores the first A load %s after an A-B-A round trip and saves the new A version',
    async (outcome) => {
      const user = userEvent.setup();
      const pending = deferred<UnderlyingDetailResponse>();
      const current = { ...first, name: 'Aktuell geladenes A', version: 11 };
      vi.mocked(marketApiClient.getUnderlying)
        .mockReturnValueOnce(pending.promise)
        .mockResolvedValueOnce(second)
        .mockResolvedValueOnce(current);
      vi.mocked(marketApiClient.updateUnderlying).mockResolvedValue(current);
      const router = mount();
      await navigate(router, edit(second));
      await screen.findByDisplayValue(second.name);
      await navigate(router, edit(first));
      const name = await screen.findByDisplayValue(current.name);
      await user.clear(name);
      await user.type(name, 'Neue Eingabe für A');
      await settle(() => {
        if (outcome === 'resolve') pending.resolve(first);
        else pending.reject(new Error('First A load failed'));
      });
      expect(name).toHaveValue('Neue Eingabe für A');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(first.id, {
        version: 11,
        name: 'Neue Eingabe für A',
        isin: first.isin,
        wkn: first.wkn,
      });
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      expect(router.state.location.pathname).toBe(`/underlyings/${first.id}`);
    },
  );

  it.each(['resolve', 'reject'] as const)(
    'ignores a replaced StrictMode effect load %s with a distinct current response',
    async (outcome) => {
      const user = userEvent.setup();
      const discarded = deferred<UnderlyingDetailResponse>();
      const pendingCurrent = deferred<UnderlyingDetailResponse>();
      const current = { ...first, name: 'Aktueller StrictMode-Aufruf', version: 13 };
      vi.mocked(marketApiClient.getUnderlying)
        .mockReturnValueOnce(discarded.promise)
        .mockReturnValueOnce(pendingCurrent.promise);
      vi.mocked(marketApiClient.updateUnderlying).mockResolvedValue(current);
      const router = mount(edit(first), true);
      expect(marketApiClient.getUnderlying).toHaveBeenCalledTimes(2);
      await settle(() => pendingCurrent.resolve(current));
      const name = await screen.findByDisplayValue(current.name);
      await user.clear(name);
      await user.type(name, 'Bewusste aktuelle Eingabe');
      await settle(() => {
        if (outcome === 'resolve') discarded.resolve(first);
        else discarded.reject(new Error('Discarded effect load failed'));
      });
      expect(name).toHaveValue('Bewusste aktuelle Eingabe');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(first.id, {
        version: 13,
        name: 'Bewusste aktuelle Eingabe',
        isin: first.isin,
        wkn: first.wkn,
      });
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      expect(router.state.location.pathname).toBe(`/underlyings/${first.id}`);
    },
  );

  it.each(['resolve', 'reject'] as const)(
    'ignores an underlying load %s after the form unmounts',
    async (outcome) => {
      const pending = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.getUnderlying).mockReturnValue(pending.promise);
      const router = mount();
      await navigate(router, `/underlyings/${second.id}`);
      await settle(() => {
        if (outcome === 'resolve') pending.resolve(first);
        else pending.reject(new Error('Unmounted form load failed'));
      });
      expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
      expect(screen.getByRole('heading', { name: 'Detailseite' })).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
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

  it.each(['listTradingVenues', 'listCurrencies'] as const)(
    'does not create when creation reference data failed to load in %s',
    async (method) => {
      vi.mocked(marketApiClient[method]).mockRejectedValue(new Error('Reference data failed'));
      mount('/underlyings/new');
      await screen.findByRole('alert');
      expect(screen.getByText(/Speichern ist gesperrt, weil das Formular/)).toBeInTheDocument();
      fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
      expect(screen.getByLabelText('Name *')).toBeDisabled();
      expect(screen.getByLabelText('Ticker *')).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();
    },
  );

  it('resets edit data when moving to creation', async () => {
    const router = mount();
    await screen.findByDisplayValue(first.name);
    await navigate(router, '/underlyings/new');
    expect(await screen.findByLabelText('Name *')).toHaveValue('');
    expect(screen.getByLabelText('ISIN')).toHaveValue('');
    expect(screen.getByLabelText('WKN')).toHaveValue('');
    expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
    expect(screen.getByLabelText('Ticker *')).toHaveValue('');
    expect(screen.getByLabelText('Markt *')).toHaveValue('00000000-0000-4000-8001-000000000001');
    expect(screen.getByLabelText('Währung *')).toHaveValue('EUR');
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
  });

  it('loads only current edit data after leaving a failed creation proposal', async () => {
    const user = userEvent.setup();
    vi.mocked(marketApiClient.createUnderlying).mockRejectedValue(new Error('Creation failed'));
    const router = mount(
      '/underlyings/new?source=EODHD&name=ETF-Vorschlag&type=ETF&isin=DE0007236101&ticker=ALT&currency=USD',
    );
    await screen.findByDisplayValue('ETF-Vorschlag');
    await user.type(screen.getByLabelText('WKN'), 'ALT123');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('alert');
    await navigate(router, edit(second));
    expect(await screen.findByLabelText('Name *')).toHaveValue(second.name);
    expect(screen.getByLabelText('ISIN')).toHaveValue('');
    expect(screen.getByLabelText('WKN')).toHaveValue('');
    expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
    expect(screen.getByLabelText('Basiswertart')).toBeDisabled();
    expect(screen.queryByLabelText('Ticker *')).not.toBeInTheDocument();
    expect(screen.queryByText('Vorschlag aus EODHD übernommen')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(second.id, {
      version: second.version,
      name: second.name,
      isin: null,
      wkn: null,
    });
    expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(1);
    expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
  });

  it('clears optional proposal fields, listing choices and errors when the proposal query changes', async () => {
    const user = userEvent.setup();
    vi.mocked(marketApiClient.createUnderlying).mockRejectedValue(
      new Error('Proposal save failed'),
    );
    const router = mount(
      '/underlyings/new?source=EODHD&name=ETF-Vorschlag&type=ETF&isin=DE0007236101&ticker=ALT&currency=USD&mic=XNAS',
    );
    await screen.findByDisplayValue('ETF-Vorschlag');
    expect(screen.getByLabelText('Markt *')).toHaveValue('00000000-0000-4000-8001-000000000002');
    await user.type(screen.getByLabelText('WKN'), 'ALT123');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('alert');
    await navigate(router, '/underlyings/new?name=Neuer+Vorschlag');
    expect(await screen.findByLabelText('Name *')).toHaveValue('Neuer Vorschlag');
    expect(screen.getByLabelText('ISIN')).toHaveValue('');
    expect(screen.getByLabelText('WKN')).toHaveValue('');
    expect(screen.getByLabelText('Basiswertart')).toHaveValue('STOCK');
    expect(screen.getByLabelText('Ticker *')).toHaveValue('');
    expect(screen.getByLabelText('Markt *')).toHaveValue('00000000-0000-4000-8001-000000000001');
    expect(screen.getByLabelText('Währung *')).toHaveValue('EUR');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText('Vorschlag aus EODHD übernommen')).not.toBeInTheDocument();
    expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(1);
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
  });

  it('keeps edited proposal inputs and the pending save across equivalent query encodings', async () => {
    const user = userEvent.setup();
    const pending = deferred<UnderlyingDetailResponse>();
    vi.mocked(marketApiClient.createUnderlying).mockReturnValue(pending.promise);
    const router = mount('/underlyings/new?name=Neuer+Vorschlag&ticker=TEST');
    const name = await screen.findByLabelText('Name *');
    await user.clear(name);
    await user.type(name, 'Bewusst bearbeiteter Vorschlag');
    await user.type(screen.getByLabelText('WKN'), 'NEU123');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await navigate(router, '/underlyings/new?name=Neuer%20Vorschlag&ticker=TEST');
    expect(screen.getByLabelText('Name *')).toHaveValue('Bewusst bearbeiteter Vorschlag');
    expect(screen.getByLabelText('WKN')).toHaveValue('NEU123');
    expect(screen.getByLabelText('Name *')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Speichern …' })).toBeDisabled();
    expect(marketApiClient.listTradingVenues).toHaveBeenCalledTimes(1);
    expect(marketApiClient.listCurrencies).toHaveBeenCalledTimes(1);
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
    fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
    expect(marketApiClient.createUnderlying).toHaveBeenCalledExactlyOnceWith({
      name: 'Bewusst bearbeiteter Vorschlag',
      type: 'STOCK',
      isin: null,
      wkn: 'NEU123',
      primary_listing: {
        trading_venue_id: '00000000-0000-4000-8001-000000000001',
        ticker: 'TEST',
        currency_code: 'EUR',
        is_primary: true,
      },
    });
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
    await settle(() => pending.resolve(first));
    expect(router.state.location.pathname).toBe(`/underlyings/${first.id}`);
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
      expect(screen.getByLabelText('Name *')).toBeDisabled();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Speichern …' })).toBeDisabled();
      fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(2);
      expect(marketApiClient.updateUnderlying).toHaveBeenNthCalledWith(2, second.id, {
        version: second.version,
        name: second.name,
        isin: null,
        wkn: null,
      });
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      await settle(() => pendingB.resolve(second));
      expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
    },
  );

  it('ignores an old save resolved between the destination commit and passive cleanup', async () => {
    const user = userEvent.setup();
    const pending = deferred<UnderlyingDetailResponse>();
    const committed = deferred<void>();
    vi.mocked(marketApiClient.updateUnderlying).mockReturnValue(pending.promise);
    function Destination() {
      useLayoutEffect(() => {
        pending.resolve(first);
        queueMicrotask(() => committed.resolve(undefined));
      }, []);
      return <h1>Detailseite</h1>;
    }
    const router = createMemoryRouter(
      [
        { path: '/underlyings/:underlyingId/edit', element: <UnderlyingFormPage /> },
        { path: '/underlyings/:underlyingId', element: <Destination /> },
      ],
      { initialEntries: [edit(first)] },
    );
    const view = render(<RouterProvider router={router} />);
    await screen.findByDisplayValue(first.name);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    const navigation = vi.spyOn(router, 'navigate');
    const target = `/underlyings/${second.id}`;
    // act drains passive effects before yielding; exercise the real transition scheduler here.
    const actEnvironment = globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean };
    const originalActEnvironment = actEnvironment.IS_REACT_ACT_ENVIRONMENT;
    actEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
    try {
      await router.navigate(target);
      await committed.promise;
      expect(navigation.mock.calls.map(([destination]) => destination)).toEqual([target]);
      expect(router.state.location.pathname).toBe(target);
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(first.id, {
        version: first.version,
        name: first.name,
        isin: first.isin,
        wkn: first.wkn,
      });
      expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    } finally {
      router.dispose();
      view.unmount();
      actEnvironment.IS_REACT_ACT_ENVIRONMENT = originalActEnvironment;
    }
  });

  it.each(['resolve', 'reject'] as const)(
    'ignores an old creation %s while the next proposal has its own pending save',
    async (outcome) => {
      const user = userEvent.setup();
      const pendingA = deferred<UnderlyingDetailResponse>();
      const pendingB = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.createUnderlying)
        .mockReturnValueOnce(pendingA.promise)
        .mockReturnValueOnce(pendingB.promise);
      const router = mount(
        '/underlyings/new?name=Alter+Vorschlag&type=ETF&isin=DE0007236101&ticker=ALT&currency=USD&mic=XNAS',
      );
      await screen.findByDisplayValue('Alter Vorschlag');
      await user.type(screen.getByLabelText('WKN'), 'ALT123');
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      const currentPath = '/underlyings/new?name=Aktueller+Vorschlag&ticker=NEU';
      await navigate(router, currentPath);
      await screen.findByDisplayValue('Aktueller Vorschlag');
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      await settle(() => {
        if (outcome === 'resolve') pendingA.resolve(first);
        else pendingA.reject(new Error('Old creation failed'));
      });
      expect(router.state.location.pathname + router.state.location.search).toBe(currentPath);
      expect(screen.getByLabelText('Name *')).toHaveValue('Aktueller Vorschlag');
      expect(screen.getByLabelText('Name *')).toBeDisabled();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Speichern …' })).toBeDisabled();
      fireEvent.submit(screen.getByLabelText('Name *').closest('form')!);
      expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(2);
      expect(marketApiClient.createUnderlying).toHaveBeenNthCalledWith(2, {
        name: 'Aktueller Vorschlag',
        type: 'STOCK',
        isin: null,
        wkn: null,
        primary_listing: {
          trading_venue_id: '00000000-0000-4000-8001-000000000001',
          ticker: 'NEU',
          currency_code: 'EUR',
          is_primary: true,
        },
      });
      expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
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

  it('keeps B loading when A completes first and then saves only the B identity and version', async () => {
    const user = userEvent.setup();
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
    await user.clear(screen.getByLabelText('Name *'));
    await user.type(screen.getByLabelText('Name *'), 'B nach beiden Antworten');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(second.id, {
      version: second.version,
      name: 'B nach beiden Antworten',
      isin: null,
      wkn: null,
    });
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(router.state.location.pathname).toBe(`/underlyings/${second.id}`);
  });

  it.each(['edit', 'create'] as const)(
    'guards synchronous duplicate %s submits and disables inputs during the current save',
    async (mode) => {
      const pending = deferred<UnderlyingDetailResponse>();
      vi.mocked(marketApiClient.updateUnderlying).mockReturnValue(pending.promise);
      vi.mocked(marketApiClient.createUnderlying).mockReturnValue(pending.promise);
      const router = mount(
        mode === 'edit' ? edit(first) : '/underlyings/new?name=Neuer+Testwert&ticker=TEST',
      );
      const name = await screen.findByLabelText('Name *');
      act(() => {
        fireEvent.submit(name.closest('form')!);
        fireEvent.submit(name.closest('form')!);
      });
      if (mode === 'edit') {
        expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(first.id, {
          version: first.version,
          name: first.name,
          isin: first.isin,
          wkn: first.wkn,
        });
        expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
      } else {
        expect(marketApiClient.createUnderlying).toHaveBeenCalledExactlyOnceWith({
          name: 'Neuer Testwert',
          type: 'STOCK',
          isin: null,
          wkn: null,
          primary_listing: {
            trading_venue_id: '00000000-0000-4000-8001-000000000001',
            ticker: 'TEST',
            currency_code: 'EUR',
            is_primary: true,
          },
        });
        expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
        expect(screen.getByLabelText('Ticker *')).toBeDisabled();
      }
      expect(name).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Speichern …' })).toBeDisabled();
      await settle(() => pending.resolve(first));
      expect(router.state.location.pathname).toBe(`/underlyings/${first.id}`);
    },
  );

  it('preserves inputs and the loaded version across a conflict and deliberate retry', async () => {
    const user = userEvent.setup();
    const conflict = new MarketApiError(409, {
      code: 'UNDERLYING_CONCURRENT_MODIFICATION',
      message: 'Der Basiswert wurde zwischenzeitlich geändert. Bitte neu laden und prüfen.',
      details: [],
      timestamp: '2026-10-17T08:00:00Z',
    });
    vi.mocked(marketApiClient.getUnderlying)
      .mockResolvedValueOnce(first)
      .mockResolvedValue({ ...first, version: 99 });
    vi.mocked(marketApiClient.updateUnderlying).mockRejectedValue(conflict);
    const router = mount();
    const name = await screen.findByLabelText('Name *');
    await user.clear(name);
    await user.type(name, 'Bewusst bearbeitet');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(conflict.response.message);
    expect(name).toHaveValue('Bewusst bearbeitet');
    expect(name).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeEnabled();
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(2);
    for (const call of [1, 2]) {
      expect(marketApiClient.updateUnderlying).toHaveBeenNthCalledWith(call, first.id, {
        version: first.version,
        name: 'Bewusst bearbeitet',
        isin: first.isin,
        wkn: first.wkn,
      });
    }
    expect(marketApiClient.getUnderlying).toHaveBeenCalledExactlyOnceWith(first.id);
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(router.state.location.pathname).toBe(edit(first));
    expect(screen.getByRole('alert')).toHaveTextContent(conflict.response.message);
    expect(name).toHaveValue('Bewusst bearbeitet');
    expect(name).toBeEnabled();
  });

  it('keeps creation inputs after a current error and saves the same payload on deliberate retry', async () => {
    const user = userEvent.setup();
    vi.mocked(marketApiClient.createUnderlying)
      .mockRejectedValueOnce(new Error('Current creation failed'))
      .mockResolvedValueOnce(first);
    const router = mount('/underlyings/new?name=Bewusste+Neuanlage&ticker=NEU');
    await screen.findByDisplayValue('Bewusste Neuanlage');
    await user.type(screen.getByLabelText('WKN'), 'NEU123');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('Name *')).toHaveValue('Bewusste Neuanlage');
    expect(screen.getByLabelText('WKN')).toHaveValue('NEU123');
    expect(screen.getByLabelText('Ticker *')).toHaveValue('NEU');
    expect(screen.getByLabelText('Name *')).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeEnabled();
    expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(marketApiClient.createUnderlying).toHaveBeenCalledTimes(2);
    for (const call of [1, 2]) {
      expect(marketApiClient.createUnderlying).toHaveBeenNthCalledWith(call, {
        name: 'Bewusste Neuanlage',
        type: 'STOCK',
        isin: null,
        wkn: 'NEU123',
        primary_listing: {
          trading_venue_id: '00000000-0000-4000-8001-000000000001',
          ticker: 'NEU',
          currency_code: 'EUR',
          is_primary: true,
        },
      });
    }
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
    expect(router.state.location.pathname).toBe(`/underlyings/${first.id}`);
  });

  it.each([
    { path: edit(first), action: 'Abbrechen', destination: `/underlyings/${first.id}` },
    { path: edit(first), action: '← Zurück', destination: `/underlyings/${first.id}` },
    { path: '/underlyings/new', action: 'Abbrechen', destination: '/underlyings' },
    { path: '/underlyings/new', action: '← Zurück', destination: '/underlyings' },
  ])('leaves $path through $action without a mutation', async ({ path, action, destination }) => {
    const user = userEvent.setup();
    const router = mount(path);
    const name = await screen.findByLabelText('Name *');
    await user.clear(name);
    await user.type(name, 'Nicht gespeicherte Eingabe');
    if (path === '/underlyings/new') await user.type(screen.getByLabelText('Ticker *'), 'NEU');
    await user.click(screen.getByRole('link', { name: action }));
    expect(router.state.location.pathname).toBe(destination);
    expect(marketApiClient.createUnderlying).not.toHaveBeenCalled();
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
  });
});
