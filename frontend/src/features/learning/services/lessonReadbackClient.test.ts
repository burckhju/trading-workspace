import { afterEach, describe, expect, it, vi } from 'vitest';

import { lessonReadbackClient } from './lessonReadbackClient';

describe('lessonReadbackClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists Lessons that reference one LearningEvidence', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ lesson_id: 'lesson-1' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await lessonReadbackClient.listForEvidence('evidence-1');

    expect(fetchMock.mock.calls[0]?.[0]).toContain(
      '/api/v1/learning/learning-evidence/evidence-1/lessons',
    );
  });

  it('loads one Lesson detail', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ lesson_id: 'lesson-1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await lessonReadbackClient.getLesson('lesson-1');

    expect(fetchMock.mock.calls[0]?.[0]).toContain('/api/v1/learning/lessons/lesson-1');
  });
});
