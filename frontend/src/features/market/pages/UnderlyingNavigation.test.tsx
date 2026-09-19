import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApiClient } from '../services/client';
import type { UnderlyingDetailResponse } from '../types/api';
import { UnderlyingListPage } from './UnderlyingListPage';
import { UnderlyingDetailPage } from './UnderlyingDetailPage';
import { UnderlyingFormPage } from './UnderlyingFormPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn(),
    searchProviderInstruments: vi.fn(),
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
    getUnderlying: vi.fn(),
    getUnderlyingAuditEvents: vi.fn(),
    getUnderlyingUsages: vi.fn(),
    updateUnderlying: vi.fn(),
    createUnderlying: vi.fn(),
    deleteUnderlying: vi.fn(),
  },
}));

const venueId = '00000000-0000-4000-8001-000000000001';
let items: UnderlyingDetailResponse[];
function HistoryControls() {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <>
      <div data-testid="location">
        {location.pathname}
        {location.search}
      </div>
      <button onClick={() => void navigate(-1)}>Browser zurück</button>
      <button onClick={() => void navigate(1)}>Browser vorwärts</button>
    </>
  );
}
function renderFlow(entry = '/underlyings') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <HistoryControls />
      <Routes>
        <Route path="/underlyings" element={<UnderlyingListPage />} />
        <Route path="/underlyings/new" element={<UnderlyingFormPage />} />
        <Route path="/underlyings/:underlyingId" element={<UnderlyingDetailPage />} />
        <Route path="/underlyings/:underlyingId/edit" element={<UnderlyingFormPage />} />
      </Routes>
    </MemoryRouter>,
  );
}
const itemName = (index: number) => `Testbasiswert ${String(index).padStart(2, '0')}`;
async function openFromPage(user: ReturnType<typeof userEvent.setup>, page: number) {
  await screen.findByRole('link', { name: itemName(1) });
  for (let current = 1; current < page; current++) {
    await user.click(screen.getByRole('button', { name: 'Weiter' }));
    await screen.findByRole('link', { name: itemName(current * 25 + 1) });
  }
  await user.click(screen.getByRole('link', { name: itemName((page - 1) * 25 + 1) }));
  await screen.findByRole('link', { name: 'Bearbeiten' });
}
async function edit(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('link', { name: 'Bearbeiten' }));
  return screen.findByRole('textbox', { name: 'Name *' });
}

beforeEach(() => {
  vi.resetAllMocks();
  items = Array.from({ length: 60 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
    type: 'STOCK',
    name: itemName(index + 1),
    isin: null,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    quality_status: 'COMPLETE',
    version: 1,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    primary_listing: null,
    listings: [],
  }));
  vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({
    items: [
      {
        id: venueId,
        mic: 'XETR',
        name: 'Xetra',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: 'test',
      },
    ],
  });
  vi.mocked(marketApiClient.listCurrencies).mockResolvedValue({
    items: [
      {
        code: 'EUR',
        name: 'Euro',
        minor_unit: 2,
        reference_version: 'test',
      },
    ],
  });
  vi.mocked(marketApiClient.searchUnderlyings).mockImplementation(({ offset = 0 } = {}) =>
    Promise.resolve({
      items: items.slice(offset, offset + 25),
      total: items.length,
      offset,
      limit: 25,
    }),
  );
  vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
    Promise.resolve(items.find((item) => item.id === id)!),
  );
  vi.mocked(marketApiClient.getUnderlyingAuditEvents).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
  });
  vi.mocked(marketApiClient.getUnderlyingUsages).mockResolvedValue({
    items: [],
  });
  vi.mocked(marketApiClient.updateUnderlying).mockImplementation((id, request) => {
    const index = items.findIndex((item) => item.id === id);
    items[index] = {
      ...items[index],
      ...request,
      name: request.name ?? items[index].name,
      version: request.version + 1,
    };
    return Promise.resolve(items[index]);
  });
  vi.mocked(marketApiClient.deleteUnderlying).mockImplementation((id) => {
    items = items.filter((item) => item.id !== id);
    return Promise.resolve();
  });
});

