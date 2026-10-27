import { beforeEach, describe, expect, it, vi } from 'vitest';

import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow, CandidateLiveWorkflowStep } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import type { AnalysisDetail, AnalysisRunDetail, AnalysisSummary } from '../types/api';
import {
  analysisContextReturnTo,
  analysisDetailUrl,
  canonicalAnalysisSetupUrl,
  parseAnalysisSetupContext,
  resolveAnalysisSetupContext,
  sanitizeOverviewContext,
} from './analysisWorkflowContext';
import { analysisApiClient } from './client';

vi.mock('../../candidate/services/client', () => ({
  candidateApiClient: { liveWorkflow: vi.fn(), evaluateAuto: vi.fn() },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn(), searchProviderInstruments: vi.fn() },
}));
vi.mock('./client', () => ({
  analysisApiClient: {
    get: vi.fn(),
    getRun: vi.fn(),
    create: vi.fn(),
    run: vi.fn(),
    runReference: vi.fn(),
  },
}));

const parse = (query = '') => parseAnalysisSetupContext(new URLSearchParams(query));
const listing = (id = 'l2', owner = 'u1', primary = false): ListingResponse => ({
  id,
  underlying_id: owner,
  trading_venue_id: 'v1',
  trading_venue_mic: 'XETR',
  trading_venue_name: 'Xetra',
  ticker: 'SYNTH',
  currency_code: 'EUR',
  lifecycle_status: 'ACTIVE',
  is_primary: primary,
  version: 1,
  created_at: '2026-10-27T00:00:00Z',
  updated_at: '2026-10-27T00:00:00Z',
});
const underlying = (id = 'u1'): UnderlyingDetailResponse => ({
  id,
  name: 'Synthetic ETF owner',
  type: 'ETF',
  isin: 'DE000TEST001',
  wkn: null,
  lifecycle_status: 'ACTIVE',
  quality_status: 'VERIFIED',
  version: 1,
  created_at: '2026-10-27T00:00:00Z',
  updated_at: '2026-10-27T00:00:00Z',
  primary_listing: null,
  listings: [listing('l1', id, true), listing('l2', id)],
});
const analysis = (patch: Partial<AnalysisSummary> = {}): AnalysisSummary => ({
  id: 'a1',
  underlying_id: 'u1',
  listing_id: 'l2',
  market_data_instrument_id: 'i1',
  created_at: '2026-10-27T00:00:00Z',
  created_by: 'Synthetic user',
  ...patch,
});
const run = (version = 1) => ({
  version,
  status: 'COMPLETED',
  quality_status: 'GOOD',
  model_id: 'EOD_TREND_MOMENTUM',
  model_version: '1.0.0',
  observation_count: 250,
  analysis_time: '2026-10-26T12:00:00Z',
  input_hash: `saved-hash-${version}`,
});
const detail = (identity = analysis()): AnalysisDetail => ({
  analysis: identity,
  runs: [run(1), run(2)],
});
const source = (identity = analysis(), version = 1): AnalysisRunDetail => ({
  analysis: identity,
  run: run(version),
  parameters: { short_window: 17, long_window: 199, price_field: 'CLOSE' },
  metrics: {},
  notes: ['Saved source'],
  data_sources: [],
  criteria: [],
  snapshot: [],
});
const step = (overrides: Partial<CandidateLiveWorkflowStep> = {}): CandidateLiveWorkflowStep => ({
  code: 'MARKET_ANALYSIS',
  label: 'Market FT-006 analysis',
  status: 'BLOCKED',
  detail: 'No completed analysis',
  action: 'RUN_MARKET_ANALYSIS',
  resource_id: 'l2',
  action_params: { underlying_id: 'u1', listing_id: 'l2' },
  ...overrides,
});
const workflow = (steps = [step()]): CandidateLiveWorkflow => ({
  candidate_id: 'c1',
  underlying_id: 'different-candidate-owner',
  as_of: '2026-10-27T00:00:00Z',
  ready: false,
  can_evaluate: false,
  next_action: 'ASSIGN_SECTOR',
  steps,
});
const repair = 'action=RUN_MARKET_ANALYSIS&candidate_id=c1&resource_id=l2';

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(marketApiClient.getUnderlying).mockImplementation((id) =>
    Promise.resolve(underlying(id)),
  );
  vi.mocked(analysisApiClient.get).mockResolvedValue(detail());
  vi.mocked(analysisApiClient.getRun).mockResolvedValue(source());
  vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(workflow());
});

