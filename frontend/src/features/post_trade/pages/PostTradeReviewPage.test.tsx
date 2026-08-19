import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { postTradeApiClient } from '../services/client';
import type {
  ExitReviewResponse,
  HandoffResponse,
  ObservationEvidenceResponse,
  ObservationResponse,
} from '../types/api';
import { PostTradeReviewPage } from './PostTradeReviewPage';

vi.mock('../services/client', () => ({
  postTradeApiClient: {
    startObservation: vi.fn(),
    observation: vi.fn(),
    evidence: vi.fn(),
    createReviewDraft: vi.fn(),
    review: vi.fn(),
    updateReviewDraft: vi.fn(),
    finalizeReview: vi.fn(),
    revalidateReview: vi.fn(),
    reviewHistory: vi.fn(),
    handoff: vi.fn(),
  },
}));

const api = vi.mocked(postTradeApiClient);

const observation: ObservationResponse = {
  id: 'observation-1',
  trade_id: 'trade-1',
  status: 'ACTIVE',
  underlying_listing_id: 'listing-1',
  target_observation_count: 20,
  available_observation_count: 13,
  missing_observation_count: 7,
  is_complete: false,
  started_at: '2026-08-18T12:00:00Z',
  completed_at: null,
  created_at: '2026-08-18T12:00:00Z',
};

const evidence: ObservationEvidenceResponse = {
  observation_id: 'observation-1',
  trade_id: 'trade-1',
  product_context: {
    warrant_id: 'warrant-1',
    underlying_id: 'underlying-1',
    historical_warrant_terms_version_id: 'terms-1',
    maturity_date: '2026-09-30',
    historical_underlying_listing_id: 'listing-1',
  },
  planning_context: {
    trade_plan_id: 'plan-1',
    trade_plan_version_id: 'plan-version-1',
    original_stop: '90',
    original_targets: ['120'],
  },
  management_levels: [
    {
      event_id: 'event-1',
      kind: 'STOP_CHANGED',
      effective_at: '2026-08-18T13:00:00Z',
      numeric_value: '95',
    },
  ],
  actual_exit: {
    full_exit_at: '2026-08-18T10:00:00Z',
    realized_gross_pnl: '125.50',
    executions: [
      {
        execution_id: 'execution-1',
        quantity: '10',
        price_per_unit: '2.50',
        executed_at: '2026-08-18T10:00:00Z',
      },
    ],
  },
  counterfactual: {
    available_observation_count: 13,
    target_observation_count: 20,
    horizon_complete: false,
    points: [],
    highest_high: { trading_date: '2026-08-25', value: '130' },
    lowest_low: { trading_date: '2026-08-20', value: '85' },
    final_close: { trading_date: '2026-08-29', value: '110' },
    target_crossings: [
      {
        level: '120',
        crossed: true,
        first_crossed_on: '2026-08-25',
      },
    ],
    stop_crossing: {
      level: '90',
      crossed: true,
      first_crossed_on: '2026-08-20',
    },
  },
};

const handoff: HandoffResponse = {
  ready: false,
  reason: 'OBSERVATION_NOT_COMPLETE',
  post_trade_observation_id: 'observation-1',
  exit_review_id: null,
  exit_review_version_id: null,
};

const draft: ExitReviewResponse = {
  exit_review_id: 'review-1',
  current_version_id: 'version-1',
  version: 1,
  status: 'DRAFT',
  currentness: 'CURRENT',
  timing: 'GOOD',
  process_adherence: 'ACCEPTABLE',
  risk_decision: 'GOOD',
  overall_exit_decision: 'IMPROVABLE',
  rationale: 'Draft rationale',
  created_at: '2026-08-18T12:00:00Z',
  created_by: 'actor-1',
  finalized_at: null,
  finalized_by: null,
  supersedes_version_id: null,
  stale_at: null,
  stale_reason: null,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
      <PostTradeReviewPage />
    </MemoryRouter>,
  );
}

