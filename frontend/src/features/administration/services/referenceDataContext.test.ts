import { beforeEach, describe, expect, it, vi } from 'vitest';
import { chartClient } from '../../analysis/services/chartClient';
import type { ChartComparison, ChartIdentity } from '../../analysis/types/charts';
import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow, CandidateLiveWorkflowStep } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import {
  canonicalSetupUrl,
  isWorkflowSetupAction,
  parseReferenceDataContext,
  resolveReferenceDataContext,
  withChartSetupContext,
} from './referenceDataContext';
import { topDownAdminClient, type ProviderMapping } from './topDownAdminClient';

vi.mock('../../analysis/services/chartClient', () => ({ chartClient: { series: vi.fn() } }));
vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { liveWorkflow: vi.fn() },
}));
vi.mock('../../market/services/client', () => ({ marketApiClient: { getUnderlying: vi.fn() } }));
vi.mock('./topDownAdminClient', () => ({
  topDownAdminClient: { references: vi.fn(), sectors: vi.fn(), mappings: vi.fn() },
}));

const parse = (query: string) => parseReferenceDataContext(new URLSearchParams(query));
const listing = (id = 'l2', underlyingId = 'u1', primary = false): ListingResponse => ({
  id,
  underlying_id: underlyingId,
  trading_venue_id: 'v1',
  trading_venue_mic: 'XETR',
  trading_venue_name: 'Xetra',
  ticker: 'TEST',
  currency_code: 'EUR',
  lifecycle_status: 'ACTIVE',
  is_primary: primary,
  version: 1,
  created_at: '2026-10-26T00:00:00Z',
  updated_at: '2026-10-26T00:00:00Z',
});
const underlying = (id = 'u1'): UnderlyingDetailResponse => ({
  id,
  name: 'Synthetic security',
  type: 'STOCK',
  isin: 'DE000TEST001',
  wkn: null,
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: '2026-10-26T00:00:00Z',
  updated_at: '2026-10-26T00:00:00Z',
  primary_listing: null,
  listings: [listing('l1', id, true), listing('l2', id)],
});
const mapping = (overrides: Partial<ProviderMapping> = {}): ProviderMapping => ({
  id: 'm1',
  workspace_id: 'workspace',
  listing_id: 'l2',
  market_data_instrument_id: 'i1',
  provider: 'EODHD',
  status: 'DISABLED',
  provider_symbol: 'TEST',
  provider_exchange_code: 'XETRA',
  version: 3,
  validated_at: null,
  validation_message: null,
  created_at: '2026-10-26T00:00:00Z',
  updated_at: '2026-10-26T00:00:00Z',
  ...overrides,
});
const step = (
  action: string,
  actionParams: Record<string, string>,
  resourceId: string | null = null,
  code = 'SYNTHETIC_STEP',
): CandidateLiveWorkflowStep => ({
  code,
  label: code,
  status: 'BLOCKED',
  detail: 'Missing synthetic prerequisite',
  action,
  action_params: actionParams,
  resource_id: resourceId,
});
const workflow = (steps: CandidateLiveWorkflowStep[]): CandidateLiveWorkflow => ({
  candidate_id: 'c1',
  underlying_id: 'candidate-owner',
  as_of: '2026-10-26T00:00:00Z',
  ready: false,
  can_evaluate: false,
  next_action: steps[0]?.action ?? null,
  steps,
});
function comparison(listingId = 'l2', underlyingId = 'u1'): ChartComparison {
  const identity: ChartIdentity = {
    key: `listing:${listingId}`,
    name: 'Synthetic security',
    instrument_id: 'i1',
    instrument_type: 'STOCK',
    reference_id: null,
    reference_code: null,
    underlying_id: underlyingId,
    listing_id: listingId,
    isin: 'DE000TEST001',
    ticker: 'TEST',
    mic: 'XETR',
    currency: 'EUR',
    return_basis: 'SECURITY',
    basis_source: null,
    active: true,
    mapping_status: 'DISABLED',
    provider_identity: 'EODHD:TEST.XETRA',
    mapping_id: 'm1',
    mapping_version: 3,
    setup_url: `/chart-setup?listing_id=${listingId}`,
  };
  return {
    series: [
      {
        identity,
        currency: 'EUR',
        return_basis: 'SECURITY',
        points: [],
        first_date: null,
        last_date: null,
        observation_count: 0,
        issues: [],
        missing_comparison_dates: [],
      },
    ],
    requested_start: null,
    requested_end: '2026-10-26',
    price_field: 'CLOSE',
    common_start: null,
    common_end: null,
    comparison_status: 'EMPTY',
    issues: [],
    model_version: '1',
    resolution: 'EOD',
    fx_adjusted: false,
    calendar_verified: false,
    max_points_per_series: 10000,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(topDownAdminClient.references).mockResolvedValue([
    { id: 'r1', code: 'SPX', name: 'S&P 500', reference_type: 'INDEX', active: true },
    { id: 'sr1', code: 'TECH', name: 'Technology', reference_type: 'SECTOR_INDEX', active: true },
  ]);
  vi.mocked(topDownAdminClient.sectors).mockResolvedValue([
    { id: 's1', code: 'TECH', name: 'Technology', active: true },
  ]);
  vi.mocked(topDownAdminClient.mappings).mockResolvedValue([mapping()]);
  vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
    Promise.resolve(underlying(id)),
  );
  vi.mocked(chartClient.series).mockResolvedValue(comparison());
});

