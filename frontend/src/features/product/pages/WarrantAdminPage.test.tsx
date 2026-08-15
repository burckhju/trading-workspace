import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { warrantApiClient } from '../services/client';
import { WarrantAdminPage } from './WarrantAdminPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    listIssuers: vi.fn(),
    searchUnderlyings: vi.fn(),
    listTradingVenues: vi.fn(),
  },
}));
vi.mock('../services/client', () => ({
  warrantApiClient: {
    list: vi.fn(),
    create: vi.fn(),
    deactivate: vi.fn(),
    reactivate: vi.fn(),
    terms: vi.fn(),
    addTerms: vi.fn(),
    listings: vi.fn(),
    addListing: vi.fn(),
  },
}));

const market = vi.mocked(marketApiClient);
const warrants = vi.mocked(warrantApiClient);
const warrant = {
  id: '00000000-0000-4000-8001-000000000401',
  workspace_id: '00000000-0000-4000-8000-000000000001',
  issuer_id: '00000000-0000-4000-8001-000000000301',
  underlying_id: '00000000-0000-4000-8001-000000000201',
  product_family: 'WARRANT' as const,
  display_name: 'Siemens Call 180 12/2026',
  isin: 'DE000TEST001',
  wkn: 'TEST01',
  lifecycle_status: 'ACTIVE' as const,
  version: 1,
  created_at: '2026-08-15T12:00:00Z',
  updated_at: '2026-08-15T12:00:00Z',
};

beforeEach(() => {
  vi.clearAllMocks();
  market.listIssuers.mockResolvedValue({
    items: [
      {
        id: warrant.issuer_id,
        legal_name: 'Test Bank AG',
        display_name: 'Test Bank',
        country_code: 'DE',
        lei: null,
      },
    ],
  });
  market.searchUnderlyings.mockResolvedValue({
    items: [
      {
        id: warrant.underlying_id,
        type: 'STOCK',
        name: 'Siemens AG',
        isin: null,
        wkn: null,
        lifecycle_status: 'ACTIVE',
        quality_status: 'COMPLETE',
        version: 1,
        created_at: warrant.created_at,
        updated_at: warrant.updated_at,
        primary_listing: null,
      },
    ],
    total: 1,
    offset: 0,
    limit: 100,
  });
  market.listTradingVenues.mockResolvedValue({
    items: [
      {
        id: '00000000-0000-4000-8001-000000000501',
        mic: 'XETR',
        name: 'Xetra',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: '1',
      },
    ],
  });
  warrants.list.mockResolvedValue([warrant]);
  warrants.terms.mockResolvedValue([
    {
      id: 't1',
      warrant_id: warrant.id,
      version_no: 1,
      effective_from: warrant.created_at,
      effective_to: null,
      option_direction: 'CALL',
      strike: '180',
      maturity_date: '2026-12-18',
      ratio: '0.1',
      created_at: warrant.created_at,
    },
  ]);
  warrants.listings.mockResolvedValue([]);
  warrants.deactivate.mockResolvedValue({ ...warrant, lifecycle_status: 'INACTIVE', version: 2 });
});

