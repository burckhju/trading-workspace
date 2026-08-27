import { afterEach, describe, expect, it, vi } from 'vitest';

import { lessonDraftClient } from './lessonDraftClient';

describe('lessonDraftClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('creates a Lesson with the materialized evidence as SUPPORTS', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          lesson_id: 'lesson-1',
          current_version_id: 'version-1',
          version: 1,
          current_state: 'CURRENT',
          title: 'Discipline',
          main_category: 'Execution',
          content: 'Wait for confirmation.',
          evidence: [],
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await lessonDraftClient.createFromEvidence('evidence-1', {
      title: 'Discipline',
      main_category: 'Execution',
      content: 'Wait for confirmation.',
      tags: [],
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      title: 'Discipline',
      main_category: 'Execution',
      content: 'Wait for confirmation.',
      tags: [],
      evidence_links: [
        {
          learning_evidence_id: 'evidence-1',
          relation: 'SUPPORTS',
        },
      ],
    });
  });
});
