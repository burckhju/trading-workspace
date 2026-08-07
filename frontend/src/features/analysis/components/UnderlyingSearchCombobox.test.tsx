import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';
import { UnderlyingSearchCombobox } from './UnderlyingSearchCombobox';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    searchUnderlyings: vi.fn(),
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
  });

  it('searches, selects and paginates underlyings', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<UnderlyingSearchCombobox value="" onChange={onChange} />);

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
});
