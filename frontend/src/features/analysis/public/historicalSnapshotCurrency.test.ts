import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { readHistoricalAnalysisCurrency, type HistoricalAnalysisReference } from '..';
import type { AnalysisRunDetail, SnapshotPage, SnapshotRow } from '../types/api';

const reference: HistoricalAnalysisReference = {
  analysisId: 'analysis-history',
  version: 2,
  underlyingId: 'underlying-1',
  modelId: 'EOD_TREND_MOMENTUM',
  modelVersion: '1.0.0',
};
const fetchMock = vi.fn<typeof fetch>();

function run(count = 1): AnalysisRunDetail {
  return {
    analysis: {
      id: reference.analysisId,
      underlying_id: reference.underlyingId,
      listing_id: 'historical-listing',
      created_at: '2025-01-01T00:00:00Z',
      created_by: 'Synthetic test',
    },
    run: {
      version: reference.version,
      status: 'COMPLETED_WITH_WARNINGS',
      quality_status: 'LIMITED',
      model_id: reference.modelId,
      model_version: reference.modelVersion,
      observation_count: count,
      analysis_time: '2025-01-01T00:00:00Z',
      input_hash: 'stored-input-hash',
    },
    parameters: {},
    metrics: {},
    notes: [],
    data_sources: [],
    criteria: [],
    snapshot: [], // The unchanged getRun reader deliberately omits these rows.
  };
}

function row(index = 0, currency = 'USD'): SnapshotRow {
  return {
    trading_date: new Date(Date.UTC(2025, 0, index + 1)).toISOString().slice(0, 10),
    open: '100',
    high: '101',
    low: '99',
    close: '100',
    adjusted_close: null,
    volume: null,
    currency,
    provider: 'STORED_TEST',
    provider_symbol: 'HISTORICAL',
    quality_status: 'VALID',
    warnings: [],
  };
}

