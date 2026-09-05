import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';
import { UnderlyingSearchCombobox } from './UnderlyingSearchCombobox';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn(),
    searchProviderInstruments: vi.fn(),
  },
}));

const first: UnderlyingSummaryResponse = {
  id: 'underlying-1',
  type: 'STOCK',
  name: 'Siemens AG',
  isin: 'DE0007236101',
  wkn: '723610',
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: '2026-08-07T10:00:00Z',
  updated_at: '2026-08-07T10:00:00Z',
  primary_listing: {
    id: 'listing-1',
    ticker: 'SIE',
    trading_venue_id: 'venue-1',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Xetra',
    currency_code: 'EUR',
  },
};

describe('UnderlyingSearchCombobox', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(marketApiClient.searchUnderlyings).mockImplementation((parameters) =>
      Promise.resolve({
        items: [first],
        total: 25,
        offset: parameters?.offset ?? 0,
        limit: 10,
      }),
    );
    vi.mocked(marketApiClient.searchProviderInstruments).mockResolvedValue({
      provider: 'EODHD',
      items: [],
    });
  });

  it('searches, selects and paginates underlyings', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <MemoryRouter>
        <UnderlyingSearchCombobox value="" onChange={onChange} />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: 'Siemens AG · SIE' });

    await user.type(screen.getByRole('textbox', { name: 'Basiswert suchen' }), ' Siemens ');
    await user.click(screen.getByRole('button', { name: 'Suchen' }));

    await waitFor(() =>
      expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
        expect.objectContaining({
          query: 'Siemens',
          offset: 0,
          limit: 10,
        }),
        expect.any(AbortSignal),
      ),
    );
    expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();

    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Basiswert filtern' }),
      'underlying-1',
    );
    expect(onChange).toHaveBeenCalledWith('underlying-1', 'Siemens AG');

    await user.click(screen.getByRole('button', { name: 'Weiter' }));

    await waitFor(() =>
      expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 10 }),
        expect.any(AbortSignal),
      ),
    );

    await user.click(screen.getByRole('button', { name: 'Zurück' }));

    await waitFor(() =>
      expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 0 }),
        expect.any(AbortSignal),
      ),
    );
  });

  it('offers a controlled EODHD handoff when the local search is empty', async () => {
    const user = userEvent.setup();
    vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 10,
    });
    vi.mocked(marketApiClient.searchProviderInstruments).mockResolvedValue({
      provider: 'EODHD',
      items: [
        {
          provider: 'EODHD',
          provider_symbol: 'AAPL',
          provider_exchange_code: 'US',
          name: 'Apple Inc',
          instrument_type: 'Common Stock',
          currency: 'USD',
          isin: 'US0378331005',
        },
        {
          provider: 'EODHD',
          provider_symbol: 'SPY',
          provider_exchange_code: 'US',
          name: 'SPDR S&P 500 ETF Trust',
          instrument_type: 'ETF',
          currency: 'USD',
          isin: 'US78462F1030',
        },
      ],
    });

    render(
      <MemoryRouter>
        <UnderlyingSearchCombobox value="" onChange={vi.fn()} />
      </MemoryRouter>,
    );

    await user.type(screen.getByRole('textbox', { name: 'Basiswert suchen' }), 'Apple');
    await user.click(screen.getByRole('button', { name: 'Suchen' }));

    await waitFor(() =>
      expect(marketApiClient.searchProviderInstruments).toHaveBeenCalledWith(
        'Apple',
        10,
        expect.any(AbortSignal),
      ),
    );

    const stockLink = await screen.findByRole('link', { name: 'Basiswert anlegen' });
    expect(stockLink).toHaveAttribute(
      'href',
      '/underlyings/new?source=EODHD&ticker=AAPL&exchange=US&name=Apple+Inc&isin=US0378331005&currency=USD',
    );
    expect(screen.getByText('Nicht als STOCK übernehmen')).toBeInTheDocument();
  });
});
