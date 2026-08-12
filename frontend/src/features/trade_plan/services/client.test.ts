import { requestJson } from '../../market/services/http';
import { tradePlanApiClient } from './client';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));

const requestJsonMock = vi.mocked(requestJson);
const PLAN_ID = '11111111-1111-4111-8111-111111111111';
const VERSION_ID = '22222222-2222-4222-8222-222222222222';

const content = {
  thesis: 'Trend continuation',
  entry: { type: 'PRICE' as const, currency: 'EUR', price: '100' },
  invalidation: { stop_price: '95', invalidation_rule: 'Close below support' },
  targets: [{ sequence: 1, price: '110' }],
  risk_assumptions: { thesis_risk: 'Breakout may fail' },
};

describe('tradePlanApiClient', () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    requestJsonMock.mockResolvedValue({});
  });

  it('creates manual plans without candidate provenance', async () => {
    const request = { origin_type: 'MANUAL' as const, underlying_id: PLAN_ID, ...content };
    await tradePlanApiClient.create(request, { correlationId: 'corr-create' });

    expect(requestJsonMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/trade-plans', {
      method: 'POST',
      body: request,
      correlationId: 'corr-create',
    });
  });

  it('creates candidate plans without a client supplied underlying', async () => {
    const request = {
      origin_type: 'CANDIDATE_EVALUATION' as const,
      candidate_id: PLAN_ID,
      candidate_evaluation_id: VERSION_ID,
      ...content,
    };
    await tradePlanApiClient.create(request);

    expect(requestJsonMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/trade-plans', {
      method: 'POST',
      body: request,
      correlationId: undefined,
    });
    expect(request).not.toHaveProperty('underlying_id');
  });

  it('uses exact version resource paths for read and amendment', async () => {
    await tradePlanApiClient.version(PLAN_ID, VERSION_ID);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      `http://localhost:8000/api/v1/trade-plans/${PLAN_ID}/versions/${VERSION_ID}`,
      { signal: undefined },
    );

    await tradePlanApiClient.amend(PLAN_ID, VERSION_ID, {
      ...content,
      change_reason: 'Raise stop',
    });
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      `http://localhost:8000/api/v1/trade-plans/${PLAN_ID}/versions/${VERSION_ID}/amendments`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('maps all lifecycle commands and correlation ids', async () => {
    await tradePlanApiClient.submitForReview(PLAN_ID, VERSION_ID, { correlationId: 'corr-review' });
    expect(requestJsonMock).toHaveBeenLastCalledWith(expect.stringContaining('/submit-review'), {
      method: 'POST',
      body: undefined,
      correlationId: 'corr-review',
    });

    await tradePlanApiClient.returnToDraft(PLAN_ID, VERSION_ID, { reason: 'Revise entry' });
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/return-draft'),
      expect.objectContaining({ body: { reason: 'Revise entry' } }),
    );

    await tradePlanApiClient.abandon(PLAN_ID, VERSION_ID, { reason: 'Setup invalid' });
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/abandon'),
      expect.objectContaining({ body: { reason: 'Setup invalid' } }),
    );

    await tradePlanApiClient.approve(PLAN_ID, VERSION_ID);
    expect(requestJsonMock).toHaveBeenLastCalledWith(expect.stringContaining('/approve'), {
      method: 'POST',
      body: undefined,
      correlationId: undefined,
    });
  });
});
