import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { candidateApiClient } from './client';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const mockedRequestJson = vi.mocked(requestJson);

describe('candidateApiClient', () => {
  beforeEach(() => {
    mockedRequestJson.mockReset();
    mockedRequestJson.mockResolvedValue({} as never);
  });

  it('covers candidate API methods', async () => {
    const controller = new AbortController();
    await candidateApiClient.list(controller.signal);
    await candidateApiClient.evaluations('candidate-1', controller.signal);
    await candidateApiClient.liveWorkflow('candidate-1', controller.signal);
    await candidateApiClient.evaluateAuto('candidate-1');

    expect(mockedRequestJson).toHaveBeenCalledTimes(4);
    expect(mockedRequestJson.mock.calls[0]?.[0]).toMatch(/\/api\/v1\/candidates$/);
    expect(mockedRequestJson.mock.calls[1]?.[0]).toContain('/candidate-1/evaluations');
    expect(mockedRequestJson.mock.calls[2]?.[0]).toContain('/candidate-1/live-workflow');
    expect(mockedRequestJson.mock.calls[3]?.[1]).toEqual({ method: 'POST', body: {} });
  });
});
