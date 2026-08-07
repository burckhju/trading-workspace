import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { analysisApiClient } from '../services/client';
import { analysisPreferenceClient } from '../services/preferencesClient';
import { MarketAnalysisPage } from './MarketAnalysisPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { searchUnderlyings: vi.fn(), getUnderlying: vi.fn() },
}));
vi.mock('../services/client', () => ({
  analysisApiClient: {
    listPage: vi.fn(),
    create: vi.fn(),
    exportUrl: vi.fn(() => '/api/v1/market-analyses/export.csv'),
  },
}));

vi.mock('../services/preferencesClient', () => ({
  analysisPreferenceClient: {
    create: vi.fn(),
    delete: vi.fn(),
    list: vi.fn().mockResolvedValue([]),
  },
}));

const underlyingId = '11111111-1111-4111-8111-111111111111';
const listingId = '22222222-2222-4222-8222-222222222222';

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  vi.mocked(analysisApiClient.listPage).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 20,
  });
  const preferenceClient = vi.mocked(analysisPreferenceClient);

  preferenceClient.list.mockResolvedValue([]);
  preferenceClient.create.mockImplementation((request) =>
    Promise.resolve({
      id: 'saved-view-1',
      ...request,
    }),
  );

  vi.mocked(analysisApiClient.create).mockResolvedValue({
    id: '33333333-3333-4333-8333-333333333333',
    underlying_id: underlyingId,
    listing_id: listingId,
    created_at: '2026-08-06T10:00:00Z',
    created_by: 'Tester',
  });
  vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
    items: [
      {
        id: underlyingId,
        type: 'STOCK',
        name: 'Siemens AG',
        isin: 'DE0007236101',
        wkn: '723610',
        lifecycle_status: 'ACTIVE',
        quality_status: 'VERIFIED',
        version: 1,
        created_at: '2026-08-06T10:00:00Z',
        updated_at: '2026-08-06T10:00:00Z',
        primary_listing: {
          id: listingId,
          ticker: 'SIE',
          trading_venue_id: '44444444-4444-4444-8444-444444444444',
          trading_venue_mic: 'XETR',
          trading_venue_name: 'Xetra',
          currency_code: 'EUR',
        },
      },
    ],
    total: 1,
    offset: 0,
    limit: 20,
  });
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue({
    id: underlyingId,
    type: 'STOCK',
    name: 'Siemens AG',
    isin: 'DE0007236101',
    wkn: '723610',
    lifecycle_status: 'ACTIVE',
    quality_status: 'VERIFIED',
    version: 1,
    created_at: '2026-08-06T10:00:00Z',
    updated_at: '2026-08-06T10:00:00Z',
    primary_listing: {
      id: listingId,
      ticker: 'SIE',
      trading_venue_id: '44444444-4444-4444-8444-444444444444',
      trading_venue_mic: 'XETR',
      trading_venue_name: 'Xetra',
      currency_code: 'EUR',
    },
    listings: [
      {
        id: listingId,
        underlying_id: underlyingId,
        trading_venue_id: '44444444-4444-4444-8444-444444444444',
        trading_venue_mic: 'XETR',
        trading_venue_name: 'Xetra',
        ticker: 'SIE',
        currency_code: 'EUR',
        lifecycle_status: 'ACTIVE',
        is_primary: true,
        version: 1,
        created_at: '2026-08-06T10:00:00Z',
        updated_at: '2026-08-06T10:00:00Z',
      },
    ],
  });
});

