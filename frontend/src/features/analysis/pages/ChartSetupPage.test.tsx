import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { chartCatalog, chartIdentity, chartSeries, comparison } from '../../../test/chartFixtures';
import {
  topDownAdminClient,
  type ProviderMapping,
  type VenueReconciliation,
} from '../../administration/services/topDownAdminClient';
import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import { chartClient } from '../services/chartClient';
import { chartSetupClient } from '../services/chartSetupClient';
import { ChartSetupPage } from './ChartSetupPage';

vi.mock('../services/chartClient', () => ({
  chartClient: { catalog: vi.fn(), underlying: vi.fn(), series: vi.fn(), clear: vi.fn() },
}));
vi.mock('../services/chartSetupClient', () => ({
  chartSetupClient: { proposals: vi.fn(), write: vi.fn() },
}));
vi.mock('../../administration/services/topDownAdminClient', () => ({
  topDownAdminClient: {
    references: vi.fn(),
    sectors: vi.fn(),
    mappings: vi.fn(),
    createMapping: vi.fn(),
    validateMapping: vi.fn(),
    venueReconciliation: vi.fn(),
    importHistory: vi.fn(),
  },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    getUnderlying: vi.fn(),
    searchUnderlyings: vi.fn(),
    searchProviderInstruments: vi.fn(),
  },
}));
vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { liveWorkflow: vi.fn(), evaluateAuto: vi.fn() },
}));

const now = '2026-10-26T10:00:00Z';
const today = () => new Date().toISOString().slice(0, 10);
function listing(id = 'secondary', primary = false): ListingResponse {
  return {
    id,
    underlying_id: 'stock',
    trading_venue_id: 'venue',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Synthetic Xetra',
    ticker: 'LOCAL',
    currency_code: 'EUR',
    lifecycle_status: 'ACTIVE',
    is_primary: primary,
    version: 1,
    created_at: now,
    updated_at: now,
  };
}
const underlying: UnderlyingDetailResponse = {
  id: 'stock',
  name: 'Synthetic ETF owner',
  type: 'ETF',
  isin: 'DE0000000001',
  wkn: null,
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: now,
  updated_at: now,
  primary_listing: null,
  listings: [listing('primary', true), listing()],
};
const references = [
  { id: 'sp500', name: 'Synthetic S&P 500', code: 'SP500', reference_type: 'INDEX', active: true },
  {
    id: 'sectorref',
    name: 'Synthetic Energy Reference',
    code: 'ENERGY',
    reference_type: 'SECTOR_INDEX',
    active: true,
  },
];
function mapping(patch: Partial<ProviderMapping> = {}): ProviderMapping {
  return {
    id: 'listing-mapping',
    workspace_id: 'workspace',
    listing_id: 'secondary',
    market_data_instrument_id: 'listing-instrument',
    provider: 'EODHD',
    provider_symbol: 'STORED_SYMBOL',
    provider_exchange_code: 'XETRA',
    status: 'ACTIVE',
    validated_at: now,
    validation_message: 'Synthetic validation',
    created_at: now,
    updated_at: now,
    version: 3,
    ...patch,
  };
}
let mappings: ProviderMapping[];
let catalog: ReturnType<typeof chartCatalog>;
let workflow: CandidateLiveWorkflow;
let venue: VenueReconciliation;
let validationVenue: VenueReconciliation['status'];