describe('analysis setup URL contract', () => {
  it('retains an exact source and its historical candidate return without a repair command', () => {
    const context = parse('analysis_id=a1&source_version=1&candidate_id=c1&evaluation_id=e-old');
    expect(context.sourceVersion).toBe(1);
    expect(context.workflowAction).toBeNull();
    expect(context.returnTo).toBe('/candidates?candidate=c1&evaluation=e-old');
    expect(
      parse(new URL(canonicalAnalysisSetupUrl(context), 'https://workspace.test').search).key,
    ).toBe(context.key);
    expect(analysisDetailUrl('a1', 1, context)).toBe(
      '/market-analyses/a1?candidate_id=c1&evaluation_id=e-old&version=1',
    );
  });

  it('preserves only documented overview filters and never accepts an external return', () => {
    const overview =
      'offset=20&underlying_id=u1&status=COMPLETED&quality_status=GOOD&analysis_time_from=2026-01-01&analysis_time_to=2026-10-26&sort_by=created_at&sort_direction=asc&return_to=https://outside.test&action=RUN';
    const context = parse(
      new URLSearchParams({
        overview_context: overview,
        return_to: 'https://outside.test',
      }).toString(),
    );
    expect(context.returnTo).toContain('/market-analyses?offset=20&underlying_id=u1');
    expect(context.returnTo).not.toContain('outside');
    expect(context.returnTo).not.toContain('action=');
    expect(
      analysisContextReturnTo({ analysisId: 'a1', sourceVersion: 2, overviewContext: overview }),
    ).toContain('/market-analyses/a1?overview_context=');
    expect(analysisDetailUrl('a1', undefined, { overviewContext: overview })).not.toContain(
      'outside',
    );
    expect(canonicalAnalysisSetupUrl()).toBe('/market-analyses/setup');
  });

  it('uses resource_id exclusively as the legacy RUN listing and merges explicit params', () => {
    const context = parse(
      `${repair}&listing_id=l2&action_params=${encodeURIComponent(JSON.stringify({ underlying_id: 'u1', listing_id: 'l2' }))}`,
    );
    expect(context.listingId).toBe('l2');
    expect(context.analysisId).toBe('');
    expect(context.instrumentId).toBe('');
    expect(context.underlyingId).toBe('u1');
  });

  it.each([
    ['action=UNKNOWN', 'Unbekannte'],
    ['action=RUN_MARKET_ANALYSIS&action=UNKNOWN', 'Widersprüchliche'],
    ['action=RUN_MARKET_ANALYSIS&listing_id=l2', 'Kandidaten'],
    ['action=RUN_MARKET_ANALYSIS&candidate_id=c1', 'Listingkennung'],
    [`${repair}&listing_id=l1`, 'Widersprüchliche'],
    ['resource_id=l2', 'Workflow-Parameter'],
    ['step_code=MARKET_ANALYSIS', 'Workflow-Parameter'],
    ['candidate_id=c1', 'konkreten Workflow'],
    ['evaluation_id=e1', 'Candidate-ID'],
    ['source_version=1', 'konkrete Analyse'],
    ['analysis_id=a1&source_version=0', 'positive ganze'],
    ['analysis_id=a1&source_version=', 'positive ganze'],
    ['analysis_id=', 'ist leer'],
    ['analysis_id=&analysis_id=a1', 'Widersprüchliche'],
    ['analysis_id=a1&source_version=&source_version=1', 'Widersprüchliche'],
    ['analysis_id=a1&source_version=1.5', 'positive ganze'],
    ['analysis_id=a1&source_version=01', 'positive ganze'],
    ['analysis_id=a1&source_version=9007199254740992', 'positive ganze'],
    ['analysis_id=a1&source_version=1&source_version=2', 'Widersprüchliche'],
    ['analysis_id=a1&analysis_id=a2', 'Widersprüchliche'],
    ['analysis_id=a1%2Fruns', 'nicht eindeutig'],
    ['market_data_instrument_id=i1', 'bestehende Analyse'],
    ['action_params={', 'nicht lesbar'],
    ['action_params=[]', 'Textwerte'],
    ['action_params={"listing_id":42}', 'Textwerte'],
    ['action_params={"listing_id":"l2"}', 'Workflow-Parameter'],
    [`${repair}&underlying_id=u1&action_params={"underlying_id":"other"}`, 'Widersprüchliche'],
  ])('blocks malformed/conflicting context %s', (query, message) => {
    expect(() => parse(query)).toThrow(message);
  });

  it('rejects conflicting overview values and invalid explicit detail versions', () => {
    expect(() => sanitizeOverviewContext('offset=1&offset=2')).toThrow('Widersprüchliche');
    expect(() => analysisDetailUrl('', 1)).toThrow('fehlt');
    expect(() => analysisDetailUrl('a1', 0)).toThrow('positive ganze');
  });
});

