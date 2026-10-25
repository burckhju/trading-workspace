import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { warrantApiClient } from '../services/client';
import { WarrantAdminPage } from './WarrantAdminPage';

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
  market.listCurrencies.mockResolvedValue({
    items: [{ code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'test' }],
  });
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
  warrants.get.mockImplementation((id) => Promise.resolve({ ...warrant, id }));
  warrants.terms.mockImplementation((id) =>
    Promise.resolve([
      {
        id: 't1',
        warrant_id: id,
        version_no: 1,
        effective_from: warrant.created_at,
        effective_to: null,
        option_direction: 'CALL',
        strike: '180',
        maturity_date: '2026-12-18',
        ratio: '0.1',
        created_at: warrant.created_at,
      },
    ]),
  );
  warrants.listings.mockResolvedValue([]);
  warrants.deactivate.mockResolvedValue({ ...warrant, lifecycle_status: 'INACTIVE', version: 2 });
});

async function fillCreation() {
  await screen.findByText('Aktuelle Produktbedingungen');
  fireEvent.click(screen.getByRole('button', { name: 'Neues Produkt' }));
  fireEvent.change(screen.getByLabelText('Anzeigename *'), {
    target: { value: 'Synthetic new Call' },
  });
  fireEvent.change(screen.getByLabelText('Emittent *'), { target: { value: warrant.issuer_id } });
  fireEvent.change(screen.getByLabelText('Basiswert *'), {
    target: { value: warrant.underlying_id },
  });
  fireEvent.change(screen.getByLabelText('Strike *'), { target: { value: '100' } });
  fireEvent.change(screen.getByLabelText('Fälligkeit *'), { target: { value: '2099-12-31' } });
  fireEvent.change(screen.getByLabelText(/^Bezugsverhältnis/), { target: { value: '0.1' } });
  fireEvent.change(screen.getByLabelText('Handelsplatz des Optionsscheins'), {
    target: { value: '00000000-0000-4000-8001-000000000501' },
  });
  fireEvent.change(screen.getByLabelText('Handelswährung des Optionsscheins'), {
    target: { value: 'eur' },
  });
}

it('sends the explicitly entered first listing with the product, never in a second POST', async () => {
  warrants.create.mockResolvedValue({
    ...warrant,
    id: 'new-warrant',
    display_name: 'Synthetic new Call',
  });
  render(<WarrantAdminPage />);
  await fillCreation();
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await waitFor(() => expect(warrants.create).toHaveBeenCalledTimes(1));
  expect(warrants.create.mock.calls[0][0]).toMatchObject({
    display_name: 'Synthetic new Call',
    strike_currency_code: null,
    initial_listing: {
      trading_venue_id: '00000000-0000-4000-8001-000000000501',
      quotation_currency_code: 'EUR',
      symbol: null,
    },
  });
  expect(warrants.addListing).not.toHaveBeenCalled();
  expect(await screen.findByText(/Optionsschein und Notierung gespeichert/)).toBeInTheDocument();
});

it('does not infer the product venue or currency from an underlying or the strike', async () => {
  render(<WarrantAdminPage />);
  await screen.findByText('Aktuelle Produktbedingungen');
  fireEvent.click(screen.getByRole('button', { name: 'Neues Produkt' }));
  expect(screen.getByLabelText('Handelsplatz des Optionsscheins')).toHaveValue('');
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toHaveValue('');
  expect(screen.getByLabelText('Handelsplatz des Optionsscheins')).toBeRequired();
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toBeRequired();
  expect(screen.getByLabelText('Börsensymbol des Optionsscheins')).not.toBeRequired();
  fireEvent.submit(screen.getByRole('button', { name: 'Optionsschein anlegen' }).closest('form')!);
  expect(warrants.create).not.toHaveBeenCalled();
});

it('keeps all entered creation data when the combined save fails', async () => {
  warrants.create.mockRejectedValue(new Error('Handelsplatz nicht verfügbar'));
  render(<WarrantAdminPage />);
  await fillCreation();
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Handelsplatz nicht verfügbar');
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toHaveValue('EUR');
  expect(screen.getByLabelText('Anzeigename *')).toHaveValue('Synthetic new Call');
  expect(warrants.addListing).not.toHaveBeenCalled();
});

it('blocks double submission synchronously and locks the creation inputs while saving', async () => {
  let resolve!: (value: typeof warrant) => void;
  warrants.create.mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  render(<WarrantAdminPage />);
  await fillCreation();
  const form = screen.getByRole('button', { name: 'Optionsschein anlegen' }).closest('form')!;
  act(() => {
    fireEvent.submit(form);
    fireEvent.submit(form);
  });
  expect(warrants.create).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Anzeigename *')).toBeDisabled();
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toBeDisabled();
  await act(async () => {
    resolve({ ...warrant, id: 'new-warrant' });
    await Promise.resolve();
  });
});

it('keeps a confirmed success separate from a failed catalogue refresh and prevents accidental recreation', async () => {
  warrants.create.mockResolvedValue({ ...warrant, id: 'new-warrant' });
  render(<WarrantAdminPage />);
  await fillCreation();
  warrants.list.mockRejectedValueOnce(new Error('Katalog nicht erreichbar'));
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Katalog nicht erreichbar');
  expect(await screen.findByText(/bereits gespeichert.*Nicht erneut anlegen/)).toHaveAttribute(
    'role',
    'status',
  );
  expect(screen.queryByRole('button', { name: 'Optionsschein anlegen' })).not.toBeInTheDocument();
  expect(warrants.create).toHaveBeenCalledTimes(1);
});

