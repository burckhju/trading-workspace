import { render, screen } from '@testing-library/react';
import { beforeEach, vi } from 'vitest';

import { marketApiClient } from '../features/market/services/client';
import { performanceApiClient } from '../features/performance/services/client';
import { Application } from './Application';
import { operationalWorkspaceApiClient } from '../features/operational_workspace/services/client';

vi.mock('../features/operational_workspace/services/client', () => ({
  operationalWorkspaceApiClient: {
    getActions: vi.fn().mockResolvedValue({ generated_at: '2026-11-21T10:00:00Z', actions: [] }),
  },
}));

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

  it('opens current attention at home and keeps the direct underlying entry', async () => {
    window.history.pushState({}, '', '/');
    render(<Application />);
    expect(await screen.findByRole('heading', { name: 'Aktuelles' })).toBeInTheDocument();
    expect(await screen.findByText('Aktuell keine offenen Hinweise')).toBeInTheDocument();
    expect(operationalWorkspaceApiClient.getActions).toHaveBeenCalledTimes(1);
    expect(marketApiClient.searchUnderlyings).not.toHaveBeenCalled();
  });

  it('preserves the existing underlying deep link', async () => {
    window.history.pushState({}, '', '/underlyings');
    render(<Application />);
    expect(await screen.findByRole('heading', { name: 'Basiswerte' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Basiswert anlegen' })).toHaveAttribute(
      'href',
      '/underlyings/new?returnTo=%2Funderlyings',
    );
    expect(marketApiClient.searchUnderlyings).toHaveBeenCalled();
  });

  it('keeps query and fragment when following the historical performance alias', async () => {
    window.history.pushState({}, '', '/performance?opaque=exact%20value#retained-anchor');
    render(<Application />);
    await screen.findByRole('heading', { name: 'Verkäufe im Zeitraum' });
    expect(window.location.pathname).toBe('/performance/realized-gross');
    expect(window.location.search).toBe('?opaque=exact%20value');
    expect(window.location.hash).toBe('#retained-anchor');
    expect(performanceApiClient.realizedGross).not.toHaveBeenCalled();
  });

  it('redirects historical root filter bookmarks to the underlying owner with exact context', async () => {
    vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
      items: [],
      total: 100,
      offset: 25,
      limit: 25,
    });
    const query = '?query=SAP&lifecycle=ACTIVE&venue=legacy&currency=EUR&offset=25';
    window.history.pushState({}, '', `/${query}#list-context`);
    render(<Application />);
    await screen.findByRole('heading', { name: 'Basiswerte' });
    expect(window.location.pathname).toBe('/underlyings');
    expect(window.location.search).toBe(query);
    expect(window.location.hash).toBe('#list-context');
    expect(operationalWorkspaceApiClient.getActions).not.toHaveBeenCalled();
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
      expect(
        screen.getByRole('link', {
          name:
            path === '/performance/closed-trades' ? 'Vollabschlüsse im Zeitraum' : 'Performance',
        }),
      ).toHaveAttribute('aria-current', 'page');
      expect(screen.getAllByRole('form')).toHaveLength(1);
      expect(screen.getByRole('form', { name: 'Performance-Zeitraum auswählen' })).toBeVisible();
      expect(performanceApiClient.realizedGross).not.toHaveBeenCalled();
      expect(performanceApiClient.closedTrades).not.toHaveBeenCalled();
    },
  );
});