describe('fresh workflow and actual listing owner', () => {
  it('matches the concrete blocked step even when it is not next_action and owner differs from candidate', async () => {
    const signal = new AbortController().signal;
    const resolved = await resolveAnalysisSetupContext(parse(repair), signal);
    expect(candidateApiClient.liveWorkflow).toHaveBeenCalledWith('c1', signal);
    expect(marketApiClient.getUnderlying).toHaveBeenCalledWith('u1', signal);
    expect(resolved.context).toMatchObject({
      underlyingId: 'u1',
      listingId: 'l2',
      stepCode: 'MARKET_ANALYSIS',
    });
    expect(resolved.listing?.is_primary).toBe(false);
    expect(resolved.returnTo).toBe('/candidates?candidate=c1');
    expect(resolved.workflowStep?.code).toBe('MARKET_ANALYSIS');
    expect(analysisApiClient.create).not.toHaveBeenCalled();
    expect(analysisApiClient.run).not.toHaveBeenCalled();
    expect(analysisApiClient.runReference).not.toHaveBeenCalled();
    expect(candidateApiClient.evaluateAuto).not.toHaveBeenCalled();
    expect(marketApiClient.searchProviderInstruments).not.toHaveBeenCalled();
  });

  it('preserves and validates an acknowledged analysis when continuing the same repair', async () => {
    const resolved = await resolveAnalysisSetupContext(parse(`${repair}&analysis_id=a1`));
    expect(resolved.detail?.analysis.id).toBe('a1');
    expect(resolved.context.listingId).toBe('l2');
    expect(canonicalAnalysisSetupUrl(resolved.context)).toContain('analysis_id=a1');
  });

  it('pins one of several blocked roles using step_code, never picking the first match', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step(), step({ code: 'SECTOR_ANALYSIS' })]),
    );
    await expect(resolveAnalysisSetupContext(parse(repair))).rejects.toThrow('Mehrere blockierte');
    const resolved = await resolveAnalysisSetupContext(
      parse(`${repair}&step_code=SECTOR_ANALYSIS`),
    );
    expect(resolved.workflowStep?.code).toBe('SECTOR_ANALYSIS');
  });

  it.each([
    step({ status: 'COMPLETE' }),
    step({ action: 'IMPORT_DAILY_PRICE_HISTORY' }),
    step({ resource_id: 'l1', action_params: { listing_id: 'l1', underlying_id: 'u1' } }),
    step({ action_params: { listing_id: 'l2', underlying_id: 'changed-owner' } }),
  ])('blocks changed steps without silently changing action or owner', async (current) => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(workflow([current]));
    await expect(resolveAnalysisSetupContext(parse(`${repair}&underlying_id=u1`))).rejects.toThrow(
      'nicht mehr blockiert',
    );
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
  });

  it('requires all supplied action params and resource IDs to match the fresh step', async () => {
    const params = encodeURIComponent(
      JSON.stringify({ underlying_id: 'u1', listing_id: 'l2', reason: 'old' }),
    );
    await expect(
      resolveAnalysisSetupContext(parse(`${repair}&action_params=${params}`)),
    ).rejects.toThrow('Identitäten');
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step({ resource_id: 'other' })]),
    );
    await expect(resolveAnalysisSetupContext(parse(`${repair}&underlying_id=u1`))).rejects.toThrow(
      'nicht mehr blockiert',
    );
  });

  it('rejects internally conflicting step identities and a foreign candidate response', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step({ resource_id: 'other' })]),
    );
    await expect(
      resolveAnalysisSetupContext(
        parse('action=RUN_MARKET_ANALYSIS&candidate_id=c1&listing_id=l2'),
      ),
    ).rejects.toThrow('Widersprüchliche');
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue({
      ...workflow(),
      candidate_id: 'other',
    });
    await expect(resolveAnalysisSetupContext(parse(repair))).rejects.toThrow('anderen Kandidaten');
  });

  it('allows completed-step readback only through an explicit readback option', async () => {
    vi.mocked(candidateApiClient.liveWorkflow).mockResolvedValue(
      workflow([step({ status: 'COMPLETE' })]),
    );
    const context = parse(`${repair}&underlying_id=u1&analysis_id=a1`);
    await expect(resolveAnalysisSetupContext(context)).rejects.toThrow('nicht mehr blockiert');
    const readback = await resolveAnalysisSetupContext(context, undefined, {
      requireBlockedStep: false,
    });
    expect(readback.workflowStep).toBeNull();
    expect(readback.detail?.analysis.id).toBe('a1');
  });
});

