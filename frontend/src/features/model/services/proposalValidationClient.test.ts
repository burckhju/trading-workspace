import { afterEach, describe, expect, it, vi } from 'vitest';

import { proposalValidationClient } from './proposalValidationClient';

describe('proposalValidationClient', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('creates a retrospective validation through the existing endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'validation-1',
          proposal_id: 'proposal-1',
          method: 'RETROSPECTIVE',
          evidence_cutoff_at: '2026-08-28T18:00:00Z',
          conclusion: 'SUPPORTS',
          metrics: { expectancy_delta: 0.2 },
          notes: 'Stable across samples',
          created_at: '2026-08-28T18:10:00Z',
          created_by: 'actor-1',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await proposalValidationClient.create('proposal-1', {
      evidence_ids: ['evidence-1'],
      evidence_cutoff_at: '2026-08-28T18:00:00Z',
      conclusion: 'SUPPORTS',
      metrics: { expectancy_delta: 0.2 },
      notes: 'Stable across samples',
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/model-governance/proposals/proposal-1/validations');
    expect(init.method).toBe('POST');
  });
});
