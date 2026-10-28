import { describe, expect, it } from 'vitest';
import { MarketTransportError } from '../../market/services/http';
import {
  defaultAnalysisParameters,
  type AnalysisDetail,
  type AnalysisRun,
  type AnalysisRunDetail,
} from '../types/api';
import {
  analysisDraftProblem,
  analysisDraftRequest,
  initialAnalysisDraft,
  prepareAnalysisSource,
  validateAnalysisCreateReceipt,
  validateAnalysisRunReadback,
  validateAnalysisRunReceipt,
} from './analysisSetupDraft';

const summary = {
  id: 'analysis',
  underlying_id: 'owner',
  listing_id: 'secondary',
  market_data_instrument_id: null,
  created_at: '2026-10-27T09:00:00Z',
  created_by: 'Tester',
};
const terminal: AnalysisRun = {
  version: 2,
  status: 'COMPLETED',
  quality_status: 'GOOD',
  model_id: 'EOD_TREND_MOMENTUM',
  model_version: '1.0.1',
  observation_count: 201,
  analysis_time: '2026-10-27T09:30:00Z',
  input_hash: 'persisted-hash',
};
const detail: AnalysisDetail = { analysis: summary, runs: [{ ...terminal, version: 1 }] };
const draft = {
  ...initialAnalysisDraft(false, false),
  start_date: '2026-01-01',
  end_date: '2026-10-01',
};
const request = analysisDraftRequest(draft);
const readback: AnalysisRunDetail = {
  analysis: summary,
  run: terminal,
  parameters: { ...defaultAnalysisParameters },
  metrics: {},
  notes: [],
  data_sources: [],
  criteria: [],
  snapshot: [],
};

describe('analysis command and historical proposal contracts', () => {
  it('keeps historical range absent and explicit candidate 400-day defaults distinct from ordinary 365-day proposals', () => {
    const ordinary = initialAnalysisDraft(false, false);
    const candidate = initialAnalysisDraft(true, false);
    expect((Date.parse(ordinary.end_date) - Date.parse(ordinary.start_date)) / 86400000).toBe(365);
    expect((Date.parse(candidate.end_date) - Date.parse(candidate.start_date)) / 86400000).toBe(
      400,
    );
    expect(initialAnalysisDraft(false, true)).toMatchObject({ start_date: '', end_date: '' });
  });

  it('preserves every supported source parameter, selected dates and exact decimal text without choosing the historical model', () => {
    const parameters = {
      ...defaultAnalysisParameters,
      price_field: 'CLOSE',
      short_window: 10,
      medium_window: 30,
      long_window: 100,
      momentum_windows: [5, 10, 50],
      volatility_window: 15,
      range_window: 99,
      minimum_required_observations: 123,
      maximum_data_age_days: 0,
      annualization_factor: '252.000000000000000000001',
      rounding_scale: 12,
    };
    const proposal = prepareAnalysisSource(draft, parameters);
    expect(analysisDraftRequest(proposal)).toEqual({
      start_date: '2026-01-01',
      end_date: '2026-10-01',
      model_version: '1.0.1',
      parameters,
    });
  });

  it('rejects incomplete or future parameter contracts rather than silently replacing absent fields with defaults', () => {
    const incomplete: Record<string, unknown> = { ...defaultAnalysisParameters };
    delete incomplete.medium_window;
    expect(() => prepareAnalysisSource(draft, incomplete)).toThrow(/nicht vollständig/);
    expect(() =>
      prepareAnalysisSource(draft, { ...defaultAnalysisParameters, future_parameter: 20 }),
    ).toThrow(/nicht vollständig/);
    expect(() =>
      prepareAnalysisSource(draft, { ...defaultAnalysisParameters, momentum_windows: [20, '60'] }),
    ).toThrow(/nicht lesbar/);
  });

  it.each([
    [{ start_date: '2026-02-30' }, /gültigen Zeitraum/],
    [{ start_date: '2026-12-01' }, /gültigen Zeitraum/],
    [{ short_window: '' }, /ganze Zahl/],
    [{ short_window: '2.5' }, /ganze Zahl/],
    [{ medium_window: '20' }, /aufsteigend/],
    [{ momentum_windows: '20, 20' }, /eindeutig aufsteigende/],
    [{ rounding_scale: '13' }, /zwischen 0 und 12/],
    [{ maximum_data_age_days: '-1' }, /ab 0/],
    [{ annualization_factor: '0.0' }, /positive Dezimalzahl/],
  ])(
    'rejects invalid input without normalizing away the correction draft: %j',
    (patch, expected) => {
      const invalid = { ...draft, ...patch };
      expect(analysisDraftProblem(invalid)).toMatch(expected);
      expect(() => analysisDraftRequest(invalid)).toThrow(expected);
      expect(invalid).toMatchObject(patch);
    },
  );

  it('retains the API-supported empty momentum list and Decimal exponent without inventing bounds', () => {
    expect(
      analysisDraftRequest({ ...draft, momentum_windows: '', annualization_factor: '+2.52e3' })
        .parameters,
    ).toMatchObject({ momentum_windows: [], annualization_factor: '+2.52e3' });
    expect(analysisDraftProblem({ ...draft, annualization_factor: '1e400' })).toBe('');
  });
});

