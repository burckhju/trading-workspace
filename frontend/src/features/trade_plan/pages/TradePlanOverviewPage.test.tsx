import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { tradePlanOverviewApiClient } from '../services/overviewClient';
import { TradePlanOverviewPage } from './TradePlanOverviewPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    getUnderlying: vi.fn(),
  },
}));

vi.mock('../services/overviewClient', () => ({
  tradePlanOverviewApiClient: {
    list: vi.fn(),
  },
}));

const overviewApi = vi.mocked(tradePlanOverviewApiClient);
const marketApi = vi.mocked(marketApiClient);

describe('TradePlanOverviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    overviewApi.list.mockResolvedValue([
      {
        id: '12345678-0000-4000-8000-000000000001',
        underlying_id: 'underlying-1',
        origin_type: 'MANUAL',
        created_at: '2026-09-05T06:00:00Z',
        latest_version_id: 'version-1',
        latest_version: 1,
        status: 'DRAFT',
      },
    ]);
    marketApi.getUnderlying.mockResolvedValue({
      id: 'underlying-1',
      type: 'STOCK',
      name: 'Apple Inc.',
      isin: 'US0378331005',
      wkn: '865985',
      lifecycle_status: 'ACTIVE',
      quality_status: 'VERIFIED',
      version: 1,
      created_at: '2026-09-05T05:00:00Z',
      updated_at: '2026-09-05T05:00:00Z',
      primary_listing: {
        id: 'listing-1',
        ticker: 'AAPL',
        trading_venue_id: 'venue-1',
        trading_venue_mic: 'XNAS',
        trading_venue_name: 'Nasdaq',
        currency_code: 'USD',
      },
      listings: [],
    });
  });

  it('shows existing plans with user-facing identity and open action', async () => {
    render(
      <MemoryRouter>
        <TradePlanOverviewPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('TP-12345678')).toBeInTheDocument();
    expect(screen.getByText(/AAPL · US0378331005 · 865985/)).toBeInTheDocument();
    expect(screen.getByText('DRAFT')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Öffnen' })).toHaveAttribute(
      'href',
      '/trade-plans?trade_plan_id=12345678-0000-4000-8000-000000000001',
    );
  });
});
