import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { TradePlanWorkflowPage } from './TradePlanWorkflowPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn(),
  },
}));

vi.mock('./TradePlanPage', () => ({
  TradePlanPage: () => <div>Base TradePlan Page</div>,
}));

const marketApi = vi.mocked(marketApiClient);

const apple = {
  id: 'underlying-apple',
  type: 'STOCK' as const,
  name: 'Apple Inc.',
  isin: 'US0378331005',
  wkn: '865985',
  lifecycle_status: 'ACTIVE' as const,
  quality_status: 'VERIFIED' as const,
  version: 1,
  created_at: '2026-09-04T00:00:00Z',
  updated_at: '2026-09-04T00:00:00Z',
  primary_listing: {
    id: 'listing-apple',
    ticker: 'AAPL',
    trading_venue_id: 'venue-1',
    trading_venue_mic: 'XNAS',
    trading_venue_name: 'Nasdaq',
    currency_code: 'USD',
  },
};

describe('TradePlanWorkflowPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    marketApi.searchUnderlyings.mockResolvedValue({
      items: [apple],
      total: 1,
      offset: 0,
      limit: 10,
    });
  });

  it('searches active underlyings by business identifiers and selects the technical id internally', async () => {
    render(
      <MemoryRouter initialEntries={['/trade-plans']}>
        <TradePlanWorkflowPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Basiswert suchen'), { target: { value: 'Apple' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));

    await waitFor(() =>
      expect(marketApi.searchUnderlyings).toHaveBeenCalledWith({
        query: 'Apple',
        lifecycleStatus: 'ACTIVE',
        limit: 10,
      }),
    );

    fireEvent.click(await screen.findByRole('button', { name: /Apple Inc\./ }));

    expect(await screen.findByText(/Technische Referenz übernommen: underlying-apple/)).toBeInTheDocument();
    expect(screen.getByText('Base TradePlan Page')).toBeInTheDocument();
  });

  it('does not show the manual selector when candidate provenance is already supplied', () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/trade-plans?candidate_id=candidate-1&candidate_evaluation_id=evaluation-1',
        ]}
      >
        <TradePlanWorkflowPage />
      </MemoryRouter>,
    );

    expect(screen.queryByLabelText('Basiswert suchen')).not.toBeInTheDocument();
    expect(screen.getByText('Base TradePlan Page')).toBeInTheDocument();
  });
});
