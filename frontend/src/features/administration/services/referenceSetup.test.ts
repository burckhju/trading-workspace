import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { chartCatalog, chartIdentity } from '../../../test/chartFixtures';
import { chartClient } from '../../analysis/services/chartClient';
import { chartSetupClient } from '../../analysis/services/chartSetupClient';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import {
  executeSetup,
  initialSetupDraft,
  readSetupSnapshot,
  selectionForAction,
  setupProblem,
  snapshotReviewKey,
  SetupValidationError,
  type SetupDraft,
  type SetupSelection,
  type SetupSnapshot,
} from './referenceSetup';
import {
  topDownAdminClient,
  type MarketReference,
  type ProviderMapping,
  type Sector,
  type VenueReconciliation,
} from './topDownAdminClient';

vi.mock('../../analysis/services/chartClient', () => ({
  chartClient: { catalog: vi.fn(), underlying: vi.fn(), clear: vi.fn() },
}));
vi.mock('../../analysis/services/chartSetupClient', () => ({
  chartSetupClient: { write: vi.fn(), proposals: vi.fn() },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn() },
}));
vi.mock('./topDownAdminClient', () => ({
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

const listing = (overrides: Partial<ListingResponse> = {}): ListingResponse => ({
  id: 'secondary',
  underlying_id: 'actual-owner',
  trading_venue_id: 'venue',
  trading_venue_mic: 'XETR',
  trading_venue_name: 'Test venue',
  ticker: 'TEST',
  currency_code: 'EUR',
  lifecycle_status: 'ACTIVE',
  is_primary: false,
  version: 1,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
  ...overrides,
});
const underlying = (): UnderlyingDetailResponse => ({
  id: 'actual-owner',
  type: 'ETF',
  name: 'Synthetic reference ETF',
  isin: 'DE0000000001',
  wkn: null,
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
  primary_listing: null,
  listings: [listing({ id: 'primary', is_primary: true }), listing()],
});
const reference: MarketReference = {
  id: 'sp500',
  code: 'SP500',
  name: 'Synthetic S&P 500',
  reference_type: 'INDEX',
  active: true,
};
const sectorReference: MarketReference = {
  id: 'energy-reference',
  code: 'ENERGY',
  name: 'Synthetic Energy Index',
  reference_type: 'SECTOR_INDEX',
  active: true,
};
const sector: Sector = { id: 'Energy', code: '10', name: 'Energy', active: true };
const mapping = (overrides: Partial<ProviderMapping> = {}): ProviderMapping => ({
  id: 'listing-mapping',
  workspace_id: 'workspace',
  listing_id: 'secondary',
  market_data_instrument_id: 'listing-instrument',
  provider: 'EODHD',
  provider_symbol: 'TEST',
  provider_exchange_code: 'XETRA',
  status: 'ACTIVE',
  validated_at: '2026-10-25T12:00:00Z',
  validation_message: 'Technically validated',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-25T12:00:00Z',
  version: 3,
  ...overrides,
});
const directMapping = () =>
  mapping({
    id: 'm',
    listing_id: null,
    market_data_instrument_id: 'reference:sp500',
    version: 1,
    provider_exchange_code: 'INDX',
  });
const venue: VenueReconciliation = {
  status: 'MATCHED',
  listing_venue_id: 'venue',
  evidence_venue_ids: ['venue'],
  explanation: 'Synthetic matched evidence',
};
const selection = (overrides: Partial<SetupSelection> = {}): SetupSelection => ({
  action: 'stockSector',
  underlyingId: 'actual-owner',
  listingId: '',
  referenceId: '',
  sectorId: 'Energy',
  mappingId: '',
  ...overrides,
});
const draft = (): SetupDraft => ({
  code: 'ENERGY',
  name: 'Synthetic Energy',
  system: 'GICS',
  version: 'test-v1',
  region: 'DE',
  symbol: 'CHANGED',
  exchange: 'XETRA',
  source: 'https://example.test/assignment',
  basis: 'PRICE_INDEX',
  start: '2026-10-26',
  end: '2026-10-26',
});
const snapshot = (overrides: Partial<SetupSnapshot> = {}): SetupSnapshot => ({
  catalog: chartCatalog(),
  references: [reference, sectorReference],
  sectors: [sector],
  underlying: underlying(),
  listing: listing(),
  reference,
  sector,
  identity: chartIdentity(),
  mapping: mapping(),
  venue,
  venueError: '',
  chartContext: {
    underlying_id: 'actual-owner',
    subject: null,
    market: null,
    sector: null,
    issues: [],
    assignment_date: '2026-10-26',
  },
  ...overrides,
});
const directSelection = (action: SetupSelection['action']): SetupSelection =>
  selection({ action, underlyingId: '', sectorId: '', referenceId: 'sp500' });
const listingSelection = (action: SetupSelection['action']): SetupSelection =>
  selection({ action, sectorId: '', listingId: 'secondary', mappingId: 'listing-mapping' });

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-10-26T12:00:00Z'));
  vi.mocked(chartClient.catalog).mockResolvedValue(chartCatalog());
  vi.mocked(chartClient.underlying).mockResolvedValue(snapshot().chartContext!);
  vi.mocked(topDownAdminClient.references).mockResolvedValue([reference, sectorReference]);
  vi.mocked(topDownAdminClient.sectors).mockResolvedValue([sector]);
  vi.mocked(topDownAdminClient.mappings).mockResolvedValue([mapping(), directMapping()]);
  vi.mocked(topDownAdminClient.venueReconciliation).mockResolvedValue(venue);
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(underlying());
  vi.mocked(chartSetupClient.write).mockResolvedValue({ id: 'written' });
  vi.mocked(topDownAdminClient.createMapping).mockResolvedValue(
    mapping({ status: 'DISABLED', version: 4 }),
  );
  vi.mocked(topDownAdminClient.validateMapping).mockResolvedValue(mapping({ version: 4 }));
  vi.mocked(topDownAdminClient.importHistory).mockResolvedValue({
    inserted: 1,
    updated: 0,
    unchanged: 0,
  });
});
afterEach(() => vi.useRealTimers());

describe('explicit writes and provenance', () => {
  it.each([false, true])(
    'preserves all four assignment payloads (candidate=%s)',
    async (candidate) => {
      const values = { ...draft(), start: candidate ? '2026-10-26' : '2024-07-15' };
      const evidence = {
        valid_from: values.start,
        valid_to: null,
        source: candidate ? 'MANUAL_ADMIN' : 'CHART_SETUP',
        source_reference: candidate ? 'Candidate live workflow' : values.source,
        quality_status: 'GOOD',
      };
      await executeSetup(
        selection({ action: 'stockMarket', referenceId: 'sp500' }),
        snapshot(),
        values,
        candidate,
      );
      await executeSetup(selection(), snapshot(), values, candidate);
      await executeSetup(
        selection({ action: 'sectorReference', underlyingId: '', referenceId: 'energy-reference' }),
        snapshot({ reference: sectorReference }),
        values,
        candidate,
      );
      await executeSetup(
        selection({ action: 'proxy', referenceId: 'sp500', listingId: 'secondary' }),
        snapshot(),
        values,
        candidate,
      );
      expect(vi.mocked(chartSetupClient.write).mock.calls).toEqual([
        [
          'underlyings/actual-owner/benchmark-assignments',
          { ...evidence, market_reference_id: 'sp500', role: 'BROAD_MARKET' },
        ],
        ['underlyings/actual-owner/sector-assignments', { ...evidence, sector_id: 'Energy' }],
        [
          'sectors/Energy/reference-assignments',
          {
            valid_from: values.start,
            valid_to: null,
            source: evidence.source,
            quality_status: 'GOOD',
            market_reference_id: 'energy-reference',
          },
        ],
        ['market-references/sp500/listing-assignments', { ...evidence, listing_id: 'secondary' }],
      ]);
      expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
    },
  );

  it('does not silently alter the visible candidate date if UTC day changed', async () => {
    await expect(
      executeSetup(selection(), snapshot(), { ...draft(), start: '2026-10-25' }, true),
    ).rejects.toThrow(/Tagesbezug/);
    expect(chartSetupClient.write).not.toHaveBeenCalled();
  });

  it('identifies all local prerequisite failures as known no-write outcomes', async () => {
    await expect(
      executeSetup(selection(), snapshot(), { ...draft(), source: '' }, false),
    ).rejects.toBeInstanceOf(SetupValidationError);
    await expect(
      executeSetup(selection({ action: 'sector' }), snapshot(), { ...draft(), name: ' ' }, false),
    ).rejects.toBeInstanceOf(SetupValidationError);
    await expect(
      executeSetup(
        directSelection('basis'),
        snapshot({ mapping: directMapping() }),
        { ...draft(), source: 'https://secret@example.test/evidence' },
        false,
      ),
    ).rejects.toBeInstanceOf(SetupValidationError);
    await expect(
      executeSetup(
        directSelection('basis'),
        snapshot({ mapping: { ...directMapping(), version: 2 } }),
        draft(),
        false,
      ),
    ).rejects.toBeInstanceOf(SetupValidationError);
    expect(chartSetupClient.write).not.toHaveBeenCalled();
    expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
  });

  it('retains bootstrap and creation contracts without update APIs', async () => {
    await executeSetup(selection({ action: 'bootstrap' }), snapshot(), draft(), false);
    await executeSetup(selection({ action: 'sector' }), snapshot(), draft(), false);
    await executeSetup(selection({ action: 'reference' }), snapshot(), draft(), false);
    expect(vi.mocked(chartSetupClient.write).mock.calls).toEqual([
      ['bootstrap-v1'],
      [
        'sectors',
        {
          code: 'ENERGY',
          name: 'Synthetic Energy',
          classification_system: 'GICS',
          classification_version: 'test-v1',
        },
      ],
      [
        'sector-references',
        { code: 'ENERGY', name: 'Synthetic Energy', region: 'DE', reference_version: 'test-v1' },
      ],
    ]);
  });

  it('uses listing owner and mapping ID without running a readback or chained action', async () => {
    await executeSetup(listingSelection('listingMapping'), snapshot(), draft(), true);
    expect(topDownAdminClient.createMapping).toHaveBeenCalledWith('secondary', 'CHANGED', 'XETRA');
    expect(topDownAdminClient.validateMapping).not.toHaveBeenCalled();
    expect(topDownAdminClient.venueReconciliation).not.toHaveBeenCalled();
    await executeSetup(listingSelection('listingValidate'), snapshot(), draft(), true);
    expect(topDownAdminClient.validateMapping).toHaveBeenCalledWith('listing-mapping');
    expect(topDownAdminClient.venueReconciliation).not.toHaveBeenCalled();
    expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
    await executeSetup(
      listingSelection('listingImport'),
      snapshot(),
      { ...draft(), start: '2026-09-01' },
      true,
    );
    expect(topDownAdminClient.importHistory).toHaveBeenCalledWith(
      'secondary',
      'listing-mapping',
      '2026-09-01',
      '2026-10-26',
    );
  });

  it('sends direct-index commands without fabricating listing identities and pins basis revision', async () => {
    const direct = snapshot({
      underlying: null,
      listing: null,
      mapping: directMapping(),
      venue: null,
    });
    await executeSetup(directSelection('referenceMapping'), direct, draft(), false);
    await executeSetup(directSelection('referenceValidate'), direct, draft(), false);
    await executeSetup(directSelection('referenceImport'), direct, draft(), false);
    await executeSetup(directSelection('basis'), direct, draft(), false);
    expect(vi.mocked(chartSetupClient.write).mock.calls).toEqual([
      [
        'market-references/sp500/provider-mapping/eodhd',
        { provider_symbol: 'CHANGED', provider_exchange_code: 'XETRA' },
        'PUT',
      ],
      ['market-references/sp500/provider-mapping/eodhd/validate'],
      [
        'market-references/sp500/daily-prices/import',
        { start_date: '2026-10-26', end_date: '2026-10-26' },
      ],
      [
        'market-references/sp500/series-basis',
        {
          mapping_id: 'm',
          mapping_version: 1,
          return_basis: 'PRICE_INDEX',
          source_url: 'https://example.test/assignment',
          confirmed: true,
        },
      ],
    ]);
    expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
  });

  it('blocks normalized unchanged PUTs and mismatched snapshots behind the form', async () => {
    await expect(
      executeSetup(
        listingSelection('listingMapping'),
        snapshot(),
        { ...draft(), symbol: ' test ', exchange: ' xetra ' },
        false,
      ),
    ).rejects.toThrow(/unverändert/);
    await expect(
      executeSetup(
        listingSelection('listingMapping'),
        snapshot({ listing: listing({ id: 'primary' }) }),
        draft(),
        false,
      ),
    ).rejects.toThrow(/Eingabekontext/);
    await expect(
      executeSetup(
        selection(),
        snapshot({ underlying: { ...underlying(), id: 'other' } }),
        draft(),
        false,
      ),
    ).rejects.toThrow(/Eingabekontext/);
    await expect(
      executeSetup(
        directSelection('basis'),
        snapshot({ mapping: directMapping(), reference: sectorReference }),
        draft(),
        false,
      ),
    ).rejects.toThrow(/Eingabekontext/);
    expect(topDownAdminClient.createMapping).not.toHaveBeenCalled();
    expect(chartSetupClient.write).not.toHaveBeenCalled();
  });

  it('preserves the original backend conflict and unknown transport outcome without retry', async () => {
    const conflict = new MarketApiError(409, {
      code: 'HTTP_409',
      message: 'assignment overlap',
      details: [],
      timestamp: '2026-10-26T12:00:00Z',
    });
    vi.mocked(chartSetupClient.write).mockRejectedValueOnce(conflict);
    await expect(executeSetup(selection(), snapshot(), draft(), false)).rejects.toBe(conflict);
    const unknown = new MarketTransportError('connection lost after PUT');
    vi.mocked(topDownAdminClient.createMapping).mockRejectedValueOnce(unknown);
    await expect(
      executeSetup(listingSelection('listingMapping'), snapshot(), draft(), false),
    ).rejects.toBe(unknown);
    expect(topDownAdminClient.createMapping).toHaveBeenCalledTimes(1);
    expect(chartSetupClient.write).toHaveBeenCalledTimes(1);
    expect(topDownAdminClient.mappings).not.toHaveBeenCalled();
  });
});

describe('authoritative snapshot reads', () => {
  it('retains explicit nonprimary listing and forwards one abort identity to GETs only', async () => {
    const signal = new AbortController().signal;
    const value = await readSetupSnapshot(listingSelection('listingMapping'), signal);
    expect(value.listing?.id).toBe('secondary');
    expect(value.underlying?.id).toBe('actual-owner');
    expect(value.mapping?.id).toBe('listing-mapping');
    expect(marketApiClient.getUnderlying).toHaveBeenCalledWith('actual-owner', signal);
    expect(chartClient.catalog).toHaveBeenCalledWith('2026-10-26', signal);
    expect(chartClient.underlying).toHaveBeenCalledWith('actual-owner', '2026-10-26', signal);
    expect(topDownAdminClient.mappings).toHaveBeenCalledWith(signal);
    expect(topDownAdminClient.venueReconciliation).toHaveBeenCalledWith('listing-mapping', signal);
    expect(chartSetupClient.write).not.toHaveBeenCalled();
    expect(chartSetupClient.proposals).not.toHaveBeenCalled();
    expect(topDownAdminClient.validateMapping).not.toHaveBeenCalled();
    expect(topDownAdminClient.importHistory).not.toHaveBeenCalled();
  });

  it('retains an explicit secondary even when only the primary has a mapping', async () => {
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([
      mapping({ id: 'primary-mapping', listing_id: 'primary' }),
    ]);
    const value = await readSetupSnapshot({ ...listingSelection('listingMapping'), mappingId: '' });
    expect(value.listing?.id).toBe('secondary');
    expect(value.mapping).toBeNull();
  });

  it('chooses the primary without a pinned mapping and rejects multiple primary candidates', async () => {
    const selected = listingSelection('listingMapping');
    selected.listingId = '';
    selected.mappingId = '';
    const value = await readSetupSnapshot(selected);
    expect(value.listing?.id).toBe('primary');
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue({
      ...underlying(),
      listings: [
        listing({ id: 'one', is_primary: true }),
        listing({ id: 'two', is_primary: true }),
      ],
    });
    await expect(readSetupSnapshot(selected)).rejects.toThrow(/Mehrere Primary/);
  });

  it('reads assignments without unrelated provider mappings or venue operations', async () => {
    await readSetupSnapshot(selection());
    expect(topDownAdminClient.mappings).not.toHaveBeenCalled();
    expect(topDownAdminClient.venueReconciliation).not.toHaveBeenCalled();
  });

  it.each([
    { listingId: 'foreign' },
    { mappingId: 'm' },
    { referenceId: 'missing' },
    { sectorId: 'missing' },
  ])('blocks foreign or missing selected identities %j', async (conflict) => {
    await expect(
      readSetupSnapshot({ ...listingSelection('listingValidate'), ...conflict }),
    ).rejects.toThrow();
    expect(topDownAdminClient.validateMapping).not.toHaveBeenCalled();
  });

  it('blocks wrong master-data and chart ownership independently', async () => {
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValueOnce({
      ...underlying(),
      id: 'candidate-owner',
    });
    await expect(readSetupSnapshot(listingSelection('listingMapping'))).rejects.toThrow(
      /Basiswert gehört nicht/,
    );
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValueOnce({
      ...underlying(),
      listings: [listing({ underlying_id: 'candidate-owner' })],
    });
    await expect(readSetupSnapshot(listingSelection('listingMapping'))).rejects.toThrow(
      /gehören nicht zusammen/,
    );
    vi.mocked(chartClient.underlying).mockResolvedValueOnce({
      ...snapshot().chartContext!,
      underlying_id: 'other',
    });
    await expect(readSetupSnapshot(listingSelection('listingMapping'))).rejects.toThrow(
      /Chart-Lesestand/,
    );
  });

  it('keeps a successful validation receipt distinct from a failing venue readback', async () => {
    const written = await executeSetup(
      listingSelection('listingValidate'),
      snapshot(),
      draft(),
      false,
    );
    expect(written).toMatchObject({ id: 'listing-mapping', version: 4 });
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([mapping({ version: 4 })]);
    vi.mocked(topDownAdminClient.venueReconciliation).mockRejectedValueOnce(
      new Error('Venue GET unavailable'),
    );
    const readback = await readSetupSnapshot(listingSelection('listingValidate'));
    expect(readback.mapping?.version).toBe(4);
    expect(readback.venue).toBeNull();
    expect(readback.venueError).toBe('Venue GET unavailable');
    await readSetupSnapshot(listingSelection('listingValidate'));
    expect(topDownAdminClient.validateMapping).toHaveBeenCalledTimes(1);
  });

  it('does not swallow a cancelled venue read as reusable context', async () => {
    const controller = new AbortController();
    const cancellation = new DOMException('left context', 'AbortError');
    vi.mocked(topDownAdminClient.venueReconciliation).mockImplementationOnce(() => {
      controller.abort();
      return Promise.reject(cancellation);
    });
    await expect(
      readSetupSnapshot(listingSelection('listingValidate'), controller.signal),
    ).rejects.toBe(cancellation);
  });

  it('rejects a contradictory venue readback without turning the write into a failure', async () => {
    await executeSetup(listingSelection('listingValidate'), snapshot(), draft(), false);
    vi.mocked(topDownAdminClient.venueReconciliation).mockResolvedValueOnce({
      ...venue,
      listing_venue_id: 'changed-in-other-tab',
    });
    const value = await readSetupSnapshot(listingSelection('listingValidate'));
    expect(value.venue).toBeNull();
    expect(value.venueError).toMatch(/passt nicht/);
    expect(setupProblem(listingSelection('listingImport'), value, draft())).toMatch(
      /eindeutig abgeglichen/,
    );
    expect(topDownAdminClient.validateMapping).toHaveBeenCalledTimes(1);
  });

  it('retains a legitimate unresolved venue and rejects an incomplete matched response', async () => {
    vi.mocked(topDownAdminClient.venueReconciliation).mockResolvedValueOnce({
      ...venue,
      status: 'UNRESOLVED',
      listing_venue_id: null,
      evidence_venue_ids: [],
    });
    expect((await readSetupSnapshot(listingSelection('listingValidate'))).venue?.status).toBe(
      'UNRESOLVED',
    );
    vi.mocked(topDownAdminClient.venueReconciliation).mockResolvedValueOnce({
      ...venue,
      status: 'MATCHED',
      listing_venue_id: null,
    });
    expect((await readSetupSnapshot(listingSelection('listingValidate'))).venueError).toMatch(
      /passt nicht/,
    );
  });

  it('reads the direct reference chain and blocks a stale catalogue revision', async () => {
    const result = await readSetupSnapshot(directSelection('basis'));
    expect(result.mapping?.listing_id).toBeNull();
    expect(result.mapping?.id).toBe('m');
    expect(topDownAdminClient.venueReconciliation).not.toHaveBeenCalled();
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([{ ...directMapping(), version: 2 }]);
    await expect(readSetupSnapshot(directSelection('basis'))).rejects.toThrow(
      /stimmen nicht überein/,
    );
    vi.mocked(chartClient.catalog).mockResolvedValue({ ...chartCatalog(), references: [] });
    await expect(readSetupSnapshot(directSelection('basis'))).rejects.toThrow(/Chartkatalog/);
  });
});

describe('review prerequisites and context boundaries', () => {
  it.each<VenueReconciliation['status']>(['CONFLICT', 'AMBIGUOUS', 'UNRESOLVED'])(
    'blocks import for %s even with a technically active mapping',
    (status) =>
      expect(
        setupProblem(
          listingSelection('listingImport'),
          snapshot({ venue: { ...venue, status } }),
          draft(),
        ),
      ).toMatch(/eindeutig abgeglichen/),
  );

  it('requires a valid assignment start and valid explicit import range', () => {
    for (const start of ['', 'not-a-date', '2026-02-30']) {
      expect(setupProblem(selection(), snapshot(), { ...draft(), start })).toMatch(
        /Gültigkeitsbeginn/,
      );
    }
    expect(
      setupProblem(listingSelection('listingImport'), snapshot(), {
        ...draft(),
        start: '2026-10-27',
      }),
    ).toMatch(/Importzeitraum/);
    expect(
      setupProblem(listingSelection('listingImport'), snapshot(), { ...draft(), end: 'invalid' }),
    ).toMatch(/Importzeitraum/);
  });

  it('retains explicit active-object, sector-reference and mapping prerequisites', () => {
    expect(setupProblem(selection(), snapshot({ underlying: null }), draft())).toMatch(/Basiswert/);
    expect(setupProblem(selection(), snapshot({ sector: null }), draft())).toMatch(/Sektor/);
    expect(
      setupProblem(listingSelection('listingMapping'), snapshot({ listing: null }), draft()),
    ).toMatch(/Notierung/);
    expect(
      setupProblem(directSelection('referenceMapping'), snapshot({ reference: null }), draft()),
    ).toMatch(/Referenz/);
    expect(
      setupProblem(selection(), snapshot({ sector: { ...sector, active: false } }), draft()),
    ).toMatch(/inaktiv/);
    expect(
      setupProblem(
        selection({ action: 'sectorReference', referenceId: 'sp500' }),
        snapshot(),
        draft(),
      ),
    ).toMatch(/Sektorreferenz/);
    expect(
      setupProblem(listingSelection('listingValidate'), snapshot({ mapping: null }), draft()),
    ).toMatch(/EODHD-Mapping/);
    expect(
      setupProblem(
        listingSelection('listingImport'),
        snapshot({ mapping: mapping({ status: 'DISABLED' }) }),
        draft(),
      ),
    ).toMatch(/aktiviert/);
    expect(
      setupProblem(listingSelection('listingMapping'), snapshot(), { ...draft(), symbol: ' ' }),
    ).toMatch(/Symbol/);
  });

  it('requires actual creation fields and the backend-supported index evidence', () => {
    expect(
      setupProblem(selection({ action: 'sector' }), snapshot(), { ...draft(), system: '' }),
    ).toMatch(/Klassifikationssystem/);
    expect(
      setupProblem(selection({ action: 'reference' }), snapshot(), { ...draft(), region: '' }),
    ).toMatch(/Region/);
    expect(setupProblem(directSelection('basis'), snapshot(), draft())).toMatch(/INDX/);
    const direct = snapshot({ mapping: directMapping() });
    expect(
      setupProblem(directSelection('basis'), direct, { ...draft(), basis: 'ETF_PRICE' }),
    ).toMatch(/unterstützte/);
    for (const source of [
      'invalid',
      'http://example.test/proof',
      'https://user:password@example.test/proof',
    ]) {
      expect(setupProblem(directSelection('basis'), direct, { ...draft(), source })).toMatch(
        /HTTPS-Quellenadresse/,
      );
    }
  });

  it('changes the review key for mapping revision, basis, venue and source identity changes', () => {
    const key = snapshotReviewKey(snapshot());
    for (const changed of [
      snapshot({ mapping: mapping({ version: 4 }) }),
      snapshot({ identity: { ...chartIdentity(), return_basis: 'UNKNOWN', basis_source: null } }),
      snapshot({ venue: { ...venue, status: 'CONFLICT' } }),
      snapshot({ listing: listing({ version: 2 }) }),
    ])
      expect(snapshotReviewKey(changed)).not.toBe(key);
    expect(snapshotReviewKey(snapshot())).toBe(key);
  });

  it('keeps old chart/candidate date defaults explicit and drops unrelated action identities', () => {
    expect(initialSetupDraft('stockSector', true).start).toBe('2026-10-26');
    expect(initialSetupDraft('stockSector', false).start).toBe('2025-01-01');
    expect(initialSetupDraft('listingImport', true).start).toBe('2025-09-21');
    expect(selectionForAction(listingSelection('listingMapping'), 'listingValidate')).toEqual(
      listingSelection('listingValidate'),
    );
    expect(selectionForAction(listingSelection('listingMapping'), 'referenceMapping')).toEqual({
      action: 'referenceMapping',
      underlyingId: '',
      listingId: '',
      referenceId: '',
      sectorId: '',
      mappingId: '',
    });
    expect(selectionForAction(directSelection('referenceMapping'), 'basis').referenceId).toBe(
      'sp500',
    );
  });
});
