import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { tradePlanApiClient } from '../services/client';
import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';
import { TradePlanPage } from './TradePlanPage';

vi.mock('../services/client', () => ({
  tradePlanApiClient: {
    create: vi.fn(),
    get: vi.fn(),
    versions: vi.fn(),
    submitForReview: vi.fn(),
    approve: vi.fn(),
    returnToDraft: vi.fn(),
    abandon: vi.fn(),
  },
}));

const mockedClient = vi.mocked(tradePlanApiClient);
const planId = '11111111-1111-4111-8111-111111111111';

const version: TradePlanVersionResponse = {
  id: '22222222-2222-4222-8222-222222222222',
  trade_plan_id: planId,
  version: 1,
  direction: 'LONG',
  thesis: 'Deep-link plan',
  entry: {
    type: 'PRICE',
    currency: 'EUR',
    price: '100',
    price_from: null,
    price_to: null,
    trigger: null,
    reference_price: null,
    valid_until: null,
    rationale: null,
  },
  invalidation: { stop_price: '95', invalidation_rule: null, rationale: null },
  targets: [{ sequence: 1, price: '110', rationale: null }],
  risk_assumptions: { thesis_risk: 'False breakout', max_loss_assumption: null, notes: null },
  status: 'READY_FOR_REVIEW',
  created_at: '2026-09-05T10:00:00Z',
  created_by: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  previous_version_id: null,
  change_reason: null,
  candidate_evaluation: null,
  approval: null,
  events: [],
};

const detail: TradePlanDetailResponse = {
  plan: {
    id: planId,
    underlying_id: '99999999-9999-4999-8999-999999999999',
    origin_type: 'MANUAL',
    candidate_id: null,
    candidate_evaluation_id: null,
    created_at: '2026-09-05T09:55:00Z',
    created_by: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  },
  latest_version: version,
};

describe('TradePlanPage deep link', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.get.mockResolvedValue(detail);
    mockedClient.versions.mockResolvedValue([version]);
  });

  it('loads trade_plan_id and history directly from the URL', async () => {
    render(
      <MemoryRouter initialEntries={[`/trade-plans?trade_plan_id=${planId}`]}>
        <TradePlanPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(mockedClient.get).toHaveBeenCalledWith(planId));
    expect(mockedClient.versions).toHaveBeenCalledWith(planId);
    expect(await screen.findByRole('heading', { name: 'TP-11111111' })).toBeInTheDocument();
    expect(screen.getByLabelText('TradePlan-ID')).toHaveValue(planId);
    expect(screen.getAllByText('READY_FOR_REVIEW').length).toBeGreaterThan(0);
  });
});
