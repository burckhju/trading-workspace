import { afterEach, describe, expect, it, vi } from 'vitest';

import { proposalApprovalClient } from './proposalApprovalClient';

describe('proposalApprovalClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reads proposal approval', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('null', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await proposalApprovalClient.getForProposal('proposal-1');

    expect(fetchMock.mock.calls[0]?.[0]).toContain('/proposals/proposal-1/approval');
  });

  it('approves with optional correlation id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          model_version: {
            id: 'version-2',
            model_id: 'model-1',
            version: 2,
            status: 'APPROVED',
            definition: { threshold: 2 },
            change_summary: 'Tighten selectivity',
            created_at: '2026-08-28T19:00:00Z',
            created_by: 'actor-1',
            previous_version_id: 'version-1',
          },
          approval: {
            id: 'approval-1',
            proposal_id: 'proposal-1',
            model_version_id: 'version-2',
            approved_at: '2026-08-28T19:00:00Z',
            approved_by: 'actor-1',
            correlation_id: 'corr-1',
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await proposalApprovalClient.approve('proposal-1', 'corr-1');

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('X-Correlation-ID')).toBe('corr-1');
  });
});
