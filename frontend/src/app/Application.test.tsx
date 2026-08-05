import { render, screen } from '@testing-library/react';
import { beforeEach, vi } from 'vitest';

import { marketApiClient } from '../features/market/services/client';
import { Application } from './Application';

vi.mock('../features/market/services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn().mockResolvedValue({ items: [], total: 0, offset: 0, limit: 25 }),
    listTradingVenues: vi.fn().mockResolvedValue({ items: [] }),
    listCurrencies: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

describe('Application', () => {
  beforeEach(() => {
    vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 25,
    });
    vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({ items: [] });
    vi.mocked(marketApiClient.listCurrencies).mockResolvedValue({ items: [] });
  });

  it('renders the FT-001 underlying list as start page', async () => {
    window.history.pushState({}, '', '/');
    render(<Application />);
    expect(await screen.findByRole('heading', { name: 'Basiswerte' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Basiswert anlegen' })).toHaveAttribute(
      'href',
      '/underlyings/new',
    );
    expect(marketApiClient.searchUnderlyings).toHaveBeenCalled();
  });

  it('renders the not-found page for unknown routes', async () => {
    window.history.pushState({}, '', '/unknown');
    render(<Application />);
    expect(
      await screen.findByRole('heading', { name: 'Seite nicht gefunden' }),
    ).toBeInTheDocument();
  });
});
