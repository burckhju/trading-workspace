import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  topDownAdminClient,
  type ProviderMapping,
} from '../../administration/services/topDownAdminClient';
import { marketApiClient } from '../../market/services/client';
import { MarketTransportError } from '../../market/services/http';
import type {
  ListingResponse,
  UnderlyingDetailResponse,
  UnderlyingSearchResponse,
} from '../../market/types/api';
import { chartClient } from '../services/chartClient';
import { chartSetupClient } from '../services/chartSetupClient';
import type { ChartCatalog, ChartIdentity } from '../types/charts';
import { ChartSetupPage } from './ChartSetupPage';

vi.mock('../../administration/services/topDownAdminClient', () => ({
  topDownAdminClient: {
    references: vi.fn(),
    sectors: vi.fn(),
    mappings: vi.fn(),
    venueReconciliation: vi.fn(),
    createMapping: vi.fn(),
    validateMapping: vi.fn(),
    importHistory: vi.fn(),
  },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn(), searchUnderlyings: vi.fn() },
}));
vi.mock('../services/chartClient', () => ({
  chartClient: { catalog: vi.fn(), underlying: vi.fn(), clear: vi.fn(), series: vi.fn() },
}));
vi.mock('../services/chartSetupClient', () => ({
  chartSetupClient: { proposals: vi.fn(), write: vi.fn() },
}));

const admin = vi.mocked(topDownAdminClient);
const market = vi.mocked(marketApiClient);
const charts = vi.mocked(chartClient);
const setup = vi.mocked(chartSetupClient);
const route = (owner = 'u1') =>
  `/chart-setup?action=listingMapping&underlying_id=${owner}&listing_id=l${owner.slice(1)}`;