describe('acknowledged response and exact readback contracts', () => {
  it('requires a usable creation identity and the requested owner/listing in a successful receipt', () => {
    expect(() => validateAnalysisCreateReceipt(summary, 'owner', 'secondary')).not.toThrow();
    for (const invalid of [
      undefined,
      { ...summary, listing_id: 'primary' },
      { ...summary, id: '../foreign' },
      { ...summary, created_at: '' },
      { ...summary, market_data_instrument_id: 23 },
    ])
      expect(() => validateAnalysisCreateReceipt(invalid, 'owner', 'secondary')).toThrow(
        MarketTransportError,
      );
  });

  it('requires a new terminal run in the requested model but preserves legitimate failed/not-evaluable outcomes', () => {
    expect(() => validateAnalysisRunReceipt(terminal, detail)).not.toThrow();
    for (const status of ['FAILED', 'NOT_EVALUABLE', 'COMPLETED_WITH_WARNINGS'])
      expect(() => validateAnalysisRunReceipt({ ...terminal, status }, detail)).not.toThrow();
    for (const invalid of [
      { ...terminal, version: 1 },
      { ...terminal, version: 1.5 },
      { ...terminal, model_version: '1.0.0' },
      { ...terminal, status: 'RUNNING' },
      { ...terminal, quality_status: 'UNKNOWN' },
      { ...terminal, input_hash: '' },
    ])
      expect(() => validateAnalysisRunReceipt(invalid, detail)).toThrow(MarketTransportError);
  });

  it('checks exact analysis ownership, version and receipt fields in readback rather than accepting latest run', () => {
    expect(() => validateAnalysisRunReadback(readback, detail, terminal, request)).not.toThrow();
    expect(() =>
      validateAnalysisRunReadback(
        { ...readback, analysis: { ...summary, id: 'foreign' } },
        detail,
        terminal,
        request,
      ),
    ).toThrow(/passt nicht/);
    expect(() =>
      validateAnalysisRunReadback(
        { ...readback, run: { ...terminal, version: 3 } },
        detail,
        terminal,
        request,
      ),
    ).toThrow(/passt nicht/);
    expect(() =>
      validateAnalysisRunReadback(
        { ...readback, parameters: { ...defaultAnalysisParameters, medium_window: 60 } },
        detail,
        terminal,
        request,
      ),
    ).toThrow(/Parameter passen nicht/);
  });

  it('compares Decimal readback exactly while accepting representation-only normalization', () => {
    const precise = analysisDraftRequest({
      ...draft,
      annualization_factor: '252.000000000000000000001',
    });
    expect(() => validateAnalysisRunReadback(readback, detail, terminal, precise)).toThrow(
      /Parameter passen nicht/,
    );
    const equivalent = {
      ...readback,
      parameters: { ...defaultAnalysisParameters, annualization_factor: '2.5200e2' },
    };
    expect(() => validateAnalysisRunReadback(equivalent, detail, terminal, request)).not.toThrow();
  });
});
