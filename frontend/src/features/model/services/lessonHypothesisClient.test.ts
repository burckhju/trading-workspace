import { afterEach, describe, expect, it, vi } from 'vitest';

import { lessonHypothesisClient } from './lessonHypothesisClient';

describe('lessonHypothesisClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reads hypotheses for the exact LessonVersion', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await lessonHypothesisClient.listForLessonVersion('lesson-version-1');

    expect(fetchMock.mock.calls[0]?.[0]).toContain(
      '/api/v1/model-governance/lesson-versions/lesson-version-1/hypotheses',
    );
  });

  it('creates a hypothesis with explicit user-authored content', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'hypothesis-1',
          title: 'Exit discipline',
          statement: 'Late exits reduce expectancy.',
          status: 'OPEN',
          source_lesson_version_id: 'lesson-version-1',
          created_at: '2026-08-28T12:00:00Z',
          created_by: 'actor-1',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await lessonHypothesisClient.createFromLessonVersion('lesson-version-1', {
      title: 'Exit discipline',
      statement: 'Late exits reduce expectancy.',
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      title: 'Exit discipline',
      statement: 'Late exits reduce expectancy.',
    });
  });
});