describe('stored analysis and source identity', () => {
  it('loads the exact old version and structured parameters without inferring request dates', async () => {
    const signal = new AbortController().signal;
    const context = parse('analysis_id=a1&source_version=1&candidate_id=c1&evaluation_id=e-old');
    const resolved = await resolveAnalysisSetupContext(context, signal);
    expect(analysisApiClient.get).toHaveBeenCalledWith('a1', signal);
    expect(analysisApiClient.getRun).toHaveBeenCalledWith('a1', 1, signal);
    expect(resolved.source).toEqual(source());
    expect(resolved.source).not.toHaveProperty('start_date');
    expect(resolved.context.sourceVersion).toBe(1);
    expect(candidateApiClient.liveWorkflow).not.toHaveBeenCalled();
  });

  it('accepts listing-free reference analysis only with its real instrument identity', async () => {
    const reference = analysis({
      underlying_id: null,
      listing_id: null,
      market_data_instrument_id: 'reference-instrument',
    });
    vi.mocked(analysisApiClient.get).mockResolvedValue(detail(reference));
    vi.mocked(analysisApiClient.getRun).mockResolvedValue(source(reference));
    const resolved = await resolveAnalysisSetupContext(
      parse('analysis_id=a1&source_version=1&market_data_instrument_id=reference-instrument'),
    );
    expect(resolved.context).toMatchObject({
      underlyingId: '',
      listingId: '',
      instrumentId: 'reference-instrument',
    });
    expect(resolved.underlying).toBeNull();
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&listing_id=l2')),
    ).rejects.toThrow('listingfreie');
  });

  it.each([
    analysis({ id: 'foreign-analysis' }),
    analysis({ underlying_id: 'foreign-owner' }),
    analysis({ listing_id: 'foreign-listing' }),
    analysis({ listing_id: null }),
    analysis({ underlying_id: null, listing_id: null, market_data_instrument_id: null }),
  ])('rejects a foreign or incomplete analysis identity', async (value) => {
    vi.mocked(analysisApiClient.get).mockResolvedValue(detail(value));
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&underlying_id=u1&listing_id=l2')),
    ).rejects.toThrow();
  });

  it('rejects an explicit foreign instrument or malformed listing-owned identity', async () => {
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&market_data_instrument_id=foreign')),
    ).rejects.toThrow('Instrumentkennung');
    vi.mocked(analysisApiClient.get).mockResolvedValue(detail(analysis({ underlying_id: null })));
    await expect(resolveAnalysisSetupContext(parse('analysis_id=a1'))).rejects.toThrow(
      'Listingzugehörigkeit',
    );
  });

  it('rejects absent/duplicate source versions and never silently selects latest', async () => {
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&source_version=3')),
    ).rejects.toThrow('Quellversion');
    expect(analysisApiClient.getRun).not.toHaveBeenCalled();
    vi.mocked(analysisApiClient.get).mockResolvedValue({ ...detail(), runs: [run(1), run(1)] });
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&source_version=1')),
    ).rejects.toThrow('nicht eindeutig');
  });

  it.each([
    { ...source(), analysis: analysis({ id: 'other' }) },
    { ...source(), analysis: analysis({ listing_id: 'l1' }) },
    { ...source(), run: run(2) },
    { ...source(), run: { ...run(), model_version: '1.0.1' } },
    { ...source(), run: { ...run(), input_hash: 'changed' } },
  ])('rejects a source read belonging to another identity or immutable run', async (value) => {
    vi.mocked(analysisApiClient.getRun).mockResolvedValue(value);
    await expect(
      resolveAnalysisSetupContext(parse('analysis_id=a1&source_version=1')),
    ).rejects.toThrow();
  });
});