describe('WarrantAdminPage', () => {
  it('shows product, terms history and listings as separate user concepts', async () => {
    render(<WarrantAdminPage />);
    expect((await screen.findAllByText('Siemens Call 180 12/2026')).length).toBeGreaterThan(0);
    expect(screen.getByText('Produktbedingungen / Historie')).toBeInTheDocument();
    expect(screen.getByText('Handelbare Notierungen')).toBeInTheDocument();
    expect(screen.getByText(/technische IDs müssen nicht eingegeben werden/)).toBeInTheDocument();
  });

  it('uses the stored version for lifecycle changes', async () => {
    render(<WarrantAdminPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Deaktivieren' }));
    await waitFor(() => expect(warrants.deactivate).toHaveBeenCalledWith(warrant.id, 1));
  });
});

it('creates a warrant and refreshes selection', async () => {
  warrants.create.mockResolvedValue({ ...warrant, id: '00000000-0000-4000-8001-000000000402' });
  warrants.list
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([{ ...warrant, id: '00000000-0000-4000-8001-000000000402' }]);

  render(<WarrantAdminPage />);
  await screen.findByText('Keine Optionsscheine vorhanden.');

  fireEvent.change(screen.getByLabelText('Anzeigename *'), { target: { value: 'Neuer Call' } });
  fireEvent.change(screen.getByLabelText('Emittent *'), { target: { value: warrant.issuer_id } });
  fireEvent.change(screen.getByLabelText('Basiswert *'), {
    target: { value: warrant.underlying_id },
  });
  fireEvent.change(screen.getByLabelText('ISIN'), { target: { value: 'de000abc1234' } });
  fireEvent.change(screen.getByLabelText('WKN'), { target: { value: 'abc123' } });
  fireEvent.change(screen.getByLabelText('Strike *'), { target: { value: '100' } });
  fireEvent.change(screen.getByLabelText('Fälligkeit *'), { target: { value: '2027-06-18' } });
  fireEvent.change(screen.getByLabelText(/^Bezugsverhältnis/), { target: { value: '0.1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));

  await waitFor(() => expect(warrants.create).toHaveBeenCalled());
  expect(warrants.create.mock.calls[0][0]).toMatchObject({
    display_name: 'Neuer Call',
    isin: 'DE000ABC1234',
    wkn: 'ABC123',
  });
});

it('adds a terms version and a listing', async () => {
  warrants.addTerms.mockResolvedValue({
    id: 't2',
    warrant_id: warrant.id,
    version_no: 2,
    effective_from: warrant.updated_at,
    effective_to: null,
    option_direction: 'PUT',
    strike: '170',
    maturity_date: '2027-06-18',
    ratio: '0.2',
    created_at: warrant.updated_at,
  });
  warrants.addListing.mockResolvedValue({
    id: 'l1',
    warrant_id: warrant.id,
    trading_venue_id: '00000000-0000-4000-8001-000000000501',
    symbol: 'SIECALL',
    quotation_currency_code: 'EUR',
    lifecycle_status: 'ACTIVE',
    version: 1,
    workspace_id: warrant.workspace_id,
    created_at: warrant.created_at,
    updated_at: warrant.updated_at,
  });

  render(<WarrantAdminPage />);
  await screen.findByText('Produktbedingungen / Historie');

  fireEvent.change(screen.getByLabelText('Neue Richtung'), { target: { value: 'PUT' } });
  fireEvent.change(screen.getByLabelText('Neuer Strike'), { target: { value: '170' } });
  fireEvent.change(screen.getByLabelText('Neue Fälligkeit'), { target: { value: '2027-06-18' } });
  fireEvent.change(screen.getByLabelText('Neues Bezugsverhältnis'), { target: { value: '0.2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Neue Terms-Version' }));
  await waitFor(() =>
    expect(warrants.addTerms).toHaveBeenCalledWith(
      warrant.id,
      expect.objectContaining({ expected_version: 1, option_direction: 'PUT' }),
    ),
  );

  fireEvent.change(screen.getByLabelText('Handelsplatz'), {
    target: { value: '00000000-0000-4000-8001-000000000501' },
  });
  fireEvent.change(screen.getByLabelText('Symbol'), { target: { value: 'SIECALL' } });
  fireEvent.change(screen.getByLabelText('Handelswährung'), { target: { value: 'usd' } });
  fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
  await waitFor(() =>
    expect(warrants.addListing).toHaveBeenCalledWith(
      warrant.id,
      expect.objectContaining({ symbol: 'SIECALL', quotation_currency_code: 'USD' }),
    ),
  );
});

it('reactivates an inactive warrant and surfaces load errors', async () => {
  const inactive = { ...warrant, lifecycle_status: 'INACTIVE' as const, version: 2 };
  warrants.list.mockResolvedValue([inactive]);
  warrants.reactivate.mockResolvedValue({ ...warrant, version: 3 });

  render(<WarrantAdminPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Reaktivieren' }));
  await waitFor(() => expect(warrants.reactivate).toHaveBeenCalledWith(warrant.id, 2));

  vi.clearAllMocks();
  market.listIssuers.mockRejectedValue(new Error('Referenzdaten nicht verfügbar'));
  market.searchUnderlyings.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
  market.listTradingVenues.mockResolvedValue({ items: [] });
  warrants.list.mockResolvedValue([]);
  render(<WarrantAdminPage />);
  expect(await screen.findByText('Referenzdaten nicht verfügbar')).toBeInTheDocument();
});
