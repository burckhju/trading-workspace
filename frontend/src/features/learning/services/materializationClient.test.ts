import { afterEach, describe, expect, it, vi } from 'vitest';

import { ft011MaterializationClient } from './materializationClient';

describe('ft011MaterializationClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reads the materialization status for a trade', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ready: true,
          reason: 'READY',
          materialized: false,
          learning_evidence_id: null,
          exit_review_version_id: 'version-1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await ft011MaterializationClient.status('trade-1');

    expect(result.ready).toBe(true);
    expect(result.materialized).toBe(false);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/learning/trades/trade-1/ft011-evidence/materialization-status');
    expect(init.method).toBe('GET');
  });

  it('materializes with the explicit idempotency header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          learning_evidence_id: 'learning-evidence-1',
          exit_review_version_id: 'version-1',
          created: true,
          replayed: false,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await ft011MaterializationClient.materialize('trade-1', 'materialize-1');

    expect(result.created).toBe(true);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/learning/trades/trade-1/ft011-evidence/materialize');
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('Idempotency-Key')).toBe('materialize-1');
  });
});
