import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';
import { WarrantAdminPageWithDelete } from './WarrantAdminPageWithDelete';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    listIssuers: vi.fn(),
    searchUnderlyings: vi.fn(),
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
  },
}));
vi.mock('../services/client', () => ({
  warrantApiClient: {
    list: vi.fn(),
    get: vi.fn(),
    terms: vi.fn(),
    listings: vi.fn(),
    delete: vi.fn(),
  },
}));

const market = vi.mocked(marketApiClient);
const warrants = vi.mocked(warrantApiClient);
const warrantA: WarrantResponse = {
  id: '00000000-0000-4000-8001-000000000401',
  workspace_id: '00000000-0000-4000-8000-000000000001',
  issuer_id: '00000000-0000-4000-8001-000000000301',
  underlying_id: '00000000-0000-4000-8001-000000000201',
  product_family: 'WARRANT',
  display_name: 'A Siemens Call',
  isin: 'DE000AAAA001',
  wkn: 'AAAA01',
  lifecycle_status: 'ACTIVE',
  version: 4,
  created_at: '2026-08-15T12:00:00Z',
  updated_at: '2026-08-15T12:00:00Z',
};
const warrantB: WarrantResponse = {
  ...warrantA,
  id: '00000000-0000-4000-8001-000000000402',
  display_name: 'B Siemens Put',
  isin: 'DE000BBBB002',
  wkn: 'BBBB02',
  version: 9,
};

beforeEach(() => {
  vi.resetAllMocks();
  market.listIssuers.mockResolvedValue({ items: [] });
  market.searchUnderlyings.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
  market.listTradingVenues.mockResolvedValue({ items: [] });
  market.listCurrencies.mockResolvedValue({ items: [] });
  warrants.list.mockResolvedValue([warrantA, warrantB]);
  warrants.get.mockImplementation((id) =>
    Promise.resolve(id === warrantB.id ? warrantB : warrantA),
  );
  warrants.terms.mockImplementation((id) =>
    Promise.resolve([
      {
        id: `terms-${id}`,
        warrant_id: id,
        version_no: 1,
        effective_from: warrantA.created_at,
        effective_to: null,
        option_direction: 'PUT',
        strike: '123.45',
        strike_currency_code: 'USD',
        maturity_date: '2027-12-17',
        ratio: '0.1',
        created_at: warrantA.created_at,
      },
    ]),
  );
  warrants.listings.mockResolvedValue([]);
  warrants.delete.mockResolvedValue(undefined);
});

async function openB() {
  render(<WarrantAdminPageWithDelete />);
  fireEvent.click(await screen.findByRole('button', { name: /B Siemens Put/ }));
  await screen.findByRole('heading', { name: warrantB.display_name });
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Produktbedingungen ändern' })).toBeEnabled(),
  );
  fireEvent.click(screen.getByText('Weitere Aktionen'));
}

describe('deletion belongs to the opened warrant', () => {
  it('confirms and deletes B with its version while A is first, without a second catalogue', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    await openB();

    expect(warrants.list).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole('button', { name: 'Löschverwaltung öffnen' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('option', { name: /A Siemens Call|B Siemens Put/ }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(confirm.mock.calls[0][0]).toContain(warrantB.display_name);
    expect(confirm.mock.calls[0][0]).toContain(warrantB.isin);
    expect(confirm.mock.calls[0][0]).not.toContain(warrantA.display_name);
    await waitFor(() => expect(warrants.delete).toHaveBeenCalledWith(warrantB.id, 9));
    expect(warrants.delete).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/wurde gelöscht/)).toBeInTheDocument();
  });

  it('keeps B open and does not delete when confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    await openB();
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

    expect(warrants.delete).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: warrantB.display_name })).toBeInTheDocument();
  });

  it('retains B and the server history-use rejection after a blocked delete', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    warrants.delete.mockRejectedValue(
      new Error('Der Optionsschein wird bereits historisch oder operativ verwendet.'),
    );
    await openB();
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('historisch oder operativ');
    expect(screen.getByRole('heading', { name: warrantB.display_name })).toBeInTheDocument();
    expect(warrants.delete).toHaveBeenCalledWith(warrantB.id, warrantB.version);
    expect(warrants.delete).toHaveBeenCalledTimes(1);
  });
});
