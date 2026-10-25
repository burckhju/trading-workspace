import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useLayoutEffect, useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import { postTradeApiClient } from '../services/client';
import type {
  ExitReviewResponse,
  HandoffResponse,
  ObservationEvidenceResponse,
  ObservationResponse,
} from '../types/api';
import { PostTradeReviewPage } from './PostTradeReviewPage';

vi.mock('../../learning/services/materializationClient', () => ({
  ft011MaterializationClient: {
    status: vi.fn(),
    materialize: vi.fn(),
  },
}));

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
const materializationApi = vi.mocked(ft011MaterializationClient);

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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

describe('PostTradeReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    api.observation.mockResolvedValue(observation);
    api.evidence.mockResolvedValue(evidence);
    api.handoff.mockResolvedValue(handoff);
    api.reviewHistory.mockResolvedValue([]);
    api.review.mockRejectedValue(new Error('not found'));

    materializationApi.status.mockResolvedValue({
      ready: false,
      reason: 'OBSERVATION_NOT_COMPLETE',
      materialized: false,
      learning_evidence_id: null,
      exit_review_version_id: null,
    });
    materializationApi.materialize.mockResolvedValue({
      learning_evidence_id: 'learning-evidence-1',
      exit_review_version_id: 'version-1',
      created: true,
      replayed: false,
    });

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

  it('keeps materialization disabled until the FT-011 handoff is ready', async () => {
    renderPage();

    const button = await screen.findByRole('button', {
      name: 'Als LearningEvidence materialisieren',
    });

    expect(button).toBeDisabled();
    expect(materializationApi.materialize).not.toHaveBeenCalled();
  });

  it('materializes READY FT-011 evidence and refreshes the status', async () => {
    api.handoff.mockResolvedValue({
      ready: true,
      reason: 'READY',
      post_trade_observation_id: 'observation-1',
      exit_review_id: 'review-1',
      exit_review_version_id: 'version-1',
    });
    materializationApi.status
      .mockResolvedValueOnce({
        ready: true,
        reason: 'READY',
        materialized: false,
        learning_evidence_id: null,
        exit_review_version_id: 'version-1',
      })
      .mockResolvedValue({
        ready: true,
        reason: 'READY',
        materialized: true,
        learning_evidence_id: 'learning-evidence-1',
        exit_review_version_id: 'version-1',
      });

    renderPage();

    const button = await screen.findByRole('button', {
      name: 'Als LearningEvidence materialisieren',
    });
    expect(button).toBeEnabled();

    fireEvent.click(button);

    await waitFor(() => expect(materializationApi.materialize).toHaveBeenCalledTimes(1));
    expect(materializationApi.materialize).toHaveBeenCalledWith(
      'trade-1',
      'ft011-to-ft012:v2:trade-1:version-1',
      'version-1',
    );
    expect(await screen.findByText('MATERIALIZED')).toBeInTheDocument();
    expect(screen.getByText('learning-evidence-1')).toBeInTheDocument();
  });

  it('notifies the Learning consumer after finalization without materializing evidence', async () => {
    const onLearningStateChanged = vi.fn();
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });
    api.review.mockResolvedValue(draft);
    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage onLearningStateChanged={onLearningStateChanged} />
      </MemoryRouter>,
    );
    const button = await screen.findByRole('button', { name: 'Review finalisieren' });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    await waitFor(() => expect(onLearningStateChanged).toHaveBeenCalledTimes(1));
    expect(api.finalizeReview).toHaveBeenCalledWith('trade-1');
    expect(materializationApi.materialize).not.toHaveBeenCalled();
  });

  it('checks a finalized review explicitly and creates a successor only on a separate action', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      available_observation_count: 20,
      missing_observation_count: 0,
      is_complete: true,
    });
    const final: ExitReviewResponse = {
      ...draft,
      status: 'FINALIZED',
      finalized_at: '2026-09-15T12:00:00Z',
      finalized_by: 'actor-1',
    };
    api.review.mockResolvedValue(final);
    renderPage();
    const check = await screen.findByRole('button', { name: 'Review-Quellenstand prüfen' });
    await waitFor(() => expect(check).toBeEnabled());
    expect(api.revalidateReview).not.toHaveBeenCalled();
    expect(api.createReviewDraft).not.toHaveBeenCalled();
    const stale: ExitReviewResponse = {
      ...final,
      currentness: 'STALE',
      stale_reason: 'INPUT_CHANGED',
    };
    api.revalidateReview.mockResolvedValue(stale);
    api.review.mockResolvedValue(stale);
    fireEvent.click(check);
    await screen.findByText('Dieser Review ist STALE und muss erneut geprüft werden.');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Neue Review-Version vorbereiten' })).toBeEnabled(),
    );
    expect(api.createReviewDraft).not.toHaveBeenCalled();
    const successor = {
      ...draft,
      current_version_id: 'version-2',
      version: 2,
      supersedes_version_id: 'version-1',
    };
    api.createReviewDraft.mockResolvedValue(successor);
    api.review.mockResolvedValue(successor);
    fireEvent.click(screen.getByRole('button', { name: 'Neue Review-Version vorbereiten' }));
    await waitFor(() => expect(api.createReviewDraft).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByLabelText('Review-Begründung')).toBeEnabled());
    expect(api.revalidateReview).toHaveBeenCalledWith('trade-1');
    expect(api.createReviewDraft).toHaveBeenCalledWith('trade-1');
    expect(api.finalizeReview).not.toHaveBeenCalled();
    expect(materializationApi.materialize).not.toHaveBeenCalled();
  });

  it('keeps the successor action disabled at the parent refresh commit and accepts one later click', async () => {
    api.observation.mockResolvedValue({ ...observation, status: 'COMPLETED', is_complete: true });
    const final: ExitReviewResponse = { ...draft, status: 'FINALIZED' };
    const stale: ExitReviewResponse = { ...final, currentness: 'STALE' };
    const successor: ExitReviewResponse = {
      ...draft,
      current_version_id: 'version-2',
      version: 2,
      supersedes_version_id: 'version-1',
    };
    const parentRead = deferred<ExitReviewResponse>();
    api.review
      .mockResolvedValueOnce(final)
      .mockResolvedValueOnce(stale)
      .mockReturnValueOnce(parentRead.promise)
      .mockResolvedValue(successor);
    api.revalidateReview.mockResolvedValue(stale);
    api.createReviewDraft.mockResolvedValue(successor);

    const disabledAtParentCommit: boolean[] = [];
    function EmbeddedReview() {
      const [version, setVersion] = useState(0);
      useLayoutEffect(() => {
        if (version === 1) {
          // Observe the actual DOM before passive effects can disable it again.
          // This is the interaction window from the native lost-click trace.
          const button = screen.getByRole('button', {
            name: 'Neue Review-Version vorbereiten',
          });
          disabledAtParentCommit.push(button.hasAttribute('disabled'));
        }
      }, [version]);
      return (
        <PostTradeReviewPage
          externalRefreshVersion={version}
          onLearningStateChanged={() => setVersion((current) => current + 1)}
        />
      );
    }

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <EmbeddedReview />
      </MemoryRouter>,
    );
    const check = await screen.findByRole('button', { name: 'Review-Quellenstand prüfen' });
    await waitFor(() => expect(check).toBeEnabled());
    fireEvent.click(check);
    await waitFor(() => expect(api.review).toHaveBeenCalledTimes(3));
    expect(disabledAtParentCommit).toEqual([true]);
    const prepare = screen.getByRole('button', { name: 'Neue Review-Version vorbereiten' });
    expect(prepare).toBeDisabled();
    expect(screen.getByLabelText('Review-Begründung')).toBeDisabled();
    fireEvent.click(prepare);
    expect(api.createReviewDraft).not.toHaveBeenCalled();

    await act(async () => {
      parentRead.resolve(stale);
      await parentRead.promise;
    });
    await waitFor(() => expect(prepare).toBeEnabled());
    fireEvent.click(prepare);
    await waitFor(() => expect(screen.getByLabelText('Review-Begründung')).toBeEnabled());
    expect(screen.getByRole('heading', { name: 'Version 2' })).toBeVisible();
    expect(api.createReviewDraft).toHaveBeenCalledExactlyOnceWith('trade-1');
    expect(api.revalidateReview).toHaveBeenCalledExactlyOnceWith('trade-1');
    expect(api.finalizeReview).not.toHaveBeenCalled();
    expect(materializationApi.materialize).not.toHaveBeenCalled();
  });

  it('does not let a completed external read enable actions while a review command is pending', async () => {
    api.observation.mockResolvedValue({ ...observation, status: 'COMPLETED', is_complete: true });
    const final: ExitReviewResponse = { ...draft, status: 'FINALIZED' };
    const stale: ExitReviewResponse = { ...final, currentness: 'STALE' };
    api.review.mockResolvedValue(final);
    const command = deferred<ExitReviewResponse>();
    const externalRead = deferred<ExitReviewResponse>();
    api.revalidateReview.mockReturnValue(command.promise);
    const view = (version: number) => (
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage externalRefreshVersion={version} />
      </MemoryRouter>
    );
    const mounted = render(view(0));
    const check = await screen.findByRole('button', { name: 'Review-Quellenstand prüfen' });
    await waitFor(() => expect(check).toBeEnabled());
    fireEvent.click(check);
    expect(check).toBeDisabled();
    api.review.mockReturnValueOnce(externalRead.promise);
    mounted.rerender(view(1));
    await waitFor(() => expect(api.review).toHaveBeenCalledTimes(2));
    await act(async () => {
      externalRead.resolve(final);
      await externalRead.promise;
    });
    expect(check).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Neue Review-Version vorbereiten' })).toBeDisabled();
    expect(api.createReviewDraft).not.toHaveBeenCalled();

    api.review.mockResolvedValue(stale);
    await act(async () => {
      command.resolve(stale);
      await command.promise;
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Neue Review-Version vorbereiten' })).toBeEnabled(),
    );
    expect(
      screen.getByText('Dieser Review ist STALE und muss erneut geprüft werden.'),
    ).toBeVisible();
    expect(api.revalidateReview).toHaveBeenCalledExactlyOnceWith('trade-1');
  });

  it('ignores an aborted refresh completion and releases the latest failed refresh with its error visible', async () => {
    const complete: ObservationResponse = {
      ...observation,
      status: 'COMPLETED',
      is_complete: true,
    };
    const obsolete = deferred<ObservationResponse>();
    const current = deferred<ObservationResponse>();
    api.observation
      .mockResolvedValueOnce(complete)
      .mockReturnValueOnce(obsolete.promise)
      .mockReturnValueOnce(current.promise);
    api.review.mockResolvedValue({ ...draft, status: 'FINALIZED' });
    const view = (version: number) => (
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage externalRefreshVersion={version} />
      </MemoryRouter>
    );
    const mounted = render(view(0));
    const prepare = await screen.findByRole('button', { name: 'Neue Review-Version vorbereiten' });
    await waitFor(() => expect(prepare).toBeEnabled());
    mounted.rerender(view(1));
    await waitFor(() => expect(api.observation).toHaveBeenCalledTimes(2));
    const obsoleteSignal = api.observation.mock.calls[1][1]!;
    mounted.rerender(view(2));
    await waitFor(() => expect(api.observation).toHaveBeenCalledTimes(3));
    expect(obsoleteSignal.aborted).toBe(true);
    await act(async () => {
      obsolete.reject(new Error('Obsolete read error'));
      await obsolete.promise.catch(() => undefined);
    });
    expect(prepare).toBeDisabled();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => {
      current.reject(new Error('Current read unavailable'));
      await current.promise.catch(() => undefined);
    });
    await waitFor(() => expect(prepare).toBeEnabled());
    expect(screen.getByRole('alert')).toHaveTextContent('Die Daten konnten nicht geladen werden.');
    expect(screen.queryByText('Post-Trade-Daten werden geladen …')).not.toBeInTheDocument();
    expect(api.createReviewDraft).not.toHaveBeenCalled();
  });

  it('does not render a second materialization action when embedded', async () => {
    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage showMaterializationAction={false} />
      </MemoryRouter>,
    );
    expect(await screen.findByText('FT-012 Handoff')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Als LearningEvidence materialisieren' }),
    ).toBeNull();
    expect(materializationApi.materialize).not.toHaveBeenCalled();
  });

  it('reloads the same trade explicitly instead of relying on a URL change', async () => {
    renderPage();
    expect(await screen.findByText('13/20')).toBeInTheDocument();
    const button = screen.getByRole('button', { name: 'Laden' });
    await waitFor(() => expect(button).toBeEnabled());
    const before = api.observation.mock.calls.length;
    fireEvent.click(button);
    await waitFor(() => expect(api.observation).toHaveBeenCalledTimes(before + 1));
    expect(api.startObservation).not.toHaveBeenCalled();
    expect(api.revalidateReview).not.toHaveBeenCalled();
  });

  it('preserves unsaved draft text and assessments through an external owner refresh', async () => {
    api.observation.mockResolvedValue({
      ...observation,
      status: 'COMPLETED',
      is_complete: true,
      available_observation_count: 20,
      missing_observation_count: 0,
    });
    api.review.mockResolvedValue(draft);
    const view = render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage externalRefreshVersion={0} />
      </MemoryRouter>,
    );
    const rationale = await screen.findByLabelText('Review-Begründung');
    await waitFor(() => expect(rationale).toBeEnabled());
    fireEvent.change(rationale, { target: { value: 'Meine noch nicht gespeicherte Begründung.' } });
    fireEvent.change(screen.getByRole('combobox', { name: 'Timing' }), {
      target: { value: 'NOT_ASSESSABLE' },
    });
    let resolve!: (value: ExitReviewResponse) => void;
    api.review.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    view.rerender(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeReviewPage externalRefreshVersion={1} />
      </MemoryRouter>,
    );
    await waitFor(() => expect(api.review).toHaveBeenCalledTimes(2));
    await act(async () => {
      resolve(draft);
      await Promise.resolve();
    });
    await waitFor(() => expect(rationale).toBeEnabled());
    expect(rationale).toHaveValue('Meine noch nicht gespeicherte Begründung.');
    expect(screen.getByRole('combobox', { name: 'Timing' })).toHaveValue('NOT_ASSESSABLE');
    fireEvent.click(screen.getByRole('button', { name: 'Review finalisieren' }));
    await waitFor(() =>
      expect(api.updateReviewDraft).toHaveBeenCalledWith(
        'trade-1',
        expect.objectContaining({
          rationale: 'Meine noch nicht gespeicherte Begründung.',
          timing: 'NOT_ASSESSABLE',
        }),
      ),
    );
  });
});
