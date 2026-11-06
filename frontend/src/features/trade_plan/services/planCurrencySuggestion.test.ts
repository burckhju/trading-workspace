import { beforeEach, describe, expect, it, vi } from 'vitest';

import { readHistoricalAnalysisCurrency } from '../../analysis';
import type { CandidateEvaluation } from '../../candidate/types/api';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import type { TradePlanOriginContext } from './originContext';
import { loadCandidatePlanCurrencySuggestion } from './planCurrencySuggestion';

vi.mock('../../analysis', () => ({ readHistoricalAnalysisCurrency: vi.fn() }));
const sourceRead = vi.mocked(readHistoricalAnalysisCurrency);
const source = {
  role: 'UNDERLYING',
  source_type: 'ANALYSIS',
  source_id: 'historical-analysis',
  source_version: 2,
  model_id: 'EOD_TREND_MOMENTUM',
  model_version: '1.0.0',
};
const underlying: UnderlyingDetailResponse = {
  id: 'underlying-1',
  name: 'Synthetic Underlying',
  type: 'STOCK',
  isin: null,
  wkn: null,
  lifecycle_status: 'ACTIVE',
  quality_status: 'COMPLETE',
  version: 3,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  primary_listing: {
    id: 'current-eur-listing',
    ticker: 'TEST',
    trading_venue_id: 'venue-current',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Synthetic exchange',
    currency_code: 'EUR',
  },
  listings: [],
};
const proposal = {
  currency: 'USD',
  analysisId: source.source_id,
  version: source.source_version,
  listingId: 'historical-usd-listing',
};

function candidate(sources: unknown = [source]): TradePlanOriginContext {
  return {
    type: 'CANDIDATE_EVALUATION',
    candidateId: 'candidate-1',
    underlying,
    evaluation: {
      id: 'pinned-evaluation',
      version: 1,
      direction: 'LONG',
      model_id: 'TOP_DOWN_CANDIDATE',
      model_version: '2',
      qualification: 'QUALIFIED',
      quality_status: 'GOOD',
      warnings: [],
      evaluated_at: '2025-01-01T00:00:00Z',
      criteria: [],
      sources: sources as CandidateEvaluation['sources'],
    },
  };
}

beforeEach(() => {
  sourceRead.mockReset();
  sourceRead.mockResolvedValue(proposal);
});

describe('Candidate plan currency source selection', () => {
  it('uses only the pinned evaluation source despite a different current primary listing', async () => {
    const signal = new AbortController().signal;
    const origin = candidate([
      { ...source, role: 'MARKET', source_id: 'market-analysis' },
      source,
      { ...source, role: 'SECTOR', source_id: 'sector-analysis' },
    ]);
    await expect(loadCandidatePlanCurrencySuggestion(origin, signal)).resolves.toEqual(proposal);
    expect(sourceRead).toHaveBeenCalledExactlyOnceWith(
      {
        analysisId: 'historical-analysis',
        version: 2,
        underlyingId: 'underlying-1',
        modelId: 'EOD_TREND_MOMENTUM',
        modelVersion: '1.0.0',
      },
      signal,
    );
    expect(underlying.primary_listing?.currency_code).toBe('EUR');
  });

  it('does not read currency for a manual origin', async () => {
    await expect(
      loadCandidatePlanCurrencySuggestion(
        { type: 'MANUAL', underlying },
        new AbortController().signal,
      ),
    ).resolves.toBeNull();
    expect(sourceRead).not.toHaveBeenCalled();
  });

  it.each<{ name: string; sources: unknown }>([
    { name: 'missing sources', sources: undefined },
    { name: 'null sources', sources: null },
    { name: 'non-array sources', sources: source },
    { name: 'empty sources', sources: [] },
    { name: 'no UNDERLYING', sources: [{ ...source, role: 'MARKET' }] },
    { name: 'two UNDERLYING analyses', sources: [source, { ...source, source_id: 'other' }] },
    {
      name: 'second UNDERLYING of another type',
      sources: [source, { ...source, source_type: 'OTHER' }],
    },
    { name: 'different source type', sources: [{ ...source, source_type: 'OTHER' }] },
    { name: 'malformed extra source', sources: [source, null] },
    { name: 'unknown extra source role', sources: [source, {}] },
    { name: 'missing source ID', sources: [{ ...source, source_id: undefined }] },
    { name: 'blank source ID', sources: [{ ...source, source_id: ' ' }] },
    { name: 'missing version', sources: [{ ...source, source_version: undefined }] },
    { name: 'zero version', sources: [{ ...source, source_version: 0 }] },
    { name: 'fractional version', sources: [{ ...source, source_version: 1.5 }] },
    { name: 'missing model ID', sources: [{ ...source, model_id: undefined }] },
    { name: 'blank model ID', sources: [{ ...source, model_id: '' }] },
    { name: 'missing model version', sources: [{ ...source, model_version: undefined }] },
    { name: 'blank model version', sources: [{ ...source, model_version: '' }] },
  ])('returns no proposal for $name without an Analysis read', async ({ sources }) => {
    const origin = candidate(sources);
    if (sources === undefined && origin.type === 'CANDIDATE_EVALUATION')
      delete origin.evaluation.sources;
    await expect(
      loadCandidatePlanCurrencySuggestion(origin, new AbortController().signal),
    ).resolves.toBeNull();
    expect(sourceRead).not.toHaveBeenCalled();
  });

  it('keeps an unavailable optional source distinct from the already resolved origin', async () => {
    const origin = candidate();
    const before = structuredClone(origin);
    sourceRead.mockResolvedValueOnce(null);
    await expect(
      loadCandidatePlanCurrencySuggestion(origin, new AbortController().signal),
    ).resolves.toBeNull();
    expect(origin).toEqual(before);

    sourceRead.mockRejectedValueOnce(new Error('optional source unavailable'));
    await expect(
      loadCandidatePlanCurrencySuggestion(origin, new AbortController().signal),
    ).rejects.toThrow('optional source unavailable');
    expect(origin).toEqual(before);
    expect(sourceRead).toHaveBeenCalledTimes(2);
  });
});