function updateMapping(id: string, patch: Partial<ProviderMapping>) {
  const existing = mappings.find((item) => item.id === id);
  if (!existing) throw new Error('Synthetic mapping missing');
  const value = { ...existing, ...patch, version: existing.version + 1 };
  mappings = mappings.map((item) => (item.id === id ? value : item));
  if (value.listing_id === null) {
    catalog = {
      ...catalog,
      references: catalog.references.map((entry) =>
        entry.identity.mapping_id === id
          ? {
              ...entry,
              identity: {
                ...entry.identity,
                mapping_version: value.version,
                mapping_status: value.status,
                return_basis: 'UNKNOWN',
                basis_source: null,
              },
            }
          : entry,
      ),
    };
  }
  return value;
}
beforeEach(() => {
  vi.resetAllMocks();
  mappings = [
    mapping(),
    mapping({
      id: 'm',
      listing_id: null,
      market_data_instrument_id: 'reference:sp500',
      provider_symbol: 'STORED_INDEX',
      provider_exchange_code: 'INDX',
      version: 1,
    }),
  ];
  catalog = chartCatalog();
  catalog.references[0].identity.provider_identity = 'DO_NOT_PARSE:WRONG.TEXT';
  catalog.references.push({
    identity: {
      ...chartIdentity('reference:sectorref'),
      name: 'Synthetic Energy Reference',
      instrument_type: 'SECTOR_INDEX',
      instrument_id: null,
      mapping_id: null,
      mapping_version: null,
      mapping_status: 'MISSING',
      return_basis: 'UNKNOWN',
      basis_source: null,
    },
    history: { count: 0, first_date: null, last_date: null },
  });
  venue = {
    status: 'MATCHED',
    listing_venue_id: 'venue',
    evidence_venue_ids: ['venue'],
    explanation: 'Synthetic venue evidence',
  };
  validationVenue = 'MATCHED';
  workflow = {
    candidate_id: 'candidate',
    underlying_id: 'candidate-stock',
    as_of: today(),
    ready: false,
    can_evaluate: false,
    next_action: 'UNRELATED_STEP',
    steps: [],
  };
  vi.mocked(chartClient.catalog).mockImplementation(() => Promise.resolve(catalog));
  vi.mocked(chartClient.underlying).mockImplementation((id) =>
    Promise.resolve({
      underlying_id: id,
      subject: null,
      market: null,
      sector: null,
      issues: [],
      assignment_date: today(),
    }),
  );
  vi.mocked(chartClient.series).mockResolvedValue(
    comparison([
      chartSeries({
        ...chartIdentity('listing:secondary', underlying.name, 'ETF'),
        underlying_id: 'stock',
        listing_id: 'secondary',
      }),
    ]),
  );
  vi.mocked(topDownAdminClient.references).mockResolvedValue(references);
  vi.mocked(topDownAdminClient.sectors).mockResolvedValue([
    { id: 'Energy', code: '10', name: 'Energy', active: true },
  ]);
  vi.mocked(topDownAdminClient.mappings).mockImplementation(() => Promise.resolve(mappings));
  vi.mocked(topDownAdminClient.venueReconciliation).mockImplementation(() =>
    Promise.resolve(venue),
  );
  vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
    Promise.resolve({
      ...underlying,
      id,
      listings: underlying.listings.map((item) => ({ ...item, underlying_id: id })),
    }),
  );
  vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
    items: [underlying],
    total: 1,
    offset: 0,
    limit: 20,
  });
  vi.mocked(candidateApiClient.liveWorkflow).mockImplementation(() => Promise.resolve(workflow));
  vi.mocked(chartSetupClient.proposals).mockResolvedValue([
    {
      code: '10',
      sector: 'Energy',
      benchmark: 'Energy Select Sector Index',
      ticker: 'XLE',
      isin: 'US81369Y5069',
      mic: 'ARCX',
      currency: 'USD',
      source_url: 'https://example.test/etf',
      classification_system: 'GICS',
      classification_version: 'v1',
      reviewed_on: '2026-10-04',
      taxonomy_source: 'https://example.test/gics',
      venue_source: 'https://example.test/mic',
      provider_coverage: 'NOT_VERIFIED',
    },
  ]);
  vi.mocked(topDownAdminClient.createMapping).mockImplementation((listingId, symbol, exchange) =>
    Promise.resolve(
      updateMapping(mappings.find((item) => item.listing_id === listingId)?.id ?? '', {
        provider_symbol: symbol.trim().toUpperCase(),
        provider_exchange_code: exchange.trim().toUpperCase(),
        status: 'DISABLED',
        validated_at: null,
        validation_message: 'Awaiting explicit validation',
      }),
    ),
  );
  vi.mocked(topDownAdminClient.validateMapping).mockImplementation((id) => {
    venue = { ...venue, status: validationVenue };
    return Promise.resolve(
      updateMapping(id, {
        status: validationVenue === 'CONFLICT' ? 'INVALID' : 'ACTIVE',
        validated_at: now,
      }),
    );
  });
  vi.mocked(topDownAdminClient.importHistory).mockImplementation(
    (listingId, mappingId, start, end) =>
      Promise.resolve({
        listing_id: listingId,
        mapping_id: mappingId,
        workspace_id: 'workspace',
        provider: 'EODHD',
        start_date: start,
        end_date: end,
        inserted: 2,
        updated: 0,
        unchanged: 0,
        processed: 2,
      }),
  );
  vi.mocked(chartSetupClient.write).mockImplementation((path, body) => {
    const data = (body ?? {}) as Record<string, unknown>;
    if (path === 'bootstrap-v1')
      return Promise.resolve(
        ['DAX', 'SP500', 'NASDAQ100'].map((code) => ({
          id: code,
          code,
          name: code,
          reference_type: 'INDEX',
          active: true,
        })),
      );
    if (path.endsWith('/provider-mapping/eodhd'))
      return Promise.resolve(
        updateMapping('m', {
          provider_symbol: String(data.provider_symbol).trim().toUpperCase(),
          provider_exchange_code: String(data.provider_exchange_code).trim().toUpperCase(),
          status: 'DISABLED',
          validated_at: null,
        }),
      );
    if (path.endsWith('/provider-mapping/eodhd/validate'))
      return Promise.resolve(updateMapping('m', { status: 'ACTIVE', validated_at: now }));
    if (path.endsWith('/series-basis'))
      return Promise.resolve({ id: 'basis-receipt', return_basis: data.return_basis });
    if (path.endsWith('/daily-prices/import'))
      return Promise.resolve({
        market_reference_id: 'sp500',
        market_data_instrument_id: 'reference:sp500',
        mapping_id: 'm',
        start_date: data.start_date,
        end_date: data.end_date,
        inserted: 1,
        updated: 0,
        unchanged: 0,
      });
    if (path.endsWith('-assignments'))
      return Promise.resolve({
        id: 'assignment-receipt',
        valid_from: data.valid_from,
        valid_to: data.valid_to,
        source: data.source,
        quality_status: data.quality_status,
        created_at: now,
      });
    return Promise.resolve({
      id: 'created',
      ...data,
      active: true,
      reference_type: 'SECTOR_INDEX',
      role: 'SECTOR_REFERENCE',
      created_at: now,
    });
  });
});

