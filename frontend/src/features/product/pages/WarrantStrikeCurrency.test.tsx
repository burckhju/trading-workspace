import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { warrantApiClient } from '../services/client';
import type { WarrantResponse, WarrantTermsResponse } from '../types/api';
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
    create: vi.fn(),
    terms: vi.fn(),
    addTerms: vi.fn(),
    listings: vi.fn(),
    addListing: vi.fn(),
  },
}));

const market = vi.mocked(marketApiClient);
const warrants = vi.mocked(warrantApiClient);
const warrant: WarrantResponse = {
  id: 'warrant-1',
  workspace_id: 'workspace-1',
  issuer_id: 'issuer-1',
  underlying_id: 'underlying-1',
  product_family: 'WARRANT',
  display_name: 'Test Call 500',
  isin: null,
  wkn: null,
  lifecycle_status: 'ACTIVE',
  version: 1,
  created_at: '2026-09-12T08:00:00Z',
  updated_at: '2026-09-12T08:00:00Z',
};
const legacyTerms: WarrantTermsResponse = {
  id: 'terms-1',
  warrant_id: warrant.id,
  version_no: 1,
  effective_from: warrant.created_at,
  effective_to: null,
  option_direction: 'CALL',
  strike: '500',
  strike_currency_code: null,
  maturity_date: '2027-01-15',
  ratio: '0.1',
  created_at: warrant.created_at,
};

beforeEach(() => {
  vi.resetAllMocks();
  market.listCurrencies.mockResolvedValue({
    items: [
      { code: 'CHF', name: 'Swiss Franc', minor_unit: 2, reference_version: 'test' },
      { code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'test' },
      { code: 'USD', name: 'US Dollar', minor_unit: 2, reference_version: 'test' },
    ],
  });
  market.listIssuers.mockResolvedValue({
    items: [
      {
        id: warrant.issuer_id,
        legal_name: 'Test Issuer AG',
        display_name: 'Test Issuer',
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
        name: 'Test Stock',
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
        id: 'venue-1',
        mic: 'XSTU',
        name: 'Test Venue',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: '1',
      },
    ],
  });
  warrants.list.mockResolvedValue([warrant]);
  warrants.terms.mockResolvedValue([legacyTerms]);
  warrants.listings.mockResolvedValue([
    {
      id: 'listing-1',
      workspace_id: warrant.workspace_id,
      warrant_id: warrant.id,
      trading_venue_id: 'venue-1',
      symbol: 'TESTCALL',
      quotation_currency_code: 'EUR',
      lifecycle_status: 'ACTIVE',
      version: 1,
      created_at: warrant.created_at,
      updated_at: warrant.updated_at,
    },
  ]);
  warrants.create.mockResolvedValue(warrant);
});

function fillProduct() {
  fireEvent.change(screen.getByLabelText('Anzeigename *'), { target: { value: 'Test Call' } });
  fireEvent.change(screen.getByLabelText('Emittent *'), { target: { value: warrant.issuer_id } });
  fireEvent.change(screen.getByLabelText('Basiswert *'), {
    target: { value: warrant.underlying_id },
  });
  fireEvent.change(screen.getByLabelText('Strike *'), { target: { value: '500' } });
  fireEvent.change(screen.getByLabelText('Fälligkeit *'), { target: { value: '2027-01-15' } });
  fireEvent.change(screen.getByLabelText(/^Bezugsverhältnis/), { target: { value: '0.1' } });
}

it('does not infer a legacy strike currency from an EUR quotation', async () => {
  render(<WarrantAdminPage />);
  expect(await screen.findByText(/Strike 500 \(Währung ungeklärt\)/)).toBeInTheDocument();
  expect(screen.getByLabelText('Strike-Währung')).toHaveValue('');
  expect(screen.getByLabelText('Neue Strike-Währung')).toHaveValue('');
  expect(screen.getByText(/Test Venue · EUR/)).toBeInTheDocument();

  fillProduct();
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await waitFor(() =>
    expect(warrants.create).toHaveBeenCalledWith(
      expect.objectContaining({ strike: '500', strike_currency_code: null }),
    ),
  );
});

it.each(['USD', 'CHF'])('posts %s independently of EUR', async (code) => {
  render(<WarrantAdminPage />);
  await screen.findByText(/Strike 500 \(Währung ungeklärt\)/);
  const selector = screen.getByRole('combobox', { name: 'Strike-Währung' });
  await within(selector).findByRole('option', { name: new RegExp(`^${code}`) });
  fillProduct();
  fireEvent.change(selector, { target: { value: code } });
  expect(selector).toHaveValue(code);
  expect(screen.getByLabelText('Handelswährung')).toHaveValue('EUR');
  fireEvent.click(screen.getByRole('button', { name: 'Optionsschein anlegen' }));
  await waitFor(() =>
    expect(warrants.create).toHaveBeenCalledWith(
      expect.objectContaining({ strike: '500', strike_currency_code: code }),
    ),
  );
});

it.each(['USD', 'CHF'])('adds %s terms and retains history', async (code) => {
  const next = {
    ...legacyTerms,
    id: 'terms-2',
    version_no: 2,
    strike_currency_code: code,
  };
  warrants.addTerms.mockResolvedValue(next);
  render(<WarrantAdminPage />);
  await screen.findByText(/Strike 500 \(Währung ungeklärt\)/);
  const selector = screen.getByRole('combobox', { name: 'Neue Strike-Währung' });
  await within(selector).findByRole('option', { name: new RegExp(`^${code}`) });

  fireEvent.change(screen.getByLabelText('Neuer Strike'), { target: { value: '500' } });
  fireEvent.change(selector, { target: { value: code } });
  fireEvent.change(screen.getByLabelText('Neue Fälligkeit'), { target: { value: '2027-01-15' } });
  fireEvent.change(screen.getByLabelText('Neues Bezugsverhältnis'), { target: { value: '0.1' } });
  warrants.terms.mockResolvedValue([{ ...legacyTerms, effective_to: warrant.updated_at }, next]);
  fireEvent.click(screen.getByRole('button', { name: 'Neue Terms-Version' }));

  await waitFor(() =>
    expect(warrants.addTerms).toHaveBeenCalledWith(
      warrant.id,
      expect.objectContaining({
        expected_version: 1,
        strike: '500',
        strike_currency_code: code,
      }),
    ),
  );
  expect(await screen.findByText(new RegExp(`Strike 500 ${code}`))).toBeInTheDocument();
  expect(screen.getByText(/Strike 500 \(Währung ungeklärt\)/)).toBeInTheDocument();
  expect(screen.getByText(/Test Venue · EUR/)).toBeInTheDocument();
  expect(warrants.addListing).not.toHaveBeenCalled();
});