describe('explicit setup context contracts', () => {
  it.each([
    ['ASSIGN_BROAD_MARKET_BENCHMARK', 'underlying_id=u1', 'stockMarket'],
    ['ASSIGN_SECTOR', 'underlying_id=u1', 'stockSector'],
    ['ASSIGN_SECTOR_REFERENCE', 'resource_id=s1', 'sectorReference'],
    ['ASSIGN_REFERENCE_LISTING', 'resource_id=r1', 'proxy'],
    ['CREATE_EODHD_MAPPING', 'resource_id=l2', 'listingMapping'],
    ['VALIDATE_EODHD_MAPPING', 'resource_id=m1', 'listingValidate'],
    ['IMPORT_DAILY_PRICE_HISTORY', 'resource_id=l2', 'listingImport'],
  ])('maps %s to one editor and one resource meaning', (action, query, expected) => {
    const context = parse(`action=${action}&${query}`);
    expect(context.action).toBe(expected);
    const target = new URL(canonicalSetupUrl(context), 'https://workspace.test');
    expect(target.pathname).toBe('/chart-setup');
    expect(target.searchParams.get('action')).toBe(action);
    if (query.startsWith('resource_id=')) {
      expect(
        [context.referenceId, context.sectorId, context.listingId, context.mappingId].filter(
          Boolean,
        ),
      ).toHaveLength(1);
    }
  });

  it.each(['mystery', 'constructor', 'toString'])('does not accept unknown action %s', (action) => {
    expect(isWorkflowSetupAction(action)).toBe(false);
    expect(() => parse(`action=${action}`)).toThrow('Unbekannte');
  });

  it.each([
    'action=VALIDATE_EODHD_MAPPING&mapping_id=m1&resource_id=m2',
    'action=CREATE_EODHD_MAPPING&listing_id=l1&resource_id=l2',
    'action=ASSIGN_REFERENCE_LISTING&reference_id=r1&market_reference_id=r2',
    'action=ASSIGN_SECTOR_REFERENCE&sector_id=s1&sector_id=s2',
    'action=ASSIGN_SECTOR&underlying_id=u1&resource_id=s1',
    'reference_id=r1&listing_id=l1',
  ])('blocks contradictory or unsupported resource context: %s', (query) => {
    expect(() => parse(query)).toThrow();
  });

  it('merges structured legacy params and rejects conflicts or invalid JSON', () => {
    const params = new URLSearchParams({
      action: 'ASSIGN_REFERENCE_LISTING',
      action_params: JSON.stringify({ market_reference_id: 'r1' }),
    });
    expect(parseReferenceDataContext(params).referenceId).toBe('r1');
    params.set('reference_id', 'r2');
    expect(() => parseReferenceDataContext(params)).toThrow('Widersprüchliche');
    for (const value of ['{', '[]', '{"listing_id":4}']) {
      expect(() =>
        parseReferenceDataContext(new URLSearchParams({ action_params: value })),
      ).toThrow();
    }
  });

  it.each([
    'ASSIGN_SECTOR',
    'ASSIGN_SECTOR_REFERENCE',
    'ASSIGN_REFERENCE_LISTING',
    'CREATE_EODHD_MAPPING',
    'VALIDATE_EODHD_MAPPING',
    'IMPORT_DAILY_PRICE_HISTORY',
  ])('blocks missing source for %s', (action) => {
    expect(() => parse(`action=${action}`)).toThrow('Ausgangsobjekt');
  });

  it('preserves existing chart deep links and permits choosing an object in an empty editor', () => {
    expect(parse('').action).toBe('bootstrap');
    expect(parse('action=listingMapping').action).toBe('listingMapping');
    expect(parse('reference_id=r1').action).toBe('referenceImport');
    expect(parse('listing_id=l2').action).toBe('listingImport');
    expect(parse('sector_id=s1').action).toBe('sectorReference');
    expect(parse('underlying_id=u1').action).toBe('stockSector');
    expect(() => parse('candidate_id=c1&action=listingMapping')).toThrow('Workflow-Aktion');
  });

  it('constructs internal candidate/chart returns and preserves only supported chart fields', () => {
    const candidate = parse(
      'action=ASSIGN_SECTOR&underlying_id=u1&candidate_id=c%2F1&return_to=https://outside.test',
    );
    expect(candidate.returnTo).toBe('/candidates?candidate=c%2F1');
    const link = withChartSetupContext(
      '/chart-setup?reference_id=r1',
      new URLSearchParams(
        'target=reference:r1&target=listing:l2&period=6&field=ADJUSTED_CLOSE&end=2026-10-26&return_to=https://outside.test',
      ),
    );
    const context = parse(link.split('?')[1]);
    expect(context.returnTo).toBe(
      '/market-charts?period=6&end=2026-10-26&field=ADJUSTED_CLOSE&target=reference%3Ar1&target=listing%3Al2',
    );
    expect(context.returnTo).not.toContain('outside');
    expect(parse(canonicalSetupUrl(context).split('?')[1]).returnTo).toBe(context.returnTo);
    expect(withChartSetupContext('/candidates', new URLSearchParams())).toBe('/candidates');
  });
});

