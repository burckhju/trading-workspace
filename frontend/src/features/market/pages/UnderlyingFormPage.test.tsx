import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
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

const detail: UnderlyingDetailResponse = {
  id: '11111111-1111-4111-8111-111111111111',
  type: 'STOCK',
  name: 'Siemens AG',
  isin: 'DE0007236101',
  wkn: '723610',
  lifecycle_status: 'ACTIVE',
  quality_status: 'COMPLETE',
  version: 7,
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
  listings: [
    {
      id: '22222222-2222-4222-8222-222222222222',
      underlying_id: '11111111-1111-4111-8111-111111111111',
      trading_venue_id: '00000000-0000-4000-8001-000000000001',
      trading_venue_mic: 'XETR',
      trading_venue_name: 'Xetra',
      ticker: 'SIE',
      currency_code: 'EUR',
      lifecycle_status: 'ACTIVE',
      is_primary: true,
      version: 2,
      created_at: '2026-08-04T10:00:00Z',
      updated_at: '2026-08-04T11:00:00Z',
    },
  ],
};

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
  vi.mocked(marketApiClient.createUnderlying).mockResolvedValue(detail);
  vi.mocked(marketApiClient.updateUnderlying).mockResolvedValue(detail);
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(detail);
});

describe('UnderlyingFormPage', () => {
  it('creates an underlying with a primary listing and navigates to detail', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/underlyings/new']}>
        <Routes>
          <Route path="/underlyings/new" element={<UnderlyingFormPage />} />
          <Route path="/underlyings/:underlyingId" element={<h1>Detail</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(await screen.findByRole('textbox', { name: 'Name *' }), 'Siemens AG');
    await user.type(screen.getByRole('textbox', { name: 'ISIN' }), 'de0007236101');
    await user.type(screen.getByRole('textbox', { name: 'WKN' }), '723610');
    await user.type(screen.getByRole('textbox', { name: 'Ticker *' }), 'sie');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(marketApiClient.createUnderlying).toHaveBeenCalledWith({
      name: 'Siemens AG',
      isin: 'DE0007236101',
      wkn: '723610',
      primary_listing: {
        trading_venue_id: '00000000-0000-4000-8001-000000000001',
        ticker: 'SIE',
        currency_code: 'EUR',
        is_primary: true,
      },
    });
    expect(await screen.findByRole('heading', { name: 'Detail' })).toBeInTheDocument();
  });

  it('updates only underlying master data with the loaded version', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/underlyings/11111111-1111-4111-8111-111111111111/edit']}>
        <Routes>
          <Route path="/underlyings/:underlyingId/edit" element={<UnderlyingFormPage />} />
          <Route path="/underlyings/:underlyingId" element={<h1>Detail</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    const name = await screen.findByRole('textbox', { name: 'Name *' });
    await user.clear(name);
    await user.type(name, 'Siemens Energy AG');
    expect(screen.queryByRole('textbox', { name: 'Ticker *' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(marketApiClient.updateUnderlying).toHaveBeenCalledWith(detail.id, {
      version: 7,
      name: 'Siemens Energy AG',
      isin: 'DE0007236101',
      wkn: '723610',
    });
  });
});