function page(items: SnapshotRow[], total = items.length, offset = 0): SnapshotPage {
  return { items, total, offset, limit: 200 };
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function read(signal = new AbortController().signal) {
  return readHistoricalAnalysisCurrency(reference, signal);
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

describe('public historical Analysis currency read', () => {
  it('reads every stored page through the unchanged GET endpoints before returning a value', async () => {
    const rows = Array.from({ length: 401 }, (_, index) => row(index));
    const signal = new AbortController().signal;
    fetchMock
      .mockResolvedValueOnce(json(run(rows.length)))
      .mockResolvedValueOnce(json(page(rows.slice(0, 200), rows.length)))
      .mockResolvedValueOnce(json(page(rows.slice(200, 400), rows.length, 200)))
      .mockResolvedValueOnce(json(page(rows.slice(400), rows.length, 400)));

    await expect(read(signal)).resolves.toEqual({
      currency: 'USD',
      analysisId: reference.analysisId,
      version: reference.version,
      listingId: 'historical-listing',
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      expect.stringContaining('/analysis-history/runs/2?include_snapshot=false'),
      expect.stringContaining('/analysis-history/runs/2/snapshot?offset=0&limit=200'),
      expect.stringContaining('/analysis-history/runs/2/snapshot?offset=200&limit=200'),
      expect.stringContaining('/analysis-history/runs/2/snapshot?offset=400&limit=200'),
    ]);
    for (const [, options] of fetchMock.mock.calls) {
      expect(options).toMatchObject({ method: 'GET', signal });
      expect(options?.body).toBeUndefined();
    }
  });

  it('preserves the exact nonblank stored code and historical model without a current-model lookup', async () => {
    const historical = { ...reference, modelId: 'HISTORICAL_MODEL', modelVersion: '0.9.0' };
    const detail = run();
    detail.run.model_id = historical.modelId;
    detail.run.model_version = historical.modelVersion;
    fetchMock
      .mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(page([row(0, 'uSd')])));

    await expect(
      readHistoricalAnalysisCurrency(historical, new AbortController().signal),
    ).resolves.toMatchObject({ currency: 'uSd' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([
    ['analysis ID', { ...reference, analysisId: '' }],
    ['Underlying ID', { ...reference, underlyingId: ' ' }],
    ['model ID', { ...reference, modelId: '' }],
    ['model version', { ...reference, modelVersion: '' }],
    ['run zero', { ...reference, version: 0 }],
    ['fractional run', { ...reference, version: 1.5 }],
    ['unsafe run', { ...reference, version: Number.MAX_SAFE_INTEGER + 1 }],
  ])('does not read an invalid reference: %s', async (_name, source) => {
    await expect(
      readHistoricalAnalysisCurrency(source, new AbortController().signal),
    ).resolves.toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each<{ name: string; value: unknown }>([
    { name: 'missing response', value: null },
    { name: 'missing analysis', value: { ...run(), analysis: null } },
    { name: 'missing run', value: { ...run(), run: null } },
    {
      name: 'different analysis',
      value: { ...run(), analysis: { ...run().analysis, id: 'other' } },
    },
    {
      name: 'different Underlying',
      value: { ...run(), analysis: { ...run().analysis, underlying_id: 'other' } },
    },
    {
      name: 'missing listing',
      value: { ...run(), analysis: { ...run().analysis, listing_id: null } },
    },
    {
      name: 'blank listing',
      value: { ...run(), analysis: { ...run().analysis, listing_id: ' ' } },
    },
    { name: 'different run', value: { ...run(), run: { ...run().run, version: 3 } } },
    { name: 'different model', value: { ...run(), run: { ...run().run, model_id: 'other' } } },
    {
      name: 'different model version',
      value: { ...run(), run: { ...run().run, model_version: '1.0.1' } },
    },
    { name: 'empty snapshot', value: run(0) },
    { name: 'invalid observation count', value: run(1.5) },
  ])(
    'rejects $name in the actual run response before reading snapshot pages',
    async ({ value }) => {
      fetchMock.mockResolvedValueOnce(json(value));
      await expect(read()).resolves.toBeNull();
      expect(fetchMock).toHaveBeenCalledTimes(1);
    },
  );

  it.each<{ name: string; value: unknown; count?: number }>([
    { name: 'missing page', value: null },
    { name: 'missing rows', value: { ...page([row()]), items: null } },
    { name: 'empty rows', value: page([], 1) },
    { name: 'different total', value: page([row()], 2) },
    { name: 'wrong offset', value: page([row()], 1, 1) },
    { name: 'wrong limit', value: { ...page([row()]), limit: 50 } },
    { name: 'too many rows', value: page([row(0), row(1)], 1) },
    { name: 'blank currency', value: page([row(0, ' ')]) },
    {
      name: 'missing currency',
      value: { ...page([row()]), items: [{ ...row(), currency: null }] },
    },
    { name: 'invalid date', value: page([{ ...row(), trading_date: '2025-02-30' }]) },
    { name: 'repeated date', value: page([row(0), row(0)]), count: 2 },
    { name: 'reversed dates', value: page([row(1), row(0)]), count: 2 },
    { name: 'different currency', value: page([row(0), row(1, 'EUR')]), count: 2 },
    { name: 'different unnormalized code', value: page([row(0), row(1, 'usd')]), count: 2 },
  ])('returns no suggestion for $name', async ({ value, count = 1 }) => {
    fetchMock.mockResolvedValueOnce(json(run(count))).mockResolvedValueOnce(json(value));
    await expect(read()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each<{ name: string; last: unknown }>([
    { name: 'currency conflict', last: page([row(200, 'EUR')], 201, 200) },
    { name: 'replayed offset', last: page([row(200)], 201, 0) },
    { name: 'replayed rows', last: page([row(0)], 201, 200) },
    { name: 'changed total', last: page([row(200)], 202, 200) },
    { name: 'missing final row', last: page([], 201, 200) },
  ])('discards the whole result for a later-page $name', async ({ last }) => {
    fetchMock
      .mockResolvedValueOnce(json(run(201)))
      .mockResolvedValueOnce(
        json(
          page(
            Array.from({ length: 200 }, (_, index) => row(index)),
            201,
          ),
        ),
      )
      .mockResolvedValueOnce(json(last));
    await expect(read()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('rejects a shortened intermediate page without accepting a partial value', async () => {
    fetchMock.mockResolvedValueOnce(json(run(201))).mockResolvedValueOnce(json(page([row()], 201)));
    await expect(read()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('propagates an unavailable later page without retrying or returning the earlier currency', async () => {
    fetchMock
      .mockResolvedValueOnce(json(run(201)))
      .mockResolvedValueOnce(
        json(
          page(
            Array.from({ length: 200 }, (_, index) => row(index)),
            201,
          ),
        ),
      )
      .mockResolvedValueOnce(json({ detail: 'unavailable' }, 503));
    await expect(read()).rejects.toThrow('HTTP 503');
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('does not start a read after abort', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(read(controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('checks abort after the identity read even when the transport returns success', async () => {
    const controller = new AbortController();
    fetchMock.mockImplementationOnce(() => {
      controller.abort();
      return Promise.resolve(json(run()));
    });
    await expect(read(controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not return a proposal when aborted during the final page read', async () => {
    const controller = new AbortController();
    let finish!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      finish = resolve;
    });
    fetchMock
      .mockResolvedValueOnce(json(run(201)))
      .mockResolvedValueOnce(
        json(
          page(
            Array.from({ length: 200 }, (_, index) => row(index)),
            201,
          ),
        ),
      )
      .mockReturnValueOnce(pending);
    const result = read(controller.signal);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    controller.abort();
    finish(json(page([row(200)], 201, 200)));
    await expect(result).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