function show(search = '') {
  const router = createMemoryRouter(
    [
      { path: '/chart-setup', element: <ChartSetupPage /> },
      { path: '/candidates', element: <h1>Kandidatenrückkehr</h1> },
      { path: '/market-charts', element: <h1>Chartrückkehr</h1> },
      { path: '/underlyings/new', element: <h1>Stammdaten</h1> },
    ],
    { initialEntries: [`/chart-setup${search ? `?${search}` : ''}`] },
  );
  render(<RouterProvider router={router} />);
  return router;
}
async function loaded() {
  await waitFor(() =>
    expect(screen.queryByText('Der gespeicherte Kontext wird gelesen …')).not.toBeInTheDocument(),
  );
}
async function confirm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('checkbox'));
  await user.click(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' }));
}
function candidateSearch(action: string, ids: Record<string, string>) {
  workflow = {
    ...workflow,
    steps: [
      {
        code: 'repair-specific',
        label: 'Synthetic repair',
        status: 'BLOCKED',
        action,
        resource_id: null,
        action_params: ids,
        detail: 'Synthetic fixture',
      },
    ],
  };
  return new URLSearchParams({
    action,
    candidate_id: 'candidate',
    action_params: JSON.stringify(ids),
    ...ids,
  }).toString();
}

it('loads suggestions only on request, prepares without writing, and preserves explicit creation', async () => {
  const user = userEvent.setup();
  show();
  await loaded();
  expect(chartSetupClient.proposals).not.toHaveBeenCalled();
  expect(chartSetupClient.write).not.toHaveBeenCalled();
  expect(screen.getAllByRole('form')).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Sektor- und ETF-Vorschläge anzeigen' }));
  await user.click(await screen.findByRole('button', { name: 'Sektorformular vorbereiten' }));
  await loaded();
  expect(screen.getByLabelText('Klassifikationssystem')).toHaveValue('GICS');
  expect(chartSetupClient.write).not.toHaveBeenCalled();
  await confirm(user);
  expect(await screen.findByText(/Schritt gespeichert/)).toBeInTheDocument();
  expect(chartSetupClient.write).toHaveBeenCalledWith('sectors', {
    code: '10',
    name: 'Energy',
    classification_system: 'GICS',
    classification_version: 'v1',
  });
});

