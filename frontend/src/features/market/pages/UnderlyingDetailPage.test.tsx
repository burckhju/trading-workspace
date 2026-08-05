import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import type { UnderlyingDetailResponse } from '../types/api';
import { UnderlyingDetailPage } from './UnderlyingDetailPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    getUnderlying: vi.fn(),
    getUnderlyingAuditEvents: vi.fn(),
    getUnderlyingUsages: vi.fn(),
    verifyUnderlying: vi.fn(),
    deactivateUnderlying: vi.fn(),
    reactivateUnderlying: vi.fn(),
    deleteUnderlying: vi.fn(),
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
  version: 4,
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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/underlyings/11111111-1111-4111-8111-111111111111']}>
      <Routes>
        <Route path="/underlyings/:underlyingId" element={<UnderlyingDetailPage />} />
        <Route path="/underlyings" element={<h1>Liste</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(detail);
  vi.mocked(marketApiClient.getUnderlyingAuditEvents).mockResolvedValue({
    items: [
      {
        id: '33333333-3333-4333-8333-333333333333',
        aggregate_type: 'UNDERLYING',
        aggregate_id: detail.id,
        occurred_at: '2026-08-04T11:00:00Z',
        actor_display_name: 'Test User',
        change_type: 'UPDATED',
        version_before: 3,
        version_after: 4,
        field_changes: { name: { old: 'Siemens', new: 'Siemens AG' } },
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
  });
  vi.mocked(marketApiClient.getUnderlyingUsages).mockResolvedValue({
    items: [
      { usage_type: 'WATCHLIST', count: 2, object_ids: ['44444444-4444-4444-8444-444444444444'] },
    ],
  });
  vi.mocked(marketApiClient.verifyUnderlying).mockResolvedValue({
    ...detail,
    quality_status: 'VERIFIED',
    version: 5,
  });
  vi.mocked(marketApiClient.deactivateUnderlying).mockResolvedValue({
    ...detail,
    lifecycle_status: 'INACTIVE',
    version: 5,
  });
  vi.mocked(marketApiClient.deleteUnderlying).mockResolvedValue(undefined);
});

describe('UnderlyingDetailPage', () => {
  it('renders detail, listings, usages and audit history', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Siemens AG' })).toBeInTheDocument();
    expect(screen.getByText('Xetra')).toBeInTheDocument();
    expect(screen.getByText('WATCHLIST')).toBeInTheDocument();
    expect(screen.getByText('UPDATED')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('passes the current optimistic-locking version to verify and reloads', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Verifizieren' }));
    expect(marketApiClient.verifyUnderlying).toHaveBeenCalledWith(detail.id, { version: 4 });
    await waitFor(() => expect(marketApiClient.getUnderlying).toHaveBeenCalledTimes(2));
  });

  it('requires confirmation before deletion and navigates after success', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Löschen' }));
    expect(window.confirm).toHaveBeenCalled();
    expect(marketApiClient.deleteUnderlying).toHaveBeenCalledWith(detail.id, 4);
    expect(await screen.findByRole('heading', { name: 'Liste' })).toBeInTheDocument();
  });
});