describe('PostTradeReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    api.observation.mockResolvedValue(observation);
    api.evidence.mockResolvedValue(evidence);
    api.handoff.mockResolvedValue(handoff);
    api.reviewHistory.mockResolvedValue([]);
    api.review.mockRejectedValue(new Error('not found'));

    api.startObservation.mockResolvedValue(observation);
    api.createReviewDraft.mockResolvedValue(draft);
    api.updateReviewDraft.mockResolvedValue(draft);
    api.finalizeReview.mockResolvedValue({
      ...draft,
      status: 'FINALIZED',
      finalized_at: '2026-08-18T14:00:00Z',
      finalized_by: 'actor-1',
    });
    api.revalidateReview.mockResolvedValue(draft);
  });

  it('shows 13/20 progress and separates Actual from Counterfactual evidence', async () => {
    renderPage();

    expect(await screen.findByText('13/20')).toBeInTheDocument();
    expect(screen.getByText('Tatsächlicher Exit')).toBeInTheDocument();
    expect(screen.getByText('Underlying-Nachbeobachtung')).toBeInTheDocument();
  });

  it('shows COMPLETED at 20/20', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
      completed_at: '2026-09-15T12:00:00Z',
    });

    api.evidence.mockResolvedValue({
      ...evidence,
      counterfactual: {
        ...evidence.counterfactual,
        available_observation_count: 20,
        horizon_complete: true,
      },
    });

    renderPage();

    expect(await screen.findByText('20/20')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'COMPLETED' })).toBeInTheDocument();
  });

  it('shows the maturity boundary notice', async () => {
    renderPage();

    expect(
      await screen.findByText(
        /Warrant-Maturity begrenzt nicht die 20 Underlying-EOD-Beobachtungen/,
      ),
    ).toBeInTheDocument();
  });

  it('loads and saves a draft including NOT_ASSESSABLE', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });

    api.review.mockResolvedValue({
      ...draft,
      process_adherence: 'NOT_ASSESSABLE',
    });

    renderPage();

    expect(await screen.findByText('Version 1')).toBeInTheDocument();

    const selects = screen.getAllByRole('combobox');
    expect(selects[1]).toHaveValue('NOT_ASSESSABLE');

    fireEvent.change(screen.getByLabelText('Review-Begründung'), {
      target: { value: 'Updated rationale' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Entwurf speichern' }));

    await waitFor(() =>
      expect(api.updateReviewDraft).toHaveBeenCalledWith(
        'trade-1',
        expect.objectContaining({
          process_adherence: 'NOT_ASSESSABLE',
          rationale: 'Updated rationale',
        }),
      ),
    );
  });

  it('does not finalize with an empty rationale', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });

    api.review.mockResolvedValue({
      ...draft,
      rationale: '',
    });

    renderPage();

    const button = await screen.findByRole('button', {
      name: 'Review finalisieren',
    });

    expect(button).toBeDisabled();

    fireEvent.click(button);

    expect(api.finalizeReview).not.toHaveBeenCalled();
  });

  it('renders a finalized review as read-only', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });

    api.review.mockResolvedValue({
      ...draft,
      status: 'FINALIZED',
      finalized_at: '2026-08-18T14:00:00Z',
      finalized_by: 'actor-1',
    });

    renderPage();

    expect(
      await screen.findByText('Finalisierte Reviews sind schreibgeschützt.'),
    ).toBeInTheDocument();

    expect(screen.queryByRole('button', { name: 'Entwurf speichern' })).not.toBeInTheDocument();
  });

  it('shows STALE state and revalidation action', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });

    api.review.mockResolvedValue({
      ...draft,
      status: 'FINALIZED',
      currentness: 'STALE',
      stale_at: '2026-08-19T10:00:00Z',
      stale_reason: 'INPUT_CHANGED',
    });

    renderPage();

    expect(await screen.findByText(/Dieser Review ist STALE/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Review erneut prüfen' }));

    await waitFor(() => expect(api.revalidateReview).toHaveBeenCalledWith('trade-1'));
  });

  it('keeps historical review versions visible', async () => {
    api.reviewHistory.mockResolvedValue([
      {
        ...draft,
        version: 1,
        current_version_id: 'version-1',
        status: 'FINALIZED',
        rationale: 'Historical rationale',
      },
      {
        ...draft,
        version: 2,
        current_version_id: 'version-2',
        rationale: 'Current rationale',
      },
    ]);

    renderPage();

    expect(await screen.findByText('Review-Historie')).toBeInTheDocument();
    expect(screen.getByText('Historical rationale')).toBeInTheDocument();
    expect(screen.getByText('Current rationale')).toBeInTheDocument();
  });
});