it('prefills exact nonprimary mapping fields and suppresses normalized unchanged PUTs', async () => {
  const user = userEvent.setup();
  show('action=listingMapping&underlying_id=stock&listing_id=secondary&mapping_id=listing-mapping');
  await loaded();
  expect(screen.getByLabelText('Eindeutige Notierung')).toHaveValue('secondary');
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('STORED_SYMBOL');
  expect(screen.getByLabelText('Geprüfter EODHD-Exchange-Code')).toHaveValue('XETRA');
  expect(screen.queryByText(/^Gelesene Providerkennung:/)).not.toBeInTheDocument();
  await user.clear(screen.getByLabelText('Geprüftes EODHD-Symbol'));
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), ' stored_symbol ');
  expect(screen.getByRole('checkbox')).toBeDisabled();
  fireEvent.submit(screen.getByRole('form'));
  expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
  expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();
});

it.each([
  ['listingValidate', 'underlying_id=stock&listing_id=secondary', 'STORED_SYMBOL', 'XETRA'],
  ['listingImport', 'underlying_id=stock&listing_id=secondary', 'STORED_SYMBOL', 'XETRA'],
  ['referenceValidate', 'reference_id=sp500', 'STORED_INDEX', 'INDX'],
  ['referenceImport', 'reference_id=sp500', 'STORED_INDEX', 'INDX'],
  ['basis', 'reference_id=sp500', 'STORED_INDEX', 'INDX'],
])(
  'shows the exact read provider identity before confirming %s',
  async (action, ids, symbol, exchange) => {
    show(`action=${action}&${ids}`);
    await loaded();
    expect(screen.getByText(/^Gelesene Providerkennung:/)).toHaveTextContent(
      `Gelesene Providerkennung: EODHD · Symbol: ${symbol} · Exchange-Code: ${exchange}`,
    );
    expect(screen.queryByLabelText('Geprüftes EODHD-Symbol')).not.toBeInTheDocument();
    expect(screen.queryByText(/DO_NOT_PARSE/)).not.toBeInTheDocument();
    expect(chartSetupClient.write).not.toHaveBeenCalled();
    expect(topDownAdminClient.validateMapping).not.toHaveBeenCalled();
    expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
  },
);

it('saves an explicitly changed mapping, reads its disabled revision and never chains validation/import', async () => {
  const user = userEvent.setup();
  show('action=listingMapping&underlying_id=stock&listing_id=secondary');
  await loaded();
  await user.clear(screen.getByLabelText('Geprüftes EODHD-Symbol'));
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), 'NEW_SYMBOL');
  expect(
    screen.getByText(/deaktiviert das Mapping und löscht die bisherige Validierung/),
  ).toBeInTheDocument();
  await confirm(user);
  await screen.findByText(/Mappingrevision: 4 · Technischer Mappingstatus: DISABLED/);
  expect(topDownAdminClient.createMapping).toHaveBeenCalledWith('secondary', 'NEW_SYMBOL', 'XETRA');
  expect(topDownAdminClient.validateMapping).not.toHaveBeenCalled();
  expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
});