const timestamp = '2026-10-26T00:00:00Z';
function security(id: string): UnderlyingDetailResponse {
  const suffix = id.slice(1);
  const listing: ListingResponse = {
    id: `l${suffix}`,
    underlying_id: id,
    trading_venue_id: 'venue',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Xetra',
    ticker: `LOCAL${suffix}`,
    currency_code: 'EUR',
    lifecycle_status: 'ACTIVE',
    is_primary: true,
    version: 1,
    created_at: timestamp,
    updated_at: timestamp,
  };
  return {
    id,
    name: `Security ${suffix}`,
    type: 'STOCK',
    isin: `DE000TEST00${suffix}`,
    wkn: null,
    lifecycle_status: 'ACTIVE',
    quality_status: 'VERIFIED',
    version: 1,
    created_at: timestamp,
    updated_at: timestamp,
    primary_listing: null,
    listings: [listing],
  };
}
function providerMapping(owner = 'u1'): ProviderMapping {
  const suffix = owner.slice(1);
  return {
    id: `m${suffix}`,
    listing_id: `l${suffix}`,
    market_data_instrument_id: `i${suffix}`,
    workspace_id: 'workspace',
    provider: 'EODHD',
    status: 'ACTIVE',
    version: 3,
    provider_symbol: `STORED${suffix}`,
    provider_exchange_code: 'XETRA',
    validated_at: timestamp,
    validation_message: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
}
function identity(id: string): ChartIdentity {
  const value = security(id);
  const listing = value.listings[0];
  const mapping = providerMapping(id);
  return {
    key: `listing:${listing.id}`,
    name: value.name,
    instrument_id: mapping.market_data_instrument_id,
    instrument_type: 'STOCK',
    reference_id: null,
    reference_code: null,
    underlying_id: id,
    listing_id: listing.id,
    isin: value.isin,
    ticker: listing.ticker,
    mic: 'XETR',
    currency: 'EUR',
    return_basis: 'SECURITY',
    basis_source: null,
    active: true,
    mapping_status: mapping.status,
    provider_identity: `EODHD:${mapping.provider_symbol}.XETRA`,
    mapping_id: mapping.id,
    mapping_version: mapping.version,
    setup_url: route(id),
  };
}
const catalog: ChartCatalog = {
  references: [],
  sectors: [],
  proxies: [],
  as_of: '2026-10-26',
  taxonomy_status: 'EMPTY',
};
let mappings: ProviderMapping[];
function renderPage(initialEntries = [route()], initialIndex = 0) {
  const router = createMemoryRouter(
    [
      { path: '/chart-setup', element: <ChartSetupPage /> },
      { path: '/market-charts', element: <h1>Chart return</h1> },
      { path: '/candidates', element: <h1>Candidate return</h1> },
    ],
    { initialEntries, initialIndex },
  );
  render(<RouterProvider router={router} />);
  return router;
}
const symbolInput = () => screen.getByRole('textbox', { name: 'Geprüftes EODHD-Symbol' });
async function ready(symbol = 'STORED1') {
  await waitFor(() => expect(symbolInput()).toHaveValue(symbol));
}
const actionSelect = () => screen.getByRole('combobox', { name: 'Aktion' });

beforeEach(() => {
  vi.clearAllMocks();
  mappings = [providerMapping(), providerMapping('u2')];
  market.getUnderlying.mockImplementation((id) => Promise.resolve(security(id)));
  market.searchUnderlyings.mockResolvedValue({
    items: [security('u1'), security('u2')],
    total: 2,
    offset: 0,
    limit: 20,
  } satisfies UnderlyingSearchResponse);
  admin.mappings.mockImplementation(() => Promise.resolve(mappings));
  admin.references.mockResolvedValue([
    { id: 'r1', code: 'INDEX', name: 'Synthetic index', reference_type: 'INDEX', active: true },
  ]);
  admin.sectors.mockResolvedValue([{ id: 's1', code: 'TECH', name: 'Technology', active: true }]);
  admin.venueReconciliation.mockResolvedValue({
    status: 'MATCHED',
    listing_venue_id: 'venue',
    evidence_venue_ids: ['venue'],
    explanation: 'Synthetic exact venue match.',
  });
  admin.createMapping.mockImplementation((listingId, symbol, exchange) => {
    const old = mappings.find((item) => item.listing_id === listingId);
    if (!old) return Promise.reject(new Error('Missing synthetic mapping'));
    const next = {
      ...old,
      provider_symbol: symbol,
      provider_exchange_code: exchange,
      version: old.version + 1,
      status: 'DISABLED',
      validated_at: null,
    };
    mappings = mappings.map((item) => (item.id === next.id ? next : item));
    return Promise.resolve(next);
  });
  charts.catalog.mockResolvedValue(catalog);
  charts.underlying.mockImplementation((id) =>
    Promise.resolve({
      underlying_id: id,
      subject: identity(id),
      market: null,
      sector: null,
      issues: [],
      assignment_date: '2026-10-26',
    }),
  );
  setup.proposals.mockResolvedValue([
    {
      code: 'SUGGESTED',
      sector: 'Suggested technology',
      benchmark: 'Technology reference',
      ticker: 'ETF',
      isin: 'US000TEST001',
      source_url: 'https://example.test/sector',
      mic: 'XNAS',
      currency: 'USD',
      classification_system: 'SYNTHETIC',
      classification_version: '2026',
      reviewed_on: '2026-10-26',
      taxonomy_source: 'https://example.test/taxonomy',
      venue_source: 'https://example.test/venue',
      provider_coverage: 'UNVERIFIED',
    },
  ]);
  setup.write.mockResolvedValue({ id: 'synthetic-result' });
});

describe('ChartSetupPage real router navigation and draft ownership', () => {
  it('protects a query change, preserves draft on stay, and only replaces it after explicit discard', async () => {
    const router = renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'DRAFT1' } });
    await act(() => router.navigate(route('u2')));
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Ungespeicherte Änderungen');
    expect(within(dialog).getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    expect(symbolInput()).toHaveValue('DRAFT1');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
    expect(router.state.location.search).toContain('underlying_id=u1');
    expect(symbolInput()).toHaveValue('DRAFT1');
    await act(() => router.navigate(route('u2')));
    fireEvent.click(await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await ready('STORED2');
    expect(router.state.location.search).toContain('underlying_id=u2');
    expect(admin.createMapping).not.toHaveBeenCalled();
  });

  it('protects browser forward and back instead of losing a draft on POP navigation', async () => {
    const router = renderPage([route(), route('u2')]);
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'FORWARD-DRAFT' } });
    await act(() => router.navigate(1));
    await screen.findByRole('alertdialog');
    expect(symbolInput()).toHaveValue('FORWARD-DRAFT');
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await ready('STORED2');
    fireEvent.change(symbolInput(), { target: { value: 'BACK-DRAFT' } });
    await act(() => router.navigate(-1));
    await screen.findByRole('alertdialog');
    expect(symbolInput()).toHaveValue('BACK-DRAFT');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(router.state.location.search).toContain('underlying_id=u2');
    await act(() => router.navigate(-1));
    fireEvent.click(await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await ready();
  });

  it('ignores delayed reads after A→B→A even when the old A identity equals the current route', async () => {
    const pending: Array<{
      id: string;
      signal?: AbortSignal;
      complete: (value: UnderlyingDetailResponse) => void;
    }> = [];
    let initialReads = 0;
    market.getUnderlying.mockImplementation((id, signal) => {
      initialReads += 1;
      if (initialReads <= 2)
        return new Promise((complete) => {
          pending.push({ id, signal, complete });
        });
      return Promise.resolve(security(id));
    });
    const router = renderPage();
    await waitFor(() => expect(pending).toHaveLength(1));
    await act(() => router.navigate(route('u2')));
    await waitFor(() => expect(pending).toHaveLength(2));
    await act(() => router.navigate(route()));
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'LATEST-A-DRAFT' } });
    expect(pending.every((request) => request.signal?.aborted)).toBe(true);
    await act(async () => {
      pending[1].complete({ ...security('u2'), name: 'Old B read' });
      pending[0].complete({ ...security('u1'), name: 'Old A read' });
      await Promise.resolve();
    });
    expect(symbolInput()).toHaveValue('LATEST-A-DRAFT');
    expect(screen.queryByText('Old A read')).not.toBeInTheDocument();
    expect(screen.queryByText('Old B read')).not.toBeInTheDocument();
    expect(router.state.location.search).toContain('underlying_id=u1');
  });

  it('protects local action changes and restores focus when staying', async () => {
    renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'LOCAL-DRAFT' } });
    actionSelect().focus();
    fireEvent.change(actionSelect(), { target: { value: 'sector' } });
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Ungespeicherte Eingaben verwerfen?');
    expect(actionSelect()).toHaveValue('listingMapping');
    expect(symbolInput()).toHaveValue('LOCAL-DRAFT');
    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(actionSelect()).toHaveFocus();
    expect(symbolInput()).toHaveValue('LOCAL-DRAFT');
    fireEvent.change(actionSelect(), { target: { value: 'sector' } });
    fireEvent.click(
      await screen.findByRole('button', { name: 'Entwurf verwerfen und fortfahren' }),
    );
    await waitFor(() => expect(actionSelect()).toHaveValue('sector'));
    expect(
      screen.queryByRole('textbox', { name: 'Geprüftes EODHD-Symbol' }),
    ).not.toBeInTheDocument();
    expect(admin.createMapping).not.toHaveBeenCalled();
  });
});