describe('underlying list return context', () => {
  it.each([2, 3])(
    'returns directly to the original page %s after a successful edit, with fresh data',
    async (page) => {
      const user = userEvent.setup();
      renderFlow();
      await openFromPage(user, page);
      const name = await edit(user);
      await user.clear(name);
      await user.type(name, 'Testbasiswert gepflegt');
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      expect(await screen.findByRole('heading', { name: 'Basiswerte' })).toBeInTheDocument();
      expect(
        await screen.findByRole('link', { name: 'Testbasiswert gepflegt' }),
      ).toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent(`Seite ${page} von 3`);
      expect(marketApiClient.updateUnderlying).toHaveBeenCalledExactlyOnceWith(
        items[(page - 1) * 25].id,
        { version: 1, name: 'Testbasiswert gepflegt', isin: null, wkn: null },
      );
      expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: (page - 1) * 25, limit: 25 }),
        expect.any(AbortSignal),
      );
      expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();
    },
  );

  it('retains submitted search, lifecycle, venue and currency through detail, edit and save', async () => {
    const user = userEvent.setup();
    renderFlow();
    await screen.findByRole('link', { name: itemName(1) });
    await user.type(screen.getByRole('textbox', { name: 'Suche' }), ' Test ');
    await user.click(screen.getByRole('button', { name: 'Suchen' }));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'ACTIVE');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Markt' }), venueId);
    await user.selectOptions(screen.getByRole('combobox', { name: 'Währung' }), 'EUR');
    await openFromPage(user, 3);
    await edit(user);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('heading', { name: 'Basiswerte' });
    await screen.findByRole('link', { name: itemName(51) });
    expect(screen.getByRole('textbox', { name: 'Suche' })).toHaveValue('Test');
    expect(screen.getByRole('combobox', { name: 'Status' })).toHaveValue('ACTIVE');
    expect(screen.getByRole('combobox', { name: 'Markt' })).toHaveValue(venueId);
    expect(screen.getByRole('combobox', { name: 'Währung' })).toHaveValue('EUR');
    expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
      {
        query: 'Test',
        lifecycleStatus: 'ACTIVE',
        tradingVenueId: venueId,
        currencyCode: 'EUR',
        offset: 50,
        limit: 25,
      },
      expect.any(AbortSignal),
    );
  });

  it.each(['Abbrechen', '← Zurück'])('returns to page 3 via %s without saving', async (label) => {
    const user = userEvent.setup();
    renderFlow();
    await openFromPage(user, 3);
    const name = await edit(user);
    await user.type(name, ' ungespeichert');
    await user.click(screen.getByRole('link', { name: label }));
    expect(await screen.findByRole('link', { name: itemName(51) })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Seite 3 von 3');
    expect(marketApiClient.updateUnderlying).not.toHaveBeenCalled();
  });

  it('retains page 3 through the detail backlink and browser back/forward', async () => {
    const user = userEvent.setup();
    renderFlow();
    await openFromPage(user, 3);
    await user.click(screen.getByRole('link', { name: '← Basiswerte' }));
    expect(await screen.findByRole('link', { name: itemName(51) })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Browser zurück' }));
    await screen.findByRole('link', { name: 'Bearbeiten' });
    await user.click(screen.getByRole('button', { name: 'Browser zurück' }));
    expect(await screen.findByRole('link', { name: itemName(51) })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Browser zurück' }));
    expect(await screen.findByRole('link', { name: itemName(26) })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Browser vorwärts' }));
    expect(await screen.findByRole('link', { name: itemName(51) })).toBeInTheDocument();
  });

  it('keeps failed saves in the form with the entered data and return context', async () => {
    const user = userEvent.setup();
    renderFlow();
    await openFromPage(user, 2);
    const name = await edit(user);
    await user.type(name, ' geändert');
    vi.mocked(marketApiClient.updateUnderlying).mockRejectedValueOnce(
      new Error('Speichern fehlgeschlagen'),
    );
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(name).toHaveValue(`${itemName(26)} geändert`);
    expect(screen.getByRole('heading', { name: 'Basiswert bearbeiten' })).toBeInTheDocument();
    expect(marketApiClient.updateUnderlying).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(
      await screen.findByRole('link', { name: `${itemName(26)} geändert` }),
    ).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Seite 2 von 3');
  });

  it('loads a linked page directly and resets pagination only when filters change', async () => {
    const user = userEvent.setup();
    renderFlow('/underlyings?query=Test&offset=50');
    expect(await screen.findByRole('link', { name: itemName(51) })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Suche' })).toHaveValue('Test');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'ACTIVE');
    expect(await screen.findByRole('link', { name: itemName(1) })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Seite 1 von 3');
  });

  it('falls back to the last existing page when the sole last-page item is deleted', async () => {
    items = items.slice(0, 51);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();
    renderFlow();
    await openFromPage(user, 3);
    await user.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(await screen.findByRole('link', { name: itemName(26) })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Seite 2 von 2');
    expect(screen.getByRole('button', { name: 'Weiter' })).toBeDisabled();
    expect(marketApiClient.deleteUnderlying).toHaveBeenCalledTimes(1);
    expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();
  });

  it.each(['', '?returnTo=https%3A%2F%2Fevil.invalid'])(
    'keeps standalone editing compatible and rejects external return targets: %s',
    async (suffix) => {
      const user = userEvent.setup();
      renderFlow(`/underlyings/${items[0].id}/edit${suffix}`);
      await screen.findByRole('textbox', { name: 'Name *' });
      await user.click(screen.getByRole('button', { name: 'Speichern' }));
      expect(await screen.findByRole('heading', { name: itemName(1) })).toBeInTheDocument();
      expect(screen.getByTestId('location')).toHaveTextContent(`/underlyings/${items[0].id}`);
    },
  );
});