it('pins a non-next candidate listing repair to the actual ETF owner distinct from the candidate', async () => {
  const user = userEvent.setup();
  const router = show(
    candidateSearch('CREATE_EODHD_MAPPING', { underlying_id: 'stock', listing_id: 'secondary' }),
  );
  await loaded();
  expect(screen.queryByLabelText('Aktion')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Basiswert / ETF')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Eindeutige Notierung')).not.toBeInTheDocument();
  expect(screen.getByText(/Listing-ID: secondary/)).toBeInTheDocument();
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), '2');
  await confirm(user);
  await screen.findByText(/Schritt gespeichert/);
  await loaded();
  expect(topDownAdminClient.createMapping).toHaveBeenCalledWith(
    'secondary',
    'STORED_SYMBOL2',
    'XETRA',
  );
  expect(candidateApiClient.evaluateAuto).not.toHaveBeenCalled();
  await user.click(screen.getByRole('link', { name: /Zurück zum Kandidaten/ }));
  expect(router.state.location.search).toBe('?candidate=candidate');
});

it.each([
  [
    'ASSIGN_BROAD_MARKET_BENCHMARK',
    { underlying_id: 'stock' },
    'Markt- / Sektor-Benchmark',
    'sp500',
    'underlyings/stock/benchmark-assignments',
    { market_reference_id: 'sp500', role: 'BROAD_MARKET' },
  ],
  [
    'ASSIGN_SECTOR',
    { underlying_id: 'stock' },
    'Administrierter Sektor',
    'Energy',
    'underlyings/stock/sector-assignments',
    { sector_id: 'Energy' },
  ],
  [
    'ASSIGN_SECTOR_REFERENCE',
    { sector_id: 'Energy' },
    'Geeignete Sektorreferenz',
    'sectorref',
    'sectors/Energy/reference-assignments',
    { market_reference_id: 'sectorref' },
  ],
] as const)(
  'uses candidate provenance and selects only the missing target for %s',
  async (action, ids, label, target, path, targetBody) => {
    const user = userEvent.setup();
    workflow.underlying_id = 'stock';
    show(candidateSearch(action, ids));
    await loaded();
    expect(screen.getByText('MANUAL_ADMIN')).toBeInTheDocument();
    expect(screen.queryByLabelText('Quellenbeleg (HTTPS)')).not.toBeInTheDocument();
    if (action === 'ASSIGN_SECTOR_REFERENCE')
      expect(screen.queryByRole('option', { name: /S&P 500/ })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(label), target);
    await loaded();
    expect(chartSetupClient.write).not.toHaveBeenCalled();
    await confirm(user);
    await screen.findByText(/Schritt gespeichert/);
    expect(chartSetupClient.write).toHaveBeenCalledWith(path, {
      valid_from: today(),
      valid_to: null,
      source: 'MANUAL_ADMIN',
      ...(action === 'ASSIGN_SECTOR_REFERENCE'
        ? {}
        : { source_reference: 'Candidate live workflow' }),
      quality_status: 'GOOD',
      ...targetBody,
    });
  },
);

it('lets a fixed reference choose an existing listing independently of the candidate owner', async () => {
  const user = userEvent.setup();
  show(candidateSearch('ASSIGN_REFERENCE_LISTING', { market_reference_id: 'sp500' }));
  await loaded();
  expect(screen.queryByLabelText('Markt- / Sektor-Benchmark')).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Basiswert / ETF'), 'stock');
  await loaded();
  await user.selectOptions(screen.getByLabelText('Eindeutige Notierung'), 'secondary');
  await loaded();
  await confirm(user);
  await screen.findByText(/Schritt gespeichert/);
  expect(chartSetupClient.write).toHaveBeenCalledWith(
    'market-references/sp500/listing-assignments',
    {
      valid_from: today(),
      valid_to: null,
      source: 'MANUAL_ADMIN',
      source_reference: 'Candidate live workflow',
      quality_status: 'GOOD',
      listing_id: 'secondary',
    },
  );
});

