import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import type { ExitReviewDraftRequest } from '../types/api';
import { postTradeApiClient } from './client';

vi.mock('../../market/services/http', () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe('postTradeApiClient', () => {
  beforeEach(() => {
    requestJsonMock.mockResolvedValue(undefined);
  });

  it('uses the FT-011 observation and evidence routes', async () => {
    const signal = new AbortController().signal;

    await postTradeApiClient.startObservation('trade-1');
    await postTradeApiClient.observation('trade-1', signal);
    await postTradeApiClient.evidence('trade-1', signal);

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/api/v1/post-trade/trades/trade-1/observation',
      { method: 'POST' },
    );

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/api/v1/post-trade/trades/trade-1/observation',
      { signal },
    );

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      3,
      'http://localhost:8000/api/v1/post-trade/trades/trade-1/observation/evidence',
      { signal },
    );
  });

  it('uses the complete ExitReview lifecycle routes', async () => {
    const signal = new AbortController().signal;

    const draft: ExitReviewDraftRequest = {
      timing: 'GOOD',
      process_adherence: 'NOT_ASSESSABLE',
      risk_decision: 'ACCEPTABLE',
      overall_exit_decision: 'IMPROVABLE',
      rationale: 'Review rationale',
    };

    await postTradeApiClient.createReviewDraft('trade-1');
    await postTradeApiClient.review('trade-1', signal);
    await postTradeApiClient.updateReviewDraft('trade-1', draft);
    await postTradeApiClient.finalizeReview('trade-1');
    await postTradeApiClient.revalidateReview('trade-1');
    await postTradeApiClient.reviewHistory('trade-1', signal);
    await postTradeApiClient.handoff('trade-1', signal);

    const base = 'http://localhost:8000/api/v1/post-trade/trades/trade-1';

    expect(requestJsonMock).toHaveBeenNthCalledWith(1, `${base}/exit-review`, {
      method: 'POST',
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(2, `${base}/exit-review`, {
      signal,
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(3, `${base}/exit-review/draft`, {
      method: 'PUT',
      body: draft,
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(4, `${base}/exit-review/finalize`, {
      method: 'POST',
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(5, `${base}/exit-review/revalidate`, {
      method: 'POST',
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(6, `${base}/exit-review/history`, {
      signal,
    });

    expect(requestJsonMock).toHaveBeenNthCalledWith(7, `${base}/handoff`, {
      signal,
    });
  });
});
