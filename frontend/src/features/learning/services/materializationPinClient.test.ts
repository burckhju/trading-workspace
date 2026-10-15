import { afterEach, describe, expect, it, vi } from 'vitest';

import { ft011MaterializationClient } from './materializationClient';

vi.mock('../../../services/environment', () => ({
  environment: { apiBaseUrl: 'https://synthetic.invalid' },
}));
vi.mock('../../../services/identity/requestIdentity', () => ({
  getRequestIdentity: () => ({}),
}));

function captureRequest() {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        learning_evidence_id: 'evidence-1',
        exit_review_version_id: 'version-1',
        created: true,
        replayed: false,
      }),
      { status: 200 },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe('FT-011 explicit version request on the wire', () => {
  it('serializes the confirmed version exactly once with the existing HTTP helper', async () => {
    const fetchMock = captureRequest();
    await ft011MaterializationClient.materialize('trade-1', 'pinned-key', 'version-1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      'https://synthetic.invalid/api/v1/learning/trades/trade-1/ft011-evidence/materialize',
    );
    expect(request.method).toBe('POST');
    expect(new Headers(request.headers).get('Content-Type')).toBe('application/json');
    expect(new Headers(request.headers).get('Idempotency-Key')).toBe('pinned-key');
    expect(JSON.parse(request.body as string)).toEqual({
      expected_exit_review_version_id: 'version-1',
    });
  });

  it('retains the bodyless legacy request', async () => {
    const fetchMock = captureRequest();
    await ft011MaterializationClient.materialize('trade-1', 'legacy-key');
    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(request.body).toBeUndefined();
    expect(new Headers(request.headers).get('Idempotency-Key')).toBe('legacy-key');
  });

  it('retains cancellation for read-only status requests', async () => {
    const fetchMock = captureRequest();
    const controller = new AbortController();
    await ft011MaterializationClient.status('trade-1', controller.signal);
    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(request.method).toBe('GET');
    expect(request.body).toBeUndefined();
    expect(request.signal).toBe(controller.signal);
  });
});