it('preserves chart validity and evidence; returns to the internally reconstructed chart context', async () => {
  const user = userEvent.setup();
  const chartContext =
    'underlying=stock&period=12&field=ADJUSTED_CLOSE&end=2026-10-20&target=listing%3Asecondary';
  const router = show(
    `action=stockSector&underlying_id=stock&sector_id=Energy&chart_context=${encodeURIComponent(chartContext)}`,
  );
  await loaded();
  await user.type(
    screen.getByLabelText('Quellenbeleg (HTTPS)'),
    'https://example.test/chart-source',
  );
  fireEvent.change(screen.getByLabelText('Zuordnung gültig ab'), {
    target: { value: '2026-09-15' },
  });
  await confirm(user);
  await screen.findByText(/Schritt gespeichert/);
  await loaded();
  expect(chartSetupClient.write).toHaveBeenCalledWith('underlyings/stock/sector-assignments', {
    valid_from: '2026-09-15',
    valid_to: null,
    source: 'CHART_SETUP',
    source_reference: 'https://example.test/chart-source',
    quality_status: 'GOOD',
    sector_id: 'Energy',
  });
  await user.click(screen.getByRole('link', { name: /Zurück zu den Diagrammen/ }));
  expect(router.state.location.pathname).toBe('/market-charts');
  expect(new URLSearchParams(router.state.location.search).get('period')).toBe('12');
  expect(new URLSearchParams(router.state.location.search).getAll('target')).toEqual([
    'listing:secondary',
  ]);
});

it.each(['MATCHED', 'CONFLICT', 'AMBIGUOUS', 'UNRESOLVED'] as const)(
  'keeps technical validation and %s venue evidence separate without automatic import',
  async (state) => {
    const user = userEvent.setup();
    validationVenue = state;
    show(
      'action=listingValidate&underlying_id=stock&listing_id=secondary&mapping_id=listing-mapping',
    );
    await loaded();
    await confirm(user);
    await screen.findByText(`Handelsplatzabgleich: ${state}`);
    await loaded();
    expect(topDownAdminClient.validateMapping).toHaveBeenCalledExactlyOnceWith('listing-mapping');
    expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
    expect(screen.getByText(/Mappingrevision: 4/)).toBeInTheDocument();
    if (state !== 'MATCHED')
      expect(
        screen.getByText(/Reparaturschritt ist nicht als eindeutig geklärt/),
      ).toBeInTheDocument();
  },
);

it('retries only GET after completed validation and a failed venue readback', async () => {
  const user = userEvent.setup();
  vi.mocked(topDownAdminClient.venueReconciliation)
    .mockResolvedValueOnce(venue)
    .mockResolvedValueOnce(venue)
    .mockRejectedValueOnce(new Error('Venue GET failed'))
    .mockResolvedValue(venue);
  show('action=listingValidate&underlying_id=stock&listing_id=secondary');
  await loaded();
  await confirm(user);
  await screen.findByText(/Der Schreibauftrag ist abgeschlossen; das Nachlesen ist gestört/);
  await loaded();
  await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
  await loaded();
  expect(screen.queryByText(/Venue GET failed/)).not.toBeInTheDocument();
  expect(topDownAdminClient.validateMapping).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' })).toBeDisabled();
});

it('preserves corrected inputs and a specific server conflict without claiming an unknown write', async () => {
  const user = userEvent.setup();
  vi.mocked(chartSetupClient.write).mockRejectedValueOnce(
    new MarketApiError(409, {
      code: 'HTTP_409',
      message: 'assignment overlaps with existing assignment',
      details: [],
      timestamp: now,
    }),
  );
  show('action=stockSector&underlying_id=stock&sector_id=Energy');
  await loaded();
  await user.type(screen.getByLabelText('Quellenbeleg (HTTPS)'), 'https://example.test/source');
  await confirm(user);
  await screen.findByText(/HTTP_409: assignment overlaps/);
  expect(screen.getByLabelText('Quellenbeleg (HTTPS)')).toHaveValue('https://example.test/source');
  expect(screen.queryByText(/Transportabschluss ist unbekannt/)).not.toBeInTheDocument();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});

it('reads after unknown transport but never treats matching state as its own receipt or replays PUT', async () => {
  const user = userEvent.setup();
  vi.mocked(topDownAdminClient.createMapping).mockImplementationOnce(() => {
    updateMapping('listing-mapping', {
      provider_symbol: 'STORED_SYMBOL2',
      status: 'DISABLED',
      validated_at: null,
    });
    return Promise.reject(new MarketTransportError('Connection lost'));
  });
  show('action=listingMapping&underlying_id=stock&listing_id=secondary');
  await loaded();
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), '2');
  await confirm(user);
  await screen.findByText(/Ein passender Wert beweist nicht den Abschluss dieses Requests/);
  await loaded();
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('STORED_SYMBOL2');
  expect(screen.getByText(/^Gelesene Providerkennung:/)).toHaveTextContent(
    'Gelesene Providerkennung: EODHD · Symbol: STORED_SYMBOL2 · Exchange-Code: XETRA',
  );
  await user.click(screen.getByRole('button', { name: 'Nur Lesestand erneut laden' }));
  await loaded();
  expect(topDownAdminClient.createMapping).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' })).toBeDisabled();
});