describe('ChartSetupPage local context and synchronous mutation locks', () => {
  it('requires explicit discard before changing the source security locally', async () => {
    renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'SOURCE-DRAFT' } });
    const select = screen.getByRole('combobox', { name: 'Basiswert / ETF' });
    fireEvent.change(select, { target: { value: 'u2' } });
    await screen.findByRole('alertdialog');
    expect(symbolInput()).toHaveValue('SOURCE-DRAFT');
    expect(select).toHaveValue('u1');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(select).toHaveValue('u1');
    fireEvent.change(select, { target: { value: 'u2' } });
    fireEvent.click(
      await screen.findByRole('button', { name: 'Entwurf verwerfen und fortfahren' }),
    );
    await ready('STORED2');
    expect(select).toHaveValue('u2');
    expect(admin.createMapping).not.toHaveBeenCalled();
  });

  it('locks double submit synchronously and forbids context discard while the write is pending', async () => {
    let complete!: (value: ProviderMapping) => void;
    admin.createMapping.mockReturnValue(
      new Promise((resolve) => {
        complete = resolve;
      }),
    );
    const router = renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'CHANGED1' } });
    fireEvent.click(screen.getByRole('checkbox'));
    const submit = screen.getByRole('button', { name: 'Geprüften Schritt ausführen' });
    act(() => {
      fireEvent.click(submit);
      fireEvent.click(submit);
    });
    await waitFor(() => expect(admin.createMapping).toHaveBeenCalledTimes(1));
    expect(admin.createMapping).toHaveBeenCalledWith('l1', 'CHANGED1', 'XETRA');
    expect(actionSelect()).toBeDisabled();
    expect(symbolInput()).toBeDisabled();
    await act(() => router.navigate('/market-charts'));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(
      screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    await act(async () => {
      const current = {
        ...providerMapping(),
        provider_symbol: 'CHANGED1',
        version: 4,
        status: 'DISABLED',
        validated_at: null,
      };
      mappings = [current, providerMapping('u2')];
      complete(current);
      await Promise.resolve();
    });
    await screen.findByText(/Schritt gespeichert/);
    await waitFor(() => expect(actionSelect()).not.toBeDisabled());
    expect(admin.createMapping).toHaveBeenCalledTimes(1);
    expect(symbolInput()).toHaveValue('CHANGED1');
    expect(router.state.location.pathname).toBe('/chart-setup');
    expect(admin.validateMapping).not.toHaveBeenCalled();
    expect(admin.importHistory).not.toHaveBeenCalled();
  });
});

