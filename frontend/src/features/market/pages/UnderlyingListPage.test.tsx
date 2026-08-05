import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import type { UnderlyingSearchResponse } from '../types/api';
import { UnderlyingListPage } from './UnderlyingListPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn(),
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
  },
}));

const result: UnderlyingSearchResponse = {
  items: [
    {
      id: '11111111-1111-4111-8111-111111111111',
      type: 'STOCK',
      name: 'Siemens AG',
      isin: 'DE0007236101',
      wkn: '723610',
      lifecycle_status: 'ACTIVE',
      quality_status: 'COMPLETE',
      version: 3,
      created_at: '2026-08-04T10:00:00Z',
      updated_at: '2026-08-04T11:00:00Z',
      primary_listing: {
        id: '22222222-2222-4222-8222-222222222222',
        ticker: 'SIE',
        trading_venue_id: '00000000-0000-4000-8001-000000000001',
        trading_venue_mic: 'XETR',
        trading_venue_name: 'Xetra',
        currency_code: 'EUR',
      },
    },
  ],
  total: 1,
  offset: 0,
  limit: 25,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <UnderlyingListPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({
    items: [
      {
        id: '00000000-0000-4000-8001-000000000001',
        mic: 'XETR',
        name: 'Xetra',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: 'FT-001-V1',
      },
    ],
  });
  vi.mocked(marketApiClient.listCurrencies).mockResolvedValue({
    items: [{ code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'FT-001-V1' }],
  });
  vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue(result);
});

describe('UnderlyingListPage', () => {
  it('loads controlled filters and renders the primary listing without detail requests', async () => {
    renderPage();

    expect(await screen.findByRole('link', { name: 'Siemens AG' })).toHaveAttribute(
      'href',
      '/underlyings/11111111-1111-4111-8111-111111111111',
    );
    expect(screen.getByText('SIE · Xetra · EUR')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Xetra · XETR' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'EUR · Euro' })).toBeInTheDocument();
    expect(marketApiClient.searchUnderlyings).toHaveBeenCalledWith(
      expect.objectContaining({ lifecycleStatus: 'ACTIVE', offset: 0, limit: 25 }),
      expect.any(AbortSignal),
    );
  });

  it('submits search and server-side venue and currency filters', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('Siemens AG');

    await user.type(screen.getByRole('textbox', { name: 'Suche' }), '  SIE  ');
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Markt' }),
      '00000000-0000-4000-8001-000000000001',
    );
    await user.selectOptions(screen.getByRole('combobox', { name: 'Währung' }), 'EUR');
    await user.click(screen.getByRole('button', { name: 'Suchen' }));

    await waitFor(() =>
      expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
        {
          query: 'SIE',
          lifecycleStatus: 'ACTIVE',
          tradingVenueId: '00000000-0000-4000-8001-000000000001',
          currencyCode: 'EUR',
          offset: 0,
          limit: 25,
        },
        expect.any(AbortSignal),
      ),
    );
  });

  it('shows an empty state for an empty result', async () => {
    vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 25,
    });
    renderPage();
    expect(
      await screen.findByRole('heading', { name: 'Keine Basiswerte gefunden' }),
    ).toBeInTheDocument();
  });
});
