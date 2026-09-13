import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApiClient } from '../../market/services/client';
import { productSelectionApiClient } from '../../product_selection/services/client';
import type { ProductSelectionRunDetailResponse } from '../../product_selection/types/api';
import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';
import { WarrantAdminPage } from './index';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    listIssuers: vi.fn(),
    searchUnderlyings: vi.fn(),
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
    getUnderlying: vi.fn(),
  },
}));
vi.mock('../../product_selection/services/client', () => ({
  productSelectionApiClient: {
    get: vi.fn(),
    start: vi.fn(),
    select: vi.fn(),
  },
}));
vi.mock('../services/client', () => ({
  warrantApiClient: {
    list: vi.fn(),
    terms: vi.fn(),
    listings: vi.fn(),
    create: vi.fn(),
    addListing: vi.fn(),
    addTerms: vi.fn(),
    delete: vi.fn(),
  },
}));
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const underlying = {
  id: id(201),
  type: 'STOCK' as const,
  name: 'Synthetic repair stock',
  isin: null,
  wkn: null,
  lifecycle_status: 'ACTIVE' as const,
  quality_status: 'COMPLETE' as const,
  version: 1,
  created_at: '2026-09-01T12:00:00Z',
  updated_at: '2026-09-01T12:00:00Z',
  primary_listing: null,
  listings: [],
};
const target: WarrantResponse = {
  id: id(401),
  workspace_id: id(1),
  issuer_id: id(301),
  underlying_id: underlying.id,
  product_family: 'WARRANT',
  display_name: 'Synthetic target warrant',
  isin: null,
  wkn: null,
  lifecycle_status: 'ACTIVE',
  version: 1,
  created_at: underlying.created_at,
  updated_at: underlying.updated_at,
};
const other = { ...target, id: id(402), underlying_id: id(202), display_name: 'Unrelated warrant' };
let detail: ProductSelectionRunDetailResponse;
const route = (suffix = `selection_run_id=${id(101)}&warrant_id=${target.id}`) => {
  render(
    <MemoryRouter initialEntries={[`/warrants-admin?${suffix}`]}>
      <WarrantAdminPage />
    </MemoryRouter>,
  );
};
beforeEach(() => {
  vi.resetAllMocks();
  detail = {
    run: {
      id: id(101),
      trade_plan_id: id(501),
      trade_plan_version_id: id(502),
      trade_plan_version_status: 'APPROVED',
      underlying_id: underlying.id,
      evaluated_at: underlying.created_at,
      created_at: underlying.created_at,
      created_by: id(2),
      universe_model: { model_id: 'universe', model_version: '1' },
      eligibility_model: { model_id: 'eligibility', model_version: '1' },
      evaluation_model: { model_id: 'evaluation', model_version: '1' },
    },
    evaluations: [],
    selection: null,
    universe_omissions: [
      { warrant_id: target.id, reason: 'NO_LISTING', explanation: 'No listing' },
    ],
  };
  vi.mocked(productSelectionApiClient.get).mockImplementation(() => Promise.resolve(detail));
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(underlying);
  vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
    items: [],
    total: 0,
    limit: 100,
    offset: 0,
  });
  vi.mocked(marketApiClient.listIssuers).mockResolvedValue({
    items: [
      {
        id: target.issuer_id,
        legal_name: 'Synthetic issuer',
        display_name: 'Synthetic issuer',
        country_code: null,
        lei: null,
      },
    ],
  });
  vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({
    items: [
      {
        id: id(601),
        mic: 'TEST',
        name: 'Synthetic venue',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: 'test',
      },
    ],
  });
  vi.mocked(marketApiClient.listCurrencies).mockResolvedValue({
    items: [{ code: 'EUR', name: 'Euro', minor_unit: 2, reference_version: 'test' }],
  });
  vi.mocked(warrantApiClient.list).mockResolvedValue([other, target]);
  vi.mocked(warrantApiClient.terms).mockResolvedValue([]);
  vi.mocked(warrantApiClient.listings).mockResolvedValue([]);
});