describe('ChartSetupPage readback and proposal draft continuity', () => {
  it('keeps the same editor and dirty values during same-context readback, resetting confirmation', async () => {
    renderPage();
    await ready();
    const field = symbolInput();
    fireEvent.change(field, { target: { value: 'UNSAVED-READBACK' } });
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('checkbox')).toBeChecked();
    const before = charts.catalog.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: 'Lesestand aktualisieren' }));
    await waitFor(() => expect(charts.catalog.mock.calls.length).toBeGreaterThan(before));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Lesestand aktualisieren' })).not.toBeDisabled(),
    );
    expect(symbolInput()).toBe(field);
    expect(field).toHaveValue('UNSAVED-READBACK');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(admin.createMapping).not.toHaveBeenCalled();
  });

  it('preserves draft when readback detects a new revision and requires reviewing that new basis', async () => {
    renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'KEEP-MY-DRAFT' } });
    fireEvent.click(screen.getByRole('checkbox'));
    mappings = [
      { ...providerMapping(), version: 4, provider_symbol: 'OTHER-TAB' },
      providerMapping('u2'),
    ];
    fireEvent.click(screen.getByRole('button', { name: 'Lesestand aktualisieren' }));
    const acknowledge = await screen.findByRole('button', {
      name: 'Aktuellen Stand prüfen und Entwurf beibehalten',
    });
    expect(symbolInput()).toHaveValue('KEEP-MY-DRAFT');
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' })).toBeDisabled();
    fireEvent.click(acknowledge);
    expect(symbolInput()).toHaveValue('KEEP-MY-DRAFT');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(admin.createMapping).not.toHaveBeenCalled();
  });

  it('loads proposals explicitly and never overwrites an open draft without discarding', async () => {
    const router = renderPage(['/chart-setup?action=sector']);
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Name' })).not.toBeDisabled());
    expect(setup.proposals).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), {
      target: { value: 'My unsaved sector' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sektor- und ETF-Vorschläge anzeigen' }));
    const prepare = await screen.findByRole('button', { name: 'Sektorformular vorbereiten' });
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('My unsaved sector');
    fireEvent.click(prepare);
    const dialog = await screen.findByRole('alertdialog');
    expect(dialog).toHaveTextContent('Ungespeicherte Eingaben verwerfen?');
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('My unsaved sector');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Hier bleiben' }));
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('My unsaved sector');
    fireEvent.click(prepare);
    fireEvent.click(
      await screen.findByRole('button', { name: 'Entwurf verwerfen und fortfahren' }),
    );
    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('Suggested technology'),
    );
    expect(screen.getByRole('textbox', { name: 'Code' })).toHaveValue('SUGGESTED');
    expect(screen.getByRole('textbox', { name: 'Klassifikationssystem' })).toHaveValue('SYNTHETIC');
    expect(setup.write).not.toHaveBeenCalled();
    expect(admin.createMapping).not.toHaveBeenCalled();
    await act(() => router.navigate('/market-charts'));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
  });

  it('cancel does not clear a mapping draft until explicit discard', async () => {
    renderPage();
    await ready();
    fireEvent.change(symbolInput(), { target: { value: 'CANCEL-ME' } });
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen / Eingaben zurücksetzen' }));
    await screen.findByRole('alertdialog');
    expect(symbolInput()).toHaveValue('CANCEL-ME');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(symbolInput()).toHaveValue('CANCEL-ME');
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen / Eingaben zurücksetzen' }));
    fireEvent.click(
      await screen.findByRole('button', { name: 'Entwurf verwerfen und fortfahren' }),
    );
    await ready();
    expect(admin.createMapping).not.toHaveBeenCalled();
  });
});