describe('authoritative identity and workflow reads', () => {
  it('keeps an explicit nonprimary listing after the underlying read', async () => {
    const result = await resolveReferenceDataContext(
      parse('action=listingMapping&underlying_id=u1&listing_id=l2'),
    );
    expect(result.listing?.id).toBe('l2');
    expect(result.listing?.is_primary).toBe(false);
    expect(result.mapping?.id).toBe('m1');
    expect(marketApiClient.getUnderlying).toHaveBeenCalledWith('u1', undefined);
  });

  it('chooses primary only without an explicit listing', async () => {
    const result = await resolveReferenceDataContext(
      parse('action=listingMapping&underlying_id=u1'),
    );
    expect(result.listingId).toBe('l1');
    expect(result.mapping).toBeNull();
  });

  it('resolves listing-only deep links through the stored scoped chart reader and the actual owner', async () => {
    const abort = new AbortController();
    const result = await resolveReferenceDataContext(parse('listing_id=l2'), abort.signal);
    expect(chartClient.series).toHaveBeenCalledWith(
      ['listing:l2'],
      expect.any(String),
      expect.any(String),
      'CLOSE',
      abort.signal,
    );
    expect(marketApiClient.getUnderlying).toHaveBeenCalledWith('u1', abort.signal);
    expect(result.underlyingId).toBe('u1');
    expect(result.listingId).toBe('l2');
  });

  it('allows an unmapped chart listing to open for explicit mapping creation', async () => {
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([]);
    const result = await resolveReferenceDataContext(parse('listing_id=l2'));
    expect(result.mapping).toBeNull();
    expect(result.listingId).toBe('l2');
  });

  it('never interprets an index mapping ID as a listing mapping', async () => {
    const result = await resolveReferenceDataContext(
      parse('action=referenceMapping&reference_id=r1&mapping_id=index-map'),
    );
    expect(result.reference?.id).toBe('r1');
    expect(result.listing).toBeNull();
    expect(topDownAdminClient.mappings).not.toHaveBeenCalled();
  });

  it('accepts a later blocked market step with its own listing owner, not candidate owner', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([
        step('ASSIGN_SECTOR', { underlying_id: 'candidate-owner' }),
        step(
          'VALIDATE_EODHD_MAPPING',
          { underlying_id: 'u1', listing_id: 'l2', mapping_id: 'm1' },
          'm1',
          'MARKET_MAPPING',
        ),
      ]),
    );
    const result = await resolveReferenceDataContext(
      parse('action=VALIDATE_EODHD_MAPPING&candidate_id=c1&resource_id=m1'),
    );
    expect(result.workflowStep?.code).toBe('MARKET_MAPPING');
    expect(result.underlying?.id).toBe('u1');
    expect(result.mappingId).toBe('m1');
    expect(result.listingId).toBe('l2');
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalledWith(
      'candidate-owner',
      expect.anything(),
    );
  });

  it('keeps reference-listing targets free of candidate underlying defaults', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step('ASSIGN_REFERENCE_LISTING', { market_reference_id: 'r1' }, 'r1')]),
    );
    const result = await resolveReferenceDataContext(
      parse('action=ASSIGN_REFERENCE_LISTING&candidate_id=c1&resource_id=r1'),
    );
    expect(result.referenceId).toBe('r1');
    expect(result.underlyingId).toBe('');
    expect(result.listingId).toBe('');
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
  });

  it('rejects stale action, changed params and explicit foreign candidate listing owner', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([
        step(
          'VALIDATE_EODHD_MAPPING',
          { underlying_id: 'u1', listing_id: 'l2', mapping_id: 'm1' },
          'm1',
        ),
      ]),
    );
    for (const query of [
      'action=CREATE_EODHD_MAPPING&listing_id=l2',
      'action=VALIDATE_EODHD_MAPPING&mapping_id=m1&underlying_id=candidate-owner',
      'action=VALIDATE_EODHD_MAPPING&mapping_id=m1&listing_id=l1',
      'action=VALIDATE_EODHD_MAPPING&mapping_id=m1&step_code=OTHER_STEP',
    ]) {
      await expect(resolveReferenceDataContext(parse(`${query}&candidate_id=c1`))).rejects.toThrow(
        'konkrete Schritt',
      );
    }
    expect(topDownAdminClient.mappings).not.toHaveBeenCalled();
  });

  it('does not silently select a different blocked action with matching code only', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([
        step(
          'CREATE_EODHD_MAPPING',
          { underlying_id: 'u1', listing_id: 'l1' },
          'l1',
          'MARKET_MAPPING',
        ),
        step(
          'CREATE_EODHD_MAPPING',
          { underlying_id: 'u2', listing_id: 'l2' },
          'l2',
          'SECTOR_MAPPING',
        ),
      ]),
    );
    const result = await resolveReferenceDataContext(
      parse(
        'action=CREATE_EODHD_MAPPING&candidate_id=c1&listing_id=l2&underlying_id=u2&resource_id=l2',
      ),
    );
    expect(result.workflowStep?.code).toBe('SECTOR_MAPPING');
    expect(result.underlyingId).toBe('u2');
  });

  it('allows postwrite readback of a completed step without changing its action', async () => {
    const completed = step('ASSIGN_SECTOR', { underlying_id: 'u1' });
    completed.status = 'COMPLETE';
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue({
      ...workflow([completed]),
      underlying_id: 'u1',
    });
    const context = parse('action=ASSIGN_SECTOR&candidate_id=c1&underlying_id=u1');
    await expect(resolveReferenceDataContext(context)).rejects.toThrow('konkrete Schritt');
    const result = await resolveReferenceDataContext(context, undefined, {
      requireBlockedStep: false,
    });
    expect(result.action).toBe('stockSector');
    expect(result.workflowStep).toBeNull();
    expect(result.workflow?.steps[0].status).toBe('COMPLETE');
  });

  it('binds a candidate assignment to the actual candidate underlying while keeping listing owners separate', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step('ASSIGN_SECTOR', { underlying_id: 'u1' })]),
    );
    await expect(
      resolveReferenceDataContext(parse('action=ASSIGN_SECTOR&candidate_id=c1&underlying_id=u1')),
    ).rejects.toThrow('Basiswert dieses Kandidaten');
  });

  it('blocks foreign/ambiguous mappings and wrong underlying membership', async () => {
    await expect(
      resolveReferenceDataContext(
        parse('action=listingMapping&listing_id=l1&underlying_id=u1&mapping_id=m1'),
      ),
    ).rejects.toThrow('Mapping-ID');
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([mapping(), mapping({ id: 'm2' })]);
    await expect(
      resolveReferenceDataContext(parse('action=listingMapping&listing_id=l2&underlying_id=u1')),
    ).rejects.toThrow('Mehrdeutige');
    vi.mocked(topDownAdminClient.mappings).mockResolvedValue([]);
    await expect(
      resolveReferenceDataContext(
        parse('action=listingMapping&listing_id=foreign&underlying_id=u1'),
      ),
    ).rejects.toThrow('gehören nicht zusammen');
  });

  it('blocks foreign scoped read results, missing references and unsuitable sector references', async () => {
    vi.mocked(chartClient.series).mockResolvedValue(comparison('wrong'));
    await expect(resolveReferenceDataContext(parse('listing_id=l2'))).rejects.toThrow(
      'Zugehörigkeit',
    );
    await expect(resolveReferenceDataContext(parse('reference_id=missing'))).rejects.toThrow(
      'Marktreferenz fehlt',
    );
    await expect(resolveReferenceDataContext(parse('sector_id=missing'))).rejects.toThrow(
      'Sektor fehlt',
    );
    await expect(
      resolveReferenceDataContext(parse('action=sectorReference&sector_id=s1&reference_id=r1')),
    ).rejects.toThrow('Sektorreferenz');
  });

  it('checks abort after reads so an abandoned generation cannot adopt the result', async () => {
    const abort = new AbortController();
    vi.mocked(marketApiClient.getUnderlying).mockImplementation(() => {
      abort.abort();
      return Promise.resolve(underlying());
    });
    await expect(
      resolveReferenceDataContext(parse('underlying_id=u1'), abort.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