describe('explicit versus default listing', () => {
  it('supports empty selection and defaults only a unique active primary', async () => {
    const empty = await resolveAnalysisSetupContext(parse());
    expect(empty.underlying).toBeNull();
    expect(marketApiClient.getUnderlying).not.toHaveBeenCalled();
    const selected = await resolveAnalysisSetupContext(parse('underlying_id=u1'));
    expect(selected.listing?.id).toBe('l1');
    const explicit = await resolveAnalysisSetupContext(parse('underlying_id=u1&listing_id=l2'));
    expect(explicit.listing?.id).toBe('l2');
  });

  it('keeps an explicit inactive listing instead of silently replacing it with primary', async () => {
    const owner = underlying();
    owner.listings[1].lifecycle_status = 'INACTIVE';
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(owner);
    const resolved = await resolveAnalysisSetupContext(parse('underlying_id=u1&listing_id=l2'));
    expect(resolved.listing).toMatchObject({ id: 'l2', lifecycle_status: 'INACTIVE' });
  });

  it('requires explicit selection for ambiguous primary and does not choose first active', async () => {
    const owner = underlying();
    owner.listings[1].is_primary = true;
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(owner);
    await expect(resolveAnalysisSetupContext(parse('underlying_id=u1'))).rejects.toThrow(
      'nicht eindeutig',
    );
    owner.listings.forEach((item) => {
      item.is_primary = false;
    });
    const resolved = await resolveAnalysisSetupContext(parse('underlying_id=u1'));
    expect(resolved.listing).toBeNull();
  });

  it('blocks foreign/duplicate memberships and missing owner reads', async () => {
    await expect(
      resolveAnalysisSetupContext(parse('underlying_id=u1&listing_id=missing')),
    ).rejects.toThrow('nicht eindeutig');
    await expect(resolveAnalysisSetupContext(parse('listing_id=l2'))).rejects.toThrow(
      'Basiswertzugehörigkeit',
    );
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue(underlying('foreign-owner'));
    await expect(resolveAnalysisSetupContext(parse('underlying_id=u1'))).rejects.toThrow(
      'Analysekontext',
    );
  });

  it('blocks a listing row with a foreign declared owner', async () => {
    vi.mocked(marketApiClient.getUnderlying).mockResolvedValue({
      ...underlying(),
      listings: [listing('l2', 'foreign')],
    });
    await expect(
      resolveAnalysisSetupContext(parse('underlying_id=u1&listing_id=l2')),
    ).rejects.toThrow('gehören nicht zusammen');
  });

  it('throws cancellation even when a delayed mocked read ignores the abort signal', async () => {
    const controller = new AbortController();
    vi.mocked(marketApiClient.getUnderlying).mockImplementation(() => {
      controller.abort();
      return Promise.resolve(underlying());
    });
    await expect(
      resolveAnalysisSetupContext(parse('underlying_id=u1'), controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