describe('existing warrant administration from a blocked selection', () => {
  it('opens exactly the omitted product, not the first product in the catalogue', async () => {
    route();
    expect(await screen.findByRole('heading', { name: target.display_name })).toBeInTheDocument();
    await waitFor(() =>
      expect(warrantApiClient.listings).toHaveBeenCalledWith(target.id, expect.any(AbortSignal)),
    );
    expect(screen.queryByRole('button', { name: /Unrelated warrant/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Optionsschein anlegen' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zurück zur Produktauswahl' })).toHaveAttribute(
      'href',
      `/product-selection?run_id=${id(101)}`,
    );
    expect(screen.getByLabelText('Handelswährung')).toHaveValue('');
    expect(warrantApiClient.create).not.toHaveBeenCalled();
    expect(warrantApiClient.addListing).not.toHaveBeenCalled();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  });
  it('resolves the underlying from the saved run and preserves it for existing product creation', async () => {
    detail.universe_omissions = [];
    vi.mocked(warrantApiClient.list).mockResolvedValue([other]);
    route(`selection_run_id=${id(101)}&underlying_id=${other.underlying_id}`);
    const field = await screen.findByRole('combobox', { name: 'Basiswert *' });
    await waitFor(() => expect(field).toHaveValue(underlying.id));
    expect(field).toBeDisabled();
    expect(screen.getByRole('option', { name: underlying.name })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: other.display_name })).not.toBeInTheDocument();
  });
  it.each(['not-a-uuid', 'https://outside.invalid', ''])(
    'rejects malformed context %s without API calls or a wrong form',
    async (runId) => {
      route(`selection_run_id=${encodeURIComponent(runId)}`);
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Ungültiger Produktauswahl-Kontext',
      );
      expect(productSelectionApiClient.get).not.toHaveBeenCalled();
      expect(
        screen.queryByRole('button', { name: 'Optionsschein anlegen' }),
      ).not.toBeInTheDocument();
    },
  );
  it('rejects a product not present in the saved run', async () => {
    route(`selection_run_id=${id(101)}&warrant_id=${other.id}`);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Produkt gehört nicht zu diesem Bewertungslauf',
    );
    expect(warrantApiClient.list).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Notierung hinzufügen' })).not.toBeInTheDocument();
  });
  it('does not fall back to another product when the requested product is no longer present', async () => {
    vi.mocked(warrantApiClient.list).mockResolvedValue([other]);
    route();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Das angeforderte Produkt ist im passenden Basiswertkontext nicht verfügbar',
    );
    expect(warrantApiClient.listings).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Notierung hinzufügen' })).not.toBeInTheDocument();
  });
  it('retains the entered listing on a failed save, with no automatic evaluation', async () => {
    vi.mocked(warrantApiClient.addListing).mockRejectedValue(new Error('Speichern fehlgeschlagen'));
    route();
    const currency = await screen.findByLabelText('Handelswährung');
    fireEvent.change(screen.getByLabelText('Handelsplatz'), { target: { value: id(601) } });
    fireEvent.change(currency, { target: { value: 'USD' } });
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Speichern fehlgeschlagen');
    expect(currency).toHaveValue('USD');
    expect(warrantApiClient.addListing).toHaveBeenCalledTimes(1);
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: 'Zurück zur Produktauswahl' })).toBeInTheDocument();
  });
  it('reports a confirmed listing write separately from a failed refresh', async () => {
    vi.mocked(warrantApiClient.addListing).mockResolvedValue({
      id: id(701),
      warrant_id: target.id,
      workspace_id: target.workspace_id,
      trading_venue_id: id(601),
      symbol: null,
      quotation_currency_code: 'EUR',
      lifecycle_status: 'ACTIVE',
      version: 1,
      created_at: underlying.created_at,
      updated_at: underlying.updated_at,
    });
    route();
    await screen.findByLabelText('Handelswährung');
    await waitFor(() => expect(warrantApiClient.listings).toHaveBeenCalledTimes(1));
    vi.mocked(warrantApiClient.listings).mockRejectedValueOnce(new Error('Lesefehler'));
    fireEvent.change(screen.getByLabelText('Handelsplatz'), { target: { value: id(601) } });
    fireEvent.change(screen.getByLabelText('Handelswährung'), { target: { value: 'EUR' } });
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Notierung wurde gespeichert');
    expect(screen.getByRole('alert')).toHaveTextContent('Nicht erneut hinzufügen');
    expect(warrantApiClient.addListing).toHaveBeenCalledTimes(1);
    expect(productSelectionApiClient.select).not.toHaveBeenCalled();
  });
});

it('rejects a current product assignment that no longer matches the saved run', async () => {
  vi.mocked(warrantApiClient.list).mockResolvedValue([
    { ...target, underlying_id: other.underlying_id },
  ]);
  route();
  expect(await screen.findByRole('alert')).toHaveTextContent('nicht verfügbar');
  expect(warrantApiClient.listings).not.toHaveBeenCalled();
});
it('keeps a failed context read from exposing the ordinary first-product form', async () => {
  vi.mocked(productSelectionApiClient.get).mockRejectedValue(new Error('Lauf nicht verfügbar'));
  route();
  expect(await screen.findByRole('alert')).toHaveTextContent('Lauf nicht verfügbar');
  expect(warrantApiClient.list).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Optionsschein anlegen' })).not.toBeInTheDocument();
});
it('rejects a different run returned by a stale or inconsistent response', async () => {
  detail.run.id = id(999);
  route();
  expect(await screen.findByRole('alert')).toHaveTextContent('passt nicht zum Aufruf');
  expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
});
