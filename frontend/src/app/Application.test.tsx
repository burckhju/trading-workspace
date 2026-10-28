import { render, screen } from '@testing-library/react';
import { beforeEach, vi } from 'vitest';

import { marketApiClient } from '../features/market/services/client';
import { performanceApiClient } from '../features/performance/services/client';
import { Application } from './Application';

vi.mock('../features/market/services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn().mockResolvedValue({ items: [], total: 0, offset: 0, limit: 25 }),
    listTradingVenues: vi.fn().mockResolvedValue({ items: [] }),
    listCurrencies: vi.fn().mockResolvedValue({ items: [] }),
  },
}));
vi.mock('../features/performance/services/client', () => ({
  performanceApiClient: { realizedGross: vi.fn(), closedTrades: vi.fn() },
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
      '/underlyings/new?returnTo=%2Funderlyings',
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

  it.each([
    ['/performance', 'Verkäufe im Zeitraum'],
    ['/performance/realized-gross', 'Verkäufe im Zeitraum'],
    ['/performance/closed-trades', 'Trades mit Vollabschluss im Zeitraum'],
  ])(
    'opens %s through the common Performance navigation without a default read',
    async (path, title) => {
      window.history.pushState({}, '', path);
      render(<Application />);
      expect(await screen.findByRole('heading', { level: 1, name: title })).toBeVisible();
      expect(screen.getByRole('link', { name: 'Performance' })).toHaveAttribute(
        'aria-current',
        'page',
      );
      expect(screen.getAllByRole('form')).toHaveLength(1);
      expect(screen.getByRole('form', { name: 'Performance-Zeitraum auswählen' })).toBeVisible();
      expect(performanceApiClient.realizedGross).not.toHaveBeenCalled();
      expect(performanceApiClient.closedTrades).not.toHaveBeenCalled();
    },
  );
});