describe('MarketAnalysisPage', () => {
  it('creates an analysis using selected domain references instead of UUID inputs', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MarketAnalysisPage />
      </MemoryRouter>,
    );

    await user.selectOptions(
      await screen.findByRole('combobox', { name: 'Basiswert' }),
      underlyingId,
    );
    await waitFor(() =>
      expect(marketApiClient.getUnderlying).toHaveBeenCalledWith(
        underlyingId,
        expect.any(AbortSignal),
      ),
    );
    expect(
      await screen.findByRole('option', { name: 'SIE · Xetra · EUR · Primär' }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Analyse anlegen' }));

    await waitFor(() =>
      expect(analysisApiClient.create).toHaveBeenCalledWith(underlyingId, listingId),
    );
  });

  it('persists date filters, renders removable chips and resets all overview filters', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          '/market-analyses?status=COMPLETED&quality_status=GOOD&analysis_time_from=2026-08-01T08%3A00&analysis_time_to=2026-08-06T18%3A00&sort_by=latest_analysis_time&sort_direction=asc',
        ]}
      >
        <MarketAnalysisPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(analysisApiClient.listPage).toHaveBeenCalledWith(
        0,
        20,
        expect.objectContaining({
          status: 'COMPLETED',
          qualityStatus: 'GOOD',
          analysisTimeFrom: '2026-08-01T08:00',
          analysisTimeTo: '2026-08-06T18:00',
          sortBy: 'latest_analysis_time',
          sortDirection: 'asc',
        }),
        expect.any(AbortSignal),
      ),
    );

    expect(
      screen.getByRole('button', { name: 'Status: Abgeschlossen entfernen' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Qualität: Gut entfernen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ab: .* entfernen/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bis: .* entfernen/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Status: Abgeschlossen entfernen' }));
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: 'Status: Abgeschlossen entfernen' }),
      ).not.toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Filter zurücksetzen' }));
    expect(screen.getByRole('combobox', { name: 'Status filtern' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Qualität filtern' })).toHaveValue('');
    expect(screen.getByLabelText('Analysezeit ab')).toHaveValue('');
    expect(screen.getByLabelText('Analysezeit bis')).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Sortieren nach' })).toHaveValue('created_at');
    expect(screen.getByRole('combobox', { name: 'Sortierrichtung' })).toHaveValue('desc');
  });

  it('filters by underlying and saves the current configuration as a named view', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MarketAnalysisPage />
      </MemoryRouter>,
    );

    const underlyingFilter = await screen.findByRole('combobox', { name: 'Basiswert filtern' });
    await user.selectOptions(underlyingFilter, underlyingId);
    await waitFor(() =>
      expect(analysisApiClient.listPage).toHaveBeenLastCalledWith(
        0,
        20,
        expect.objectContaining({ underlyingId }),
        expect.any(AbortSignal),
      ),
    );

    await user.type(screen.getByRole('textbox', { name: 'Name der Ansicht' }), 'Siemens Analysen');
    await user.click(screen.getByRole('button', { name: 'Ansicht speichern' }));
    expect(screen.getByRole('option', { name: 'Siemens Analysen' })).toBeInTheDocument();
    const preferenceClient = vi.mocked(analysisPreferenceClient);
    expect(preferenceClient.create.mock.calls.at(-1)?.[0]).toEqual({
      name: 'Siemens Analysen',
      underlyingId,
      underlyingLabel: 'Siemens AG',
      status: '',
      qualityStatus: '',
      analysisTimeFrom: '',
      analysisTimeTo: '',
      sortBy: 'created_at',
      sortDirection: 'desc',
    });
  });

  it('applies and deletes a persisted saved view', async () => {
    const user = userEvent.setup();
    const preferenceClient = vi.mocked(analysisPreferenceClient);

    preferenceClient.list.mockResolvedValue([
      {
        id: 'saved-view-existing',
        name: 'Gespeicherte Siemens-Ansicht',
        underlyingId,
        underlyingLabel: 'Siemens AG',
        status: 'COMPLETED',
        qualityStatus: 'GOOD',
        analysisTimeFrom: '2026-08-01T08:00',
        analysisTimeTo: '2026-08-06T18:00',
        sortBy: 'latest_analysis_time',
        sortDirection: 'asc',
      },
    ]);
    preferenceClient.delete.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <MarketAnalysisPage />
      </MemoryRouter>,
    );

    const savedView = await screen.findByRole('combobox', {
      name: 'Gespeicherte Ansicht',
    });

    await screen.findByRole('option', {
      name: 'Gespeicherte Siemens-Ansicht',
    });

    await user.selectOptions(savedView, 'saved-view-existing');

    expect(screen.getByRole('combobox', { name: 'Status filtern' })).toHaveValue('COMPLETED');
    expect(screen.getByRole('combobox', { name: 'Qualität filtern' })).toHaveValue('GOOD');
    expect(screen.getByLabelText('Analysezeit ab')).toHaveValue('2026-08-01T08:00');
    expect(screen.getByLabelText('Analysezeit bis')).toHaveValue('2026-08-06T18:00');
    expect(screen.getByRole('combobox', { name: 'Sortieren nach' })).toHaveValue(
      'latest_analysis_time',
    );
    expect(screen.getByRole('combobox', { name: 'Sortierrichtung' })).toHaveValue('asc');

    await user.click(screen.getByRole('button', { name: 'Ansicht löschen' }));

    await waitFor(() =>
      expect(preferenceClient.delete.mock.calls.at(-1)?.[0]).toBe('saved-view-existing'),
    );

    expect(
      screen.queryByRole('option', { name: 'Gespeicherte Siemens-Ansicht' }),
    ).not.toBeInTheDocument();
  });
});
