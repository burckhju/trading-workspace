import { afterEach, describe, expect, it, vi } from 'vitest';

import { productSelectionApiClient } from './client';

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function requestBody(init: RequestInit | undefined): unknown {
  if (typeof init?.body !== 'string') throw new Error('Expected a JSON string body');
  return JSON.parse(init.body) as unknown;
}

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

describe('productSelectionApiClient', () => {
  afterEach(() => vi.restoreAllMocks());

  it('starts a run with the TradePlan identities only', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ run: { id: 'run-1' } }, 201));

    await productSelectionApiClient.start({
      trade_plan_id: 'plan-1',
      trade_plan_version_id: 'version-1',
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(requestUrl(url)).toContain('/api/v1/product-selection-runs');
    expect(init?.method).toBe('POST');
    expect(requestBody(init)).toEqual({
      trade_plan_id: 'plan-1',
      trade_plan_version_id: 'version-1',
    });
  });

  it('persists an explicit product selection including rationale', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ run: { id: 'run-1' } }, 201));

    await productSelectionApiClient.select('run-1', {
      product_evaluation_id: 'evaluation-1',
      rationale: 'Chosen after comparison',
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(requestUrl(url)).toContain('/api/v1/product-selection-runs/run-1/selection');
    expect(init?.method).toBe('POST');
    expect(requestBody(init)).toEqual({
      product_evaluation_id: 'evaluation-1',
      rationale: 'Chosen after comparison',
    });
  });
});
