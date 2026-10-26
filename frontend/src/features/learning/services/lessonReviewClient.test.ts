import { afterEach, expect, it, vi } from 'vitest';
import { evidenceLabel, lessonReviewClient, type ReviewCommand } from './lessonReviewClient';
vi.mock('../../../services/environment', () => ({
  environment: { apiBaseUrl: 'https://synthetic.invalid' },
}));
vi.mock('../../../services/identity/requestIdentity', () => ({ getRequestIdentity: () => ({}) }));
afterEach(() => vi.unstubAllGlobals());
it('pins exact state, version, open signal, interpretation, relations and idempotency key once', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        code: 'LESSON_REVIEW_CONFLICT',
        message: 'Changed context',
        details: [],
        timestamp: '2026-10-15T00:00:00Z',
      }),
      { status: 409 },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  const command: ReviewCommand = {
    operation: 'NEW_VERSION',
    expected_current_version_id: 'v1',
    expected_current_state: 'REVIEW_RECOMMENDED',
    expected_open_signal_id: 's1',
    reason: 'Explicit',
    confirmed: true,
    content: 'My interpretation',
    main_category: 'Process',
    evidence: [
      { learning_evidence_id: 'e1', relation: 'SUPPORTS' },
      { learning_evidence_id: 'e2', relation: 'CONTRADICTS' },
      { learning_evidence_id: 'e3', relation: 'CONTEXTUAL' },
    ],
  };
  await expect(lessonReviewClient.execute('l1', command, 'once')).rejects.toMatchObject({
    status: 409,
    response: { code: 'LESSON_REVIEW_CONFLICT' },
  });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe('https://synthetic.invalid/api/v1/learning/lessons/l1/review-commands');
  expect(init.method).toBe('POST');
  expect(JSON.parse(init.body as string)).toEqual(command);
  expect(new Headers(init.headers).get('Idempotency-Key')).toBe('once');
});
it('retains the explicit null signal pin and the complete evidence set for source review', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        lesson_id: 'l1',
        result_id: 'transition',
        result_type: 'LESSON_STATE_TRANSITION',
        replayed: false,
      }),
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  const command: ReviewCommand = {
    operation: 'OPEN_SOURCE_REVIEW',
    expected_current_version_id: 'v1',
    expected_current_state: 'CURRENT',
    expected_open_signal_id: null,
    reason: 'Explicit full-source review',
    confirmed: true,
    reviewed_evidence_ids: ['supports', 'contradicts', 'context'],
  };
  await lessonReviewClient.execute('l1', command, 'source-once');
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(JSON.parse(init.body as string)).toEqual(command);
  expect(new Headers(init.headers).get('Idempotency-Key')).toBe('source-once');
});
it('history, catalog and exact-source inspection are read only and forward abort signal', async () => {
  const fetchMock = vi
    .fn<(url: string, init: RequestInit) => Promise<Response>>()
    .mockImplementation(() => Promise.resolve(new Response('{}')));
  vi.stubGlobal('fetch', fetchMock);
  const signal = new AbortController().signal;
  await lessonReviewClient.context('l1', signal);
  await lessonReviewClient.evidence(signal);
  await lessonReviewClient.source('e1', signal);
  expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
    'https://synthetic.invalid/api/v1/learning/lessons/l1/review-context',
    'https://synthetic.invalid/api/v1/learning/learning-evidence',
    'https://synthetic.invalid/api/v1/learning/learning-evidence/e1/currentness',
  ]);
  for (const [, init] of fetchMock.mock.calls) {
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
    expect(init.signal).toBe(signal);
  }
});
it('all supported source labels retain concrete version and materialization date; unknown is explicit', () => {
  for (const field of [
    'trade_journal_version_id',
    'exit_review_version_id',
    'external_observation_version_id',
    'external_observation_journal_version_id',
  ])
    expect(
      evidenceLabel({
        evidence_id: 'e',
        source_type: 'type',
        source: { type: 'type', [field]: 'exact-v' },
        created_at: 'captured',
      }),
    ).toBe('type · exact-v · erfasst captured');
  expect(
    evidenceLabel({
      evidence_id: 'e',
      source_type: 'type',
      source: { type: 'type' },
      created_at: 'captured',
    }),
  ).toContain('Quelle unbekannt');
});