describe('ChartSetupPage initialization and uncertain request identities', () => {
  it('does not allow a local context transition to race the initial authoritative resolver', async () => {
    let finish!: (value: UnderlyingDetailResponse) => void;
    market.getUnderlying.mockImplementationOnce(
      () =>
        new Promise((complete) => {
          finish = complete;
        }),
    );
    renderPage();
    await waitFor(() => expect(market.getUnderlying).toHaveBeenCalled());
    expect(actionSelect()).toBeDisabled();
    expect(screen.getByRole('combobox', { name: 'Basiswert / ETF' })).toBeDisabled();
    await act(async () => {
      finish(security('u1'));
      await Promise.resolve();
    });
    await ready();
    expect(actionSelect()).not.toBeDisabled();
  });

  it('does not rebind an uncertain direct-index request from its shown mapping to a different mapping', async () => {
    const original: ProviderMapping = {
      ...providerMapping(),
      id: 'reference-map-1',
      listing_id: null,
      market_data_instrument_id: 'reference-instrument',
      provider_symbol: 'INDEX-OLD',
    };
    const originalIdentity: ChartIdentity = {
      ...identity('u1'),
      key: 'reference:r1',
      name: 'Synthetic index',
      reference_id: 'r1',
      reference_code: 'INDEX',
      instrument_id: 'reference-instrument',
      instrument_type: 'INDEX',
      underlying_id: null,
      listing_id: null,
      isin: null,
      ticker: null,
      mic: null,
      currency: null,
      return_basis: 'PRICE_INDEX',
      basis_source: 'https://example.test/index',
      mapping_id: original.id,
      mapping_version: original.version,
      setup_url: '/chart-setup?reference_id=r1',
    };
    mappings = [original];
    charts.catalog.mockResolvedValue({
      ...catalog,
      references: [
        { identity: originalIdentity, history: { count: 0, first_date: null, last_date: null } },
      ],
    });
    setup.write.mockImplementation(() => {
      const replacement = {
        ...original,
        id: 'reference-map-2',
        version: 7,
        provider_symbol: 'OTHER-MAPPING',
      };
      mappings = [replacement];
      charts.catalog.mockResolvedValue({
        ...catalog,
        references: [
          {
            identity: {
              ...originalIdentity,
              mapping_id: replacement.id,
              mapping_version: replacement.version,
              return_basis: 'UNKNOWN',
              basis_source: null,
            },
            history: { count: 0, first_date: null, last_date: null },
          },
        ],
      });
      return Promise.reject(new MarketTransportError('Synthetic connection closed after send'));
    });
    renderPage(['/chart-setup?action=referenceMapping&reference_id=r1']);
    await ready('INDEX-OLD');
    fireEvent.change(symbolInput(), { target: { value: 'INDEX-DRAFT' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' }));
    await screen.findByText(/Der Transportabschluss ist unbekannt/);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' })).not.toBeDisabled(),
    );
    expect(setup.write).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Gewählter Kontext')).toHaveTextContent(
      'Mapping-ID: reference-map-1',
    );
    expect(screen.getByLabelText('Gewählter Kontext')).not.toHaveTextContent('reference-map-2');
    expect(symbolInput()).toHaveValue('INDEX-DRAFT');
    expect(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' })).toBeDisabled();
  });
});

describe('ChartSetupPage return and acknowledged identity continuity', () => {
  it('keeps the exact candidate return even when the incoming setup identity is contradictory', () => {
    renderPage([
      '/chart-setup?action=VALIDATE_EODHD_MAPPING&candidate_id=c1&resource_id=m1&mapping_id=m2',
    ]);
    expect(screen.getByRole('alert')).toHaveTextContent('Widersprüchliche');
    expect(screen.getByRole('link')).toHaveAttribute('href', '/candidates?candidate=c1');
    expect(admin.createMapping).not.toHaveBeenCalled();
  });

  it('pins an acknowledged newly created index mapping before readback instead of adopting a different mapping', async () => {
    const baseIdentity: ChartIdentity = {
      ...identity('u1'),
      key: 'reference:r1',
      name: 'Synthetic index',
      reference_id: 'r1',
      reference_code: 'INDEX',
      instrument_id: null,
      instrument_type: 'INDEX',
      underlying_id: null,
      listing_id: null,
      isin: null,
      ticker: null,
      mic: null,
      currency: null,
      return_basis: 'UNKNOWN',
      basis_source: null,
      mapping_status: 'MISSING',
      provider_identity: null,
      mapping_id: null,
      mapping_version: null,
      setup_url: '/chart-setup?reference_id=r1',
    };
    mappings = [];
    charts.catalog.mockResolvedValue({
      ...catalog,
      references: [
        { identity: baseIdentity, history: { count: 0, first_date: null, last_date: null } },
      ],
    });
    setup.write.mockImplementation(() => {
      const created = {
        ...providerMapping(),
        id: 'created-map-1',
        listing_id: null,
        market_data_instrument_id: 'reference-instrument',
        version: 1,
        provider_symbol: 'NEWINDEX',
        status: 'DISABLED',
        validated_at: null,
      };
      const replacement = {
        ...created,
        id: 'foreign-map-2',
        provider_symbol: 'OTHERINDEX',
        version: 2,
      };
      mappings = [replacement];
      charts.catalog.mockResolvedValue({
        ...catalog,
        references: [
          {
            identity: {
              ...baseIdentity,
              instrument_id: 'reference-instrument',
              mapping_id: replacement.id,
              mapping_version: replacement.version,
              mapping_status: 'DISABLED',
            },
            history: { count: 0, first_date: null, last_date: null },
          },
        ],
      });
      return Promise.resolve(created);
    });
    renderPage(['/chart-setup?action=referenceMapping&reference_id=r1']);
    await ready('');
    await waitFor(() => expect(symbolInput()).not.toBeDisabled());
    fireEvent.change(symbolInput(), { target: { value: 'NEWINDEX' } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Geprüfter EODHD-Exchange-Code' }), {
      target: { value: 'XETRA' },
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' }));
    await screen.findByText(/Schritt gespeichert/);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Schreibauftrag ist abgeschlossen');
    expect(alert).toHaveTextContent(/Mapping-ID|Mapping/);
    expect(screen.getByLabelText('Gewählter Kontext')).not.toHaveTextContent('foreign-map-2');
    expect(setup.write).toHaveBeenCalledTimes(1);
  });
});
