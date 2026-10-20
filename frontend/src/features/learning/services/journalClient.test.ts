import { afterEach, expect, it, vi } from 'vitest';
import { journalClient } from './journalClient';
vi.mock('../../../services/environment', () => ({
  environment: { apiBaseUrl: 'https://synthetic.invalid' },
}));
vi.mock('../../../services/identity/requestIdentity', () => ({ getRequestIdentity: () => ({}) }));
afterEach(() => vi.unstubAllGlobals());
it('pins revision, exact source and command key once, retaining a structured conflict', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        code: 'JOURNAL_CONFLICT',
        message: 'Saved draft changed',
        details: [],
        timestamp: '2026-10-14T12:00:00Z',
      }),
      { status: 409 },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  await expect(
    journalClient.command(
      'trade',
      {
        operation: 'FINALIZE',
        version_id: 'j1',
        expected_edit_revision: 4,
        expected_exit_review_version_id: 'r1',
        confirmed: true,
      },
      'key',
    ),
  ).rejects.toMatchObject({ status: 409, response: { code: 'JOURNAL_CONFLICT' } });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe('https://synthetic.invalid/api/v1/learning/trades/trade/journal/commands');
  expect(new Headers(init.headers).get('Idempotency-Key')).toBe('key');
  expect(JSON.parse(init.body as string)).toEqual({
    operation: 'FINALIZE',
    version_id: 'j1',
    expected_edit_revision: 4,
    expected_exit_review_version_id: 'r1',
    confirmed: true,
  });
});
it('reads history and a concrete historical version without writes', async () => {
  const fetchMock = vi
    .fn<(url: string, options: RequestInit) => Promise<Response>>()
    .mockImplementation(() => Promise.resolve(new Response('{}')));
  vi.stubGlobal('fetch', fetchMock);
  const signal = new AbortController().signal;
  await journalClient.history('trade', signal);
  await journalClient.version('old-version', signal);
  expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
    'https://synthetic.invalid/api/v1/learning/trades/trade/journal',
    'https://synthetic.invalid/api/v1/learning/journal-versions/old-version',
  ]);
  for (const [, init] of fetchMock.mock.calls) {
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
    expect(init.signal).toBe(signal);
  }
});
