import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { MarketDataRefreshPanel } from './MarketDataRefreshPanel';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
afterEach(() => vi.resetAllMocks());

describe('issuer discovery diagnostics', () => {
  it.each([
    ['ISSUER_ISIN_INVALID', /Die ISIN ist formal ungültig/],
    ['ISSUER_LISTING_MISSING', /Es ist keine Notierung hinterlegt/],
    ['ISSUER_NO_ACTIVE_EUR_LISTING', /Es fehlt eine aktive EUR-Notierung/],
    ['ISSUER_MULTIPLE_ACTIVE_EUR_LISTINGS', /Mehrere aktive EUR-Notierungen passen/],
  ])('explains %s as master data requiring review', async (reason, message) => {
    request.mockResolvedValue({
      enabled: true,
      running: false,
      leader: true,
      settings: {
        warrants_interval_seconds: 300,
        underlyings_interval_seconds: 3600,
        discovery_interval_seconds: 3600,
      },
      jobs: [
        {
          job: 'ISSUER_MAPPING:JPMORGAN:1',
          isin: 'DE000JZ91459',
          name: 'New call',
          status: 'NEEDS_MASTER_DATA',
          reason,
        },
      ],
    });
    render(<MarketDataRefreshPanel />);
    fireEvent.click(screen.getByText('Automatischer Kursabruf'));
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText('Stammdaten ergänzen oder prüfen')).toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(1);
    expect(request.mock.calls[0][0]).toContain('/market-data/refresh/status');
  });
});