it('starts a deliberately new product with empty listing fields instead of reusing the previous product', async () => {
  warrants.create.mockResolvedValue({ ...warrant, id: 'new-warrant' });
  render(<WarrantAdminPage />);
  await fillCreation();
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await screen.findByText(/Optionsschein und Notierung gespeichert/);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Neues Produkt' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Neues Produkt' }));
  expect(screen.getByLabelText('Anzeigename *')).toHaveValue('');
  expect(screen.getByLabelText('Handelsplatz des Optionsscheins')).toHaveValue('');
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toHaveValue('');
  await act(() => Promise.resolve());
});

it('does not display the empty new-terms currency warning until editing is opened', async () => {
  render(<WarrantAdminPage />);
  await screen.findByText('Aktuelle Produktbedingungen');
  expect(screen.getByRole('button', { name: 'Produktbedingungen ändern' })).toBeInTheDocument();
  expect(screen.queryByLabelText('Neue Strike-Währung')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Anzeigename *')).not.toBeInTheDocument();
});

it('keeps the created identity open after a failed detail read and retries only that read', async () => {
  const created = { ...warrant, id: 'new-warrant', display_name: 'Synthetic new Call' };
  warrants.create.mockResolvedValue(created);
  render(<WarrantAdminPage />);
  await fillCreation();
  warrants.list.mockResolvedValue([warrant, created]);
  warrants.get.mockRejectedValueOnce(new Error('Produktdetails nicht erreichbar'));
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));

  expect(await screen.findByRole('alert')).toHaveTextContent(
    /Anzeige konnte nicht aktualisiert werden/,
  );
  expect(await screen.findByText(/Optionsschein und Notierung gespeichert/)).toHaveAttribute(
    'role',
    'status',
  );
  expect(screen.getByRole('heading', { name: created.display_name })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Optionsschein anlegen' })).not.toBeInTheDocument();
  expect(warrants.create).toHaveBeenCalledTimes(1);
  warrants.get.mockImplementation((id) => Promise.resolve(id === created.id ? created : warrant));
  fireEvent.click(screen.getByRole('button', { name: 'Produkt neu laden' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Produktbedingungen ändern' })).toBeEnabled(),
  );
  expect(screen.getByRole('heading', { name: created.display_name })).toBeInTheDocument();
  expect(warrants.get).toHaveBeenLastCalledWith(created.id, expect.any(AbortSignal));
  expect(warrants.create).toHaveBeenCalledTimes(1);
  expect(warrants.addListing).not.toHaveBeenCalled();
});

it('requires an explicit next creation and ignores the previous confirmed product readback', async () => {
  const created = { ...warrant, id: 'new-warrant', display_name: 'Synthetic new Call' };
  let resolve!: (value: typeof created) => void;
  const pending = new Promise<typeof created>((accept) => {
    resolve = accept;
  });
  warrants.create.mockResolvedValue(created);
  render(<WarrantAdminPage />);
  await fillCreation();
  warrants.list.mockResolvedValue([warrant, created]);
  warrants.get.mockImplementation(async (id) => (id === created.id ? pending : warrant));
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await screen.findByRole('heading', { name: created.display_name });
  expect(screen.queryByRole('button', { name: 'Optionsschein anlegen' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Neues Produkt' }));
  expect(screen.getByLabelText('Handelsplatz des Optionsscheins')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Anzeigename *'), {
    target: { value: 'Explicit next product' },
  });
  await act(async () => {
    resolve(created);
    await pending;
  });
  expect(screen.getByLabelText('Anzeigename *')).toHaveValue('Explicit next product');
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toHaveValue('');
  expect(warrants.create).toHaveBeenCalledTimes(1);
});

it('keeps a dirty creation when cancellation is declined and creates nothing when cancelled', async () => {
  const confirm = vi.spyOn(window, 'confirm');
  render(<WarrantAdminPage />);
  await fillCreation();
  confirm.mockReturnValueOnce(false);
  fireEvent.click(screen.getByRole('button', { name: 'Anlage abbrechen' }));
  expect(screen.getByLabelText('Anzeigename *')).toHaveValue('Synthetic new Call');
  expect(screen.getByLabelText('Handelswährung des Optionsscheins')).toHaveValue('EUR');
  confirm.mockReturnValueOnce(true);
  fireEvent.click(screen.getByRole('button', { name: 'Anlage abbrechen' }));
  expect(screen.queryByLabelText('Anzeigename *')).not.toBeInTheDocument();
  expect(warrants.create).not.toHaveBeenCalled();
  expect(warrants.addListing).not.toHaveBeenCalled();
});

it('does not show a late created-product catalogue error after another product is opened', async () => {
  const created = { ...warrant, id: 'new-warrant', display_name: 'Synthetic new Call' };
  let reject!: (reason: Error) => void;
  const pending = new Promise<(typeof warrant)[]>((_resolve, fail) => {
    reject = fail;
  });
  warrants.create.mockResolvedValue(created);
  warrants.get.mockImplementation((id) => Promise.resolve(id === created.id ? created : warrant));
  render(<WarrantAdminPage />);
  await fillCreation();
  warrants.list.mockReturnValueOnce(pending);
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await screen.findByRole('heading', { name: created.display_name });
  fireEvent.click(screen.getByRole('button', { name: new RegExp(warrant.display_name) }));
  await screen.findByRole('heading', { name: warrant.display_name });
  await act(async () => {
    reject(new Error('Katalogfehler der vorherigen Anlage'));
    await pending.catch(() => undefined);
  });
  expect(screen.queryByText(/Katalogfehler der vorherigen Anlage/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Nicht erneut anlegen/)).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: warrant.display_name })).toBeInTheDocument();
  expect(warrants.create).toHaveBeenCalledTimes(1);
});