it('requires a new review of changed revision while preserving the intended symbol', async () => {
  const user = userEvent.setup();
  show('action=listingMapping&underlying_id=stock&listing_id=secondary');
  await loaded();
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), '_DRAFT');
  updateMapping('listing-mapping', {
    provider_symbol: 'OTHER_TAB',
    provider_exchange_code: 'OTHER_EXCHANGE',
  });
  await confirm(user);
  await screen.findByRole('button', { name: 'Aktuellen Stand prüfen und Entwurf beibehalten' });
  expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('STORED_SYMBOL_DRAFT');
  expect(screen.getByLabelText('Geprüfter EODHD-Exchange-Code')).toHaveValue('XETRA');
  expect(screen.getByText(/^Gelesene Providerkennung:/)).toHaveTextContent(
    'Gelesene Providerkennung: EODHD · Symbol: OTHER_TAB · Exchange-Code: OTHER_EXCHANGE',
  );
  expect(screen.getByText(/Dein Entwurf ist noch nicht gespeichert/)).toBeInTheDocument();
  await user.click(
    screen.getByRole('button', { name: 'Aktuellen Stand prüfen und Entwurf beibehalten' }),
  );
  await confirm(user);
  await screen.findByText(/Schritt gespeichert/);
  expect(topDownAdminClient.createMapping).toHaveBeenCalledTimes(1);
  expect(topDownAdminClient.createMapping).toHaveBeenCalledWith(
    'secondary',
    'STORED_SYMBOL_DRAFT',
    'XETRA',
  );
});

it('prefills direct index fields from the DTO without provider text parsing or a fabricated listing', async () => {
  const user = userEvent.setup();
  show('action=referenceMapping&reference_id=sp500&mapping_id=m');
  await loaded();
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('STORED_INDEX');
  expect(screen.getByLabelText('Geprüfter EODHD-Exchange-Code')).toHaveValue('INDX');
  expect(screen.queryByText(/^Gelesene Providerkennung:/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Basiswert / ETF')).not.toBeInTheDocument();
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), '2');
  await confirm(user);
  await screen.findByText(/Mappingrevision: 2/);
  expect(chartSetupClient.write).toHaveBeenCalledWith(
    'market-references/sp500/provider-mapping/eodhd',
    { provider_symbol: 'STORED_INDEX2', provider_exchange_code: 'INDX' },
    'PUT',
  );
  expect(
    await screen.findByText(/Renditegrundlage dieser Mappingrevision: UNKNOWN/),
  ).toBeInTheDocument();
});

it('drops old basis evidence after revalidation and requires a separate exact-revision confirmation', async () => {
  const user = userEvent.setup();
  show('action=referenceValidate&reference_id=sp500');
  await loaded();
  expect(
    screen.getByText(/Renditegrundlage dieser Mappingrevision: PRICE_INDEX/),
  ).toBeInTheDocument();
  await confirm(user);
  await screen.findByText(/Renditegrundlage dieser Mappingrevision: UNKNOWN/);
  await loaded();
  await user.selectOptions(screen.getByLabelText('Aktion'), 'basis');
  await loaded();
  await user.type(screen.getByLabelText('Quellenbeleg (HTTPS)'), 'https://example.test/new-basis');
  await confirm(user);
  await screen.findByText(/Schritt gespeichert/);
  expect(chartSetupClient.write).toHaveBeenLastCalledWith('market-references/sp500/series-basis', {
    mapping_id: 'm',
    mapping_version: 2,
    return_basis: 'PRICE_INDEX',
    source_url: 'https://example.test/new-basis',
    confirmed: true,
  });
});

