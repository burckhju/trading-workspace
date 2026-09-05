import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { tradePlanApiClient } from '../services/client';
import type { TradePlanDetailResponse, TradePlanStatus, TradePlanVersionResponse } from '../types/api';
import { ExistingTradePlanPage } from './ExistingTradePlanPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn() },
}));

vi.mock('../services/client', () => ({
  tradePlanApiClient: {
    get: vi.fn(),
    versions: vi.fn(),
    submitForReview: vi.fn(),
    approve: vi.fn(),
    abandon: vi.fn(),
  },
}));

const getPlan = vi.mocked(tradePlanApiClient.get);
const getVersions = vi.mocked(tradePlanApiClient.versions);
const abandon = vi.mocked(tradePlanApiClient.abandon);
const getUnderlying = vi.mocked(marketApiClient.getUnderlying);

function version(status: TradePlanStatus): TradePlanVersionResponse {
  return {
    id: 'version-1',
    trade_plan_id: 'plan-1',
    version: 1,
    direction: 'LONG',
    thesis: 'Trendfortsetzung',
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
    risk_assumptions: {
      thesis_risk: 'Trendbruch',
      max_loss_assumption: null,
      notes: null,
    },
    status,
    created_at: '2026-09-05T10:00:00Z',
    created_by: 'actor-1',
    previous_version_id: null,
    change_reason: null,
    candidate_evaluation: null,
    approval: null,
    events: [],
  };
}

function detail(status: TradePlanStatus): TradePlanDetailResponse {
  return {
    plan: {
      id: 'plan-1',
      underlying_id: 'underlying-1',
      origin_type: 'MANUAL',
      candidate_id: null,
      candidate_evaluation_id: null,
      created_at: '2026-09-05T10:00:00Z',
      created_by: 'actor-1',
    },
    latest_version: version(status),
  };
}

describe('ExistingTradePlanPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getUnderlying.mockRejectedValue(new Error('optional context unavailable'));
    abandon.mockResolvedValue(version('ABANDONED'));
  });

  it('allows a draft TradePlan to be abandoned and reloads the authoritative state', async () => {
    getPlan.mockResolvedValueOnce(detail('DRAFT')).mockResolvedValue(detail('ABANDONED'));
    getVersions
      .mockResolvedValueOnce([version('DRAFT')])
      .mockResolvedValue([version('ABANDONED')]);

    render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );

    const button = await screen.findByRole('button', { name: 'TradePlan aufgeben' });
    fireEvent.click(button);

    await waitFor(() => expect(abandon).toHaveBeenCalledWith('plan-1', 'version-1'));
    expect(await screen.findByText('Version 1 · ABANDONED')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'TradePlan aufgeben' })).not.toBeInTheDocument();
  });

  it('does not offer abandon for an approved TradePlan', async () => {
    getPlan.mockResolvedValue(detail('APPROVED'));
    getVersions.mockResolvedValue([version('APPROVED')]);

    render(
      <MemoryRouter>
        <ExistingTradePlanPage tradePlanId="plan-1" />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Version 1 · APPROVED')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'TradePlan aufgeben' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl starten' })).toBeInTheDocument();
  });
});
