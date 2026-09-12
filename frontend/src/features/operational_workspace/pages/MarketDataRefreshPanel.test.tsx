import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { MarketDataRefreshPanel } from './MarketDataRefreshPanel';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
const sample = {
  enabled: true,
  running: false,
  leader: true,
  last_error: null,
  settings: {
    warrants_interval_seconds: 300,
    underlyings_interval_seconds: 3600,
    discovery_interval_seconds: 3600,
  },
  jobs: [
    {
      job: 'WARRANT_QUOTES:1',
      name: 'BNP Call',
      isin: 'DE000BN00012',
      status: 'AVAILABLE',
      reason: 'QUOTE_OBSERVATIONS_AVAILABLE',
      next_run_at: '2026-09-12T12:05:00Z',
    },
    {
      job: 'UNDERLYING_EOD:2',
      name: 'Stock',
      isin: null,
      status: 'BLOCKED',
      reason: 'EODHD_DISABLED',
      next_run_at: '2026-09-12T13:00:00Z',
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe('MarketDataRefreshPanel', () => {
  it('loads diagnostics on demand and displays intervals and per-product coverage', async () => {
    request.mockResolvedValue(sample);
    render(<MarketDataRefreshPanel />);
    expect(request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('Automatischer Kursabruf'));
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
    expect(await screen.findByText(/Optionsscheine: alle 5 Min/)).toBeInTheDocument();
    expect(screen.getByText(/BNP Call/)).toBeInTheDocument();
    expect(screen.getByText(/Zuordnung oder Zugang fehlt/)).toBeInTheDocument();
    expect(request.mock.calls[0][0]).toContain('/market-data/refresh/status');
  });
  it('distinguishes disabled configuration from failed retrieval', async () => {
    request.mockResolvedValue({ ...sample, enabled: false, jobs: [] });
    render(<MarketDataRefreshPanel />);
    fireEvent.click(screen.getByText('Automatischer Kursabruf'));
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
    expect(
      await screen.findByText('Automatischer Kursabruf ist ausgeschaltet.'),
    ).toBeInTheDocument();
    request.mockRejectedValue(new Error('network'));
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Abrufstatus konnte nicht geladen werden.',
    );
  });
});
