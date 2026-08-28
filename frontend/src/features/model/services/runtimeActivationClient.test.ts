import { afterEach, describe, expect, it, vi } from 'vitest';

import { runtimeActivationClient } from './runtimeActivationClient';

describe('runtimeActivationClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reads current runtime activation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('null', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await runtimeActivationClient.getCurrent('model-1');

    expect(fetchMock.mock.calls[0]?.[0]).toContain('/models/model-1/runtime-activation');
  });

  it('activates approved version with optional correlation id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'activation-1',
          model_id: 'model-1',
          model_version_id: 'version-2',
          activated_at: '2026-08-28T20:00:00Z',
          activated_by: 'actor-1',
          correlation_id: 'corr-1',
          model_version: {
            id: 'version-2',
            model_id: 'model-1',
            version: 2,
            status: 'APPROVED',
            definition: {},
            change_summary: 'change',
            created_at: '2026-08-28T19:00:00Z',
            created_by: 'actor-1',
            previous_version_id: 'version-1',
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await runtimeActivationClient.activate('model-1', 'version-2', 'corr-1');

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(fetchMock.mock.calls[0]?.[0]).toContain('/models/model-1/versions/version-2/activate');
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('X-Correlation-ID')).toBe('corr-1');
  });
});