it('rejects contradictory ownership or foreign mapping before any write', async () => {
  show('action=listingMapping&underlying_id=stock&listing_id=secondary&mapping_id=m');
  await loaded();
  expect(await screen.findByRole('alert')).toHaveTextContent(/Mapping-ID gehört nicht/);
  expect(screen.queryByLabelText('Geprüftes EODHD-Symbol')).not.toBeInTheDocument();
  expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
});

it('keeps a valid explicit listing-only URL and finds its owner through a stored chart read', async () => {
  show('listing_id=secondary');
  await loaded();
  expect(screen.getByLabelText('Eindeutige Notierung')).toHaveValue('secondary');
  expect(chartClient.series).toHaveBeenCalledWith(
    ['listing:secondary'],
    today(),
    today(),
    'CLOSE',
    expect.any(AbortSignal),
  );
  expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
});

it('rechecks the exact blocked workflow immediately before writing and keeps a stale draft', async () => {
  const user = userEvent.setup();
  show(
    candidateSearch('CREATE_EODHD_MAPPING', { underlying_id: 'stock', listing_id: 'secondary' }),
  );
  await loaded();
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), '2');
  workflow = { ...workflow, steps: [] };
  await confirm(user);
  await screen.findByText(
    /Dieser konkrete Schritt ist im aktuellen Kandidaten-Workflow nicht mehr blockiert/,
  );
  expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('STORED_SYMBOL2');
});

it('uses only local search when no existing underlying matches', async () => {
  const user = userEvent.setup();
  vi.mocked(marketApiClient.searchUnderlyings).mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 20,
  });
  show('action=stockSector');
  await loaded();
  await user.type(screen.getByLabelText('Basiswert suchen'), 'UNKNOWN');
  await user.click(screen.getByRole('button', { name: 'Suchen' }));
  await waitFor(() =>
    expect(marketApiClient.searchUnderlyings).toHaveBeenLastCalledWith(
      { query: 'UNKNOWN', lifecycleStatus: 'ACTIVE', offset: 0, limit: 20 },
      expect.any(AbortSignal),
    ),
  );
  expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();
  expect(chartSetupClient.write).not.toHaveBeenCalled();
});

it('shows only a locked state for unknown actions and preserves no second editor', () => {
  show('action=NOT_A_WORKFLOW_ACTION');
  expect(screen.getByRole('alert')).toHaveTextContent('Unbekannte Einrichtungsaktion');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
});

it('requires explicit import confirmation for the exact listing/mapping and selected dates', async () => {
  const user = userEvent.setup();
  show('action=listingImport&underlying_id=stock&listing_id=secondary&mapping_id=listing-mapping');
  await loaded();
  fireEvent.change(screen.getByLabelText('Import von'), { target: { value: '2026-08-01' } });
  fireEvent.change(screen.getByLabelText('Import bis'), { target: { value: '2026-08-31' } });
  expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
  await confirm(user);
  await screen.findByText(/Import abgeschlossen: 2 neu/);
  expect(topDownAdminClient.importHistory).toHaveBeenCalledExactlyOnceWith(
    'secondary',
    'listing-mapping',
    '2026-08-01',
    '2026-08-31',
  );
});

it('preserves inputs when the same-context read is delayed and does not remount the form', async () => {
  const user = userEvent.setup();
  show('action=listingMapping&underlying_id=stock&listing_id=secondary');
  await loaded();
  const input = screen.getByLabelText('Geprüftes EODHD-Symbol');
  await user.type(input, '2');
  let finish!: (value: ProviderMapping[]) => void;
  vi.mocked(topDownAdminClient.mappings).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await user.click(screen.getByRole('button', { name: 'Lesestand aktualisieren' }));
  expect(input).toHaveValue('STORED_SYMBOL2');
  await act(async () => {
    finish(mappings);
    await Promise.resolve();
  });
  await loaded();
  expect(within(screen.getByRole('form')).getByLabelText('Geprüftes EODHD-Symbol')).toBe(input);
  expect(input).toHaveValue('STORED_SYMBOL2');
});
