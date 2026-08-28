import { afterEach, describe, expect, it, vi } from 'vitest';

import { hypothesisProposalClient } from './hypothesisProposalClient';

describe('hypothesisProposalClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('creates a DRAFT proposal through the existing governance endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'proposal-1',
          model_id: 'model-1',
          base_model_version_id: 'version-1',
          hypothesis_id: 'hypothesis-1',
          status: 'DRAFT',
          proposed_definition: { threshold: 2 },
          rationale: 'Tighten selectivity',
          created_at: '2026-08-28T18:00:00Z',
          created_by: 'actor-1',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await hypothesisProposalClient.create({
      model_id: 'model-1',
      base_model_version_id: 'version-1',
      hypothesis_id: 'hypothesis-1',
      proposed_definition: { threshold: 2 },
      rationale: 'Tighten selectivity',
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/model-governance/proposals');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      model_id: 'model-1',
      base_model_version_id: 'version-1',
      hypothesis_id: 'hypothesis-1',
      proposed_definition: { threshold: 2 },
      rationale: 'Tighten selectivity',
    });
  });
});
