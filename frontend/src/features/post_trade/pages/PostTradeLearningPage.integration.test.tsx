import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { StrictMode } from 'react';
import { createMemoryRouter, Link, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { journalClient, type JournalHistory } from '../../learning/services/journalClient';
import { lessonDraftClient } from '../../learning/services/lessonDraftClient';
import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import { MarketApiError } from '../../market/services/http';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../../trade/services/client';
import { postTradeApiClient } from '../services/client';
import type {
  ExitReviewResponse,
  ObservationEvidenceResponse,
  ObservationResponse,
} from '../types/api';
import { PostTradeLearningPage } from './PostTradeLearningPage';

// Only I/O is mocked: Parent, Journal, both Lesson forms, Review and the router guard are real.
vi.mock('../../learning/services/journalClient', async (original) => ({
  ...(await original<typeof import('../../learning/services/journalClient')>()),
  journalClient: { history: vi.fn(), version: vi.fn(), command: vi.fn() },
}));
vi.mock('../../learning/services/lessonDraftClient', () => ({
  lessonDraftClient: { createFromEvidence: vi.fn() },
}));
vi.mock('../../learning/services/lessonReadbackClient', () => ({
  lessonReadbackClient: { listForEvidence: vi.fn() },
}));
vi.mock('../../learning/services/materializationClient', () => ({
  ft011MaterializationClient: { status: vi.fn(), materialize: vi.fn(), history: vi.fn() },
}));
vi.mock('../../product/services/client', () => ({ warrantApiClient: { get: vi.fn() } }));
vi.mock('../../trade/services/client', () => ({ tradeManagementApiClient: { trade: vi.fn() } }));
vi.mock('../services/client', () => ({
  postTradeApiClient: {
    observation: vi.fn(),
    evidence: vi.fn(),
    handoff: vi.fn(),
    reviewHistory: vi.fn(),
    review: vi.fn(),
    startObservation: vi.fn(),
    createReviewDraft: vi.fn(),
    updateReviewDraft: vi.fn(),
    finalizeReview: vi.fn(),
    revalidateReview: vi.fn(),
  },
}));

const tradeId = '10000000-0000-4000-8000-000000000001';
const journalId = '20000000-0000-4000-8000-000000000001';
const draftId = '30000000-0000-4000-8000-000000000002';
const finalId = '30000000-0000-4000-8000-000000000001';
const reviewId = '40000000-0000-4000-8000-000000000001';
const evidenceId = '50000000-0000-4000-8000-000000000001';
const journalEvidenceId = '50000000-0000-4000-8000-000000000002';
const initialUrl = `/post-trade?trade_id=${tradeId}&journal_version_id=${draftId}&tab=reflection`;

const observation: ObservationResponse = {
  id: 'observation',
  trade_id: tradeId,
  status: 'COMPLETED',
  underlying_listing_id: 'listing',
  target_observation_count: 20,
  available_observation_count: 20,
  missing_observation_count: 0,
  is_complete: true,
  started_at: '2026-10-01T00:00:00Z',
  completed_at: '2026-10-25T00:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
};
const evidence: ObservationEvidenceResponse = {
  observation_id: 'observation',
  trade_id: tradeId,
  product_context: null,
  planning_context: {
    trade_plan_id: null,
    trade_plan_version_id: null,
    original_stop: null,
    original_targets: [],
  },
  management_levels: [],
  actual_exit: { full_exit_at: '2026-09-30T00:00:00Z', realized_gross_pnl: '0.00', executions: [] },
  counterfactual: {
    available_observation_count: 20,
    target_observation_count: 20,
    horizon_complete: true,
    points: [],
    highest_high: null,
    lowest_low: null,
    final_close: null,
    target_crossings: [],
    stop_crossing: null,
  },
};
const review: ExitReviewResponse = {
  exit_review_id: 'review',
  current_version_id: reviewId,
  version: 1,
  status: 'DRAFT',
  currentness: 'CURRENT',
  timing: 'GOOD',
  process_adherence: 'GOOD',
  risk_decision: 'GOOD',
  overall_exit_decision: 'GOOD',
  rationale: 'Saved review rationale',
  created_at: '2026-10-25T00:00:00Z',
  created_by: 'actor',
  finalized_at: null,
  finalized_by: null,
  supersedes_version_id: null,
  stale_at: null,
  stale_reason: null,
};
const ownerStatus = {
  ready: true,
  reason: 'READY',
  materialized: true,
  learning_evidence_id: evidenceId,
  exit_review_version_id: reviewId,
};
function history(): JournalHistory {
  const version = {
    id: draftId,
    trade_journal_id: journalId,
    version: 2,
    edit_revision: 1,
    status: 'DRAFT' as const,
    source_exit_review_version_id: reviewId,
    supersedes_version_id: finalId,
    created_at: '2026-10-25',
    created_by: 'actor',
    updated_at: '2026-10-25',
    updated_by: 'actor',
    finalized_at: null,
    finalized_by: null,
    what_went_well: 'Saved journal text',
    would_do_differently: 'Saved alternative',
    additional_notes: 'Saved notes',
  };
  return {
    trade_id: tradeId,
    journal_id: journalId,
    handoff: { ready: true, reason: 'READY', exit_review_version_id: reviewId },
    versions: [
      {
        version,
        is_latest: true,
        source_currentness: 'CURRENT',
        source_checked_at: '2026-10-26',
        learning_evidence_id: null,
      },
      {
        version: {
          ...version,
          id: finalId,
          version: 1,
          status: 'FINALIZED',
          what_went_well: 'Historical journal text',
          supersedes_version_id: null,
          finalized_at: '2026-10-24',
          finalized_by: 'actor',
        },
        is_latest: false,
        source_currentness: 'STALE',
        source_checked_at: '2026-10-26',
        learning_evidence_id: journalEvidenceId,
      },
    ],
  };
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
function mountPage(url = initialUrl, strict = false) {
  const router = createMemoryRouter(
    [
      {
        path: '/post-trade',
        element: (
          <>
            <nav>
              <Link to="/away">Andere Seite</Link>
              <Link
                to={`/post-trade?trade_id=${tradeId}&journal_version_id=${finalId}&tab=reflection`}
              >
                Historische Quelle
              </Link>
              <Link to="/post-trade?trade_id=10000000-0000-4000-8000-000000000099">
                Anderer Trade
              </Link>
            </nav>
            <PostTradeLearningPage />
          </>
        ),
      },
      { path: '/away', element: <h1>Andere Seite geöffnet</h1> },
    ],
    { initialEntries: ['/away', url], initialIndex: 1 },
  );
  const element = <RouterProvider router={router} />;
  const view = render(strict ? <StrictMode>{element}</StrictMode> : element);
  return { router, ...view };
}
async function editJournal(text = 'Local journal interpretation') {
  const journal = within(await screen.findByRole('region', { name: 'Trade-Journal' }));
  const edit = await journal.findByRole('button', { name: 'Journal bearbeiten' });
  await waitFor(() => expect(edit).toBeEnabled());
  fireEvent.click(edit);
  fireEvent.change(journal.getByLabelText('Was lief gut?'), { target: { value: text } });
  return journal;
}
function fillLesson(
  scope: Pick<typeof screen, 'getByLabelText'> = screen,
  title = 'Local Lesson title',
) {
  fireEvent.change(scope.getByLabelText('Lesson-Titel'), { target: { value: title } });
  fireEvent.change(scope.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
  fireEvent.change(scope.getByLabelText('Lesson-Inhalt'), {
    target: { value: 'Independent Lesson interpretation' },
  });
}

describe('PostTradeLearningPage with real forms and a data router', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(journalClient.history).mockImplementation(() => Promise.resolve(history()));
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue(ownerStatus);
    vi.mocked(ft011MaterializationClient.history).mockResolvedValue([]);
    vi.mocked(lessonReadbackClient.listForEvidence).mockResolvedValue([]);
    vi.mocked(tradeManagementApiClient.trade).mockResolvedValue({
      id: tradeId,
      product_id: 'product',
      origin: 'EXTERNAL',
      trade_plan_id: null,
      trade_plan_version_id: null,
      product_selection_id: null,
      product_evaluation_id: null,
      created_at: '2026-10-01',
    });
    vi.mocked(warrantApiClient.get).mockRejectedValue(new Error('optional product context'));
    vi.mocked(postTradeApiClient.observation).mockResolvedValue(observation);
    vi.mocked(postTradeApiClient.evidence).mockResolvedValue(evidence);
    vi.mocked(postTradeApiClient.handoff).mockResolvedValue({
      ready: false,
      reason: 'EXIT_REVIEW_NOT_FINALIZED',
      post_trade_observation_id: 'observation',
      exit_review_id: 'review',
      exit_review_version_id: reviewId,
    });
    vi.mocked(postTradeApiClient.reviewHistory).mockResolvedValue([]);
    vi.mocked(postTradeApiClient.review).mockResolvedValue(review);
    vi.mocked(postTradeApiClient.updateReviewDraft).mockResolvedValue(review);
    vi.mocked(lessonDraftClient.createFromEvidence).mockResolvedValue({
      lesson_id: 'lesson',
      current_version_id: 'lv',
      version: 1,
      current_state: 'CURRENT',
      title: 'Created',
      main_category: 'Execution',
      content: 'Independent meaning',
      evidence: [],
    });
  });

  it('uses one guard for journal, Lesson and Review across query, route, trade, back and unload', async () => {
    const { router } = mountPage();
    const journal = await editJournal();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    const rationale = await screen.findByLabelText('Review-Begründung');
    await waitFor(() => expect(rationale).toBeEnabled());
    fireEvent.change(rationale, { target: { value: 'Local review interpretation' } });
    for (const link of ['Historische Quelle', 'Anderer Trade', 'Andere Seite']) {
      fireEvent.click(screen.getByRole('link', { name: link }));
      expect(await screen.findAllByRole('alertdialog')).toHaveLength(1);
      expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
      fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
      expect(router.state.location.search).toContain(draftId);
      expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
      expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
      expect(rationale).toHaveValue('Local review interpretation');
    }
    await act(async () => {
      await router.navigate(-1);
    });
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    await act(async () => {
      fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' });
      await Promise.resolve();
    });
    const unload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    await act(async () => {
      fireEvent.click(
        await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
      );
    });
    expect(await screen.findByRole('heading', { name: 'Andere Seite geöffnet' })).toBeVisible();
    expect(journalClient.command).not.toHaveBeenCalled();
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
    expect(postTradeApiClient.updateReviewDraft).not.toHaveBeenCalled();
  });

  it('preserves journal and Lesson inputs through a successful review write and parent refresh', async () => {
    mountPage();
    const journal = await editJournal();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    const rationale = await screen.findByLabelText('Review-Begründung');
    await waitFor(() => expect(rationale).toBeEnabled());
    fireEvent.change(rationale, { target: { value: 'Saved new review rationale' } });
    const savedReview = { ...review, rationale: 'Saved new review rationale' };
    const writing = deferred<ExitReviewResponse>();
    const statusRead = deferred<typeof ownerStatus>();
    const journalRead = deferred<JournalHistory>();
    vi.mocked(postTradeApiClient.updateReviewDraft).mockReturnValue(writing.promise);
    vi.mocked(postTradeApiClient.review).mockResolvedValue(savedReview);
    vi.mocked(ft011MaterializationClient.status).mockReturnValue(statusRead.promise);
    vi.mocked(journalClient.history).mockReturnValue(journalRead.promise);
    fireEvent.click(screen.getByRole('button', { name: 'Entwurf speichern' }));
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    await act(async () => {
      writing.resolve(savedReview);
      await writing.promise;
    });
    await waitFor(() => expect(journalClient.history).toHaveBeenCalledTimes(2));
    expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    await act(async () => {
      statusRead.resolve(ownerStatus);
      journalRead.resolve(history());
      await Promise.all([statusRead.promise, journalRead.promise]);
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeEnabled(),
    );
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(postTradeApiClient.updateReviewDraft).toHaveBeenCalledTimes(1);
    expect(journalClient.command).not.toHaveBeenCalled();
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
  });

  it('keeps the real embedded journal Lesson through a failed same-source refresh in StrictMode', async () => {
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue({
      ...ownerStatus,
      materialized: false,
      learning_evidence_id: null,
    });
    mountPage(`/post-trade?trade_id=${tradeId}&journal_version_id=${finalId}`, true);
    const journal = within(await screen.findByRole('region', { name: 'Trade-Journal' }));
    await journal.findByLabelText('Lesson-Titel');
    fillLesson(journal, 'Journal-specific Lesson');
    const read = deferred<JournalHistory>();
    vi.mocked(journalClient.history).mockReturnValue(read.promise);
    const reload = screen.getByRole('button', { name: 'Laden' });
    await waitFor(() => expect(reload).toBeEnabled());
    fireEvent.click(reload);
    await waitFor(() =>
      expect(journal.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled(),
    );
    expect(journal.getByLabelText('Lesson-Titel')).toHaveValue('Journal-specific Lesson');
    await act(async () => {
      read.reject(new Error('temporarily unavailable'));
      await read.promise.catch(() => undefined);
    });
    expect(journal.getByLabelText('Lesson-Titel')).toHaveValue('Journal-specific Lesson');
    expect(journal.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
    expect(journalClient.command).not.toHaveBeenCalled();
  });

  it('does not rebind a direct FT011 Lesson when a refresh reveals different Evidence', async () => {
    mountPage();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue({
      ...ownerStatus,
      learning_evidence_id: 'new-evidence',
      exit_review_version_id: 'new-review',
    });
    const reload = screen.getByRole('button', { name: 'Laden' });
    await waitFor(() => expect(reload).toBeEnabled());
    fireEvent.click(reload);
    expect(await screen.findByText(/Die Evidence hat sich geändert/)).toHaveTextContent(evidenceId);
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
      ).toBeEnabled(),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
    );
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    fillLesson(screen, 'New context interpretation');
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    await waitFor(() =>
      expect(lessonDraftClient.createFromEvidence).toHaveBeenCalledExactlyOnceWith(
        'new-evidence',
        expect.objectContaining({ title: 'New context interpretation' }),
      ),
    );
    expect(journalClient.command).not.toHaveBeenCalled();
  });

  it('does not release a pending direct Lesson POST on a route or trade change', async () => {
    mountPage();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    const writing = deferred<Awaited<ReturnType<typeof lessonDraftClient.createFromEvidence>>>();
    vi.mocked(lessonDraftClient.createFromEvidence).mockReturnValue(writing.promise);
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    fireEvent.click(screen.getByRole('link', { name: 'Anderer Trade' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    await act(async () => {
      writing.reject(new Error('unknown POST outcome'));
      await writing.promise.catch(() => undefined);
    });
    expect(await screen.findByText(/nicht idempotent wiederholt/)).toBeVisible();
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    expect(lessonDraftClient.createFromEvidence).toHaveBeenCalledTimes(1);
  });

  it('coordinates the direct materialization write without clearing a separate journal draft', async () => {
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue({
      ...ownerStatus,
      materialized: false,
      learning_evidence_id: null,
    });
    vi.mocked(postTradeApiClient.review).mockResolvedValue({ ...review, status: 'FINALIZED' });
    mountPage();
    const journal = await editJournal();
    const writing = deferred<Awaited<ReturnType<typeof ft011MaterializationClient.materialize>>>();
    vi.mocked(ft011MaterializationClient.materialize).mockReturnValue(writing.promise);
    const handoff = await screen.findByRole('button', { name: 'An Lessons Learned übergeben' });
    await waitFor(() => expect(handoff).toBeEnabled());
    fireEvent.click(handoff);
    fireEvent.click(handoff);
    expect(ft011MaterializationClient.materialize).toHaveBeenCalledExactlyOnceWith(
      tradeId,
      `ft011-to-ft012:v2:${tradeId}:${reviewId}`,
      reviewId,
    );
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue(ownerStatus);
    await act(async () => {
      writing.resolve({
        learning_evidence_id: evidenceId,
        exit_review_version_id: reviewId,
        created: true,
        replayed: false,
      });
      await writing.promise;
    });
    await screen.findByLabelText('Lesson-Titel');
    expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
    fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    expect(journalClient.command).not.toHaveBeenCalled();
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
  });

  it('retains a materialization source mismatch after the fresh owner version has finished loading', async () => {
    const readyStatus = { ...ownerStatus, materialized: false, learning_evidence_id: null };
    const nextReviewId = '40000000-0000-4000-8000-000000000002';
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue(readyStatus);
    vi.mocked(postTradeApiClient.review).mockResolvedValue({ ...review, status: 'FINALIZED' });
    mountPage();
    await screen.findByLabelText('Review-Begründung');
    const handoff = await screen.findByRole('button', { name: 'An Lessons Learned übergeben' });
    await waitFor(() => expect(handoff).toBeEnabled());

    const freshRead = deferred<Awaited<ReturnType<typeof ft011MaterializationClient.status>>>();
    vi.mocked(ft011MaterializationClient.status).mockReturnValue(freshRead.promise);
    vi.mocked(ft011MaterializationClient.materialize).mockRejectedValue(
      new MarketApiError(409, {
        code: 'SOURCE_VERSION_MISMATCH',
        message: 'Changed source',
        details: [],
        timestamp: '2026-10-26T12:00:00Z',
      }),
    );
    fireEvent.click(handoff);
    expect(await screen.findByText(/Die Review-Version hat sich geändert/)).toBeVisible();
    expect(handoff).toBeDisabled();

    vi.mocked(postTradeApiClient.review).mockResolvedValue({
      ...review,
      current_version_id: nextReviewId,
      version: 2,
      status: 'FINALIZED',
    });
    await act(async () => {
      freshRead.resolve({ ...readyStatus, exit_review_version_id: nextReviewId });
      await freshRead.promise;
    });
    await waitFor(() => expect(handoff).toBeEnabled());
    expect(screen.getByText(`ExitReviewVersion: ${nextReviewId}`, { exact: true })).toBeVisible();
    expect(screen.getByText(/Die Review-Version hat sich geändert/)).toBeVisible();
    expect(ft011MaterializationClient.materialize).toHaveBeenCalledExactlyOnceWith(
      tradeId,
      `ft011-to-ft012:v2:${tradeId}:${reviewId}`,
      reviewId,
    );
    expect(journalClient.command).not.toHaveBeenCalled();
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
  });

  it('retains a direct Lesson across a failed owner read and suppresses a duplicate after explicit new-source reconciliation', async () => {
    mountPage();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    vi.mocked(ft011MaterializationClient.status).mockRejectedValue(new Error('status unavailable'));
    const reload = screen.getByRole('button', { name: 'Laden' });
    await waitFor(() => expect(reload).toBeEnabled());
    fireEvent.click(reload);
    expect(
      await screen.findByText('Der Learning-Übergabestatus konnte nicht geladen werden.'),
    ).toBeVisible();
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue({
      ...ownerStatus,
      learning_evidence_id: 'new-evidence',
    });
    vi.mocked(lessonReadbackClient.listForEvidence).mockImplementation((id) =>
      Promise.resolve(
        id === 'new-evidence'
          ? [
              {
                lesson_id: 'existing-lesson',
                current_version_id: 'lv',
                current_state: 'CURRENT',
                title: 'Existing new-source Lesson',
              },
            ]
          : [],
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Übergabestatus erneut laden' }));
    expect(await screen.findByText(/Die Evidence hat sich geändert/)).toHaveTextContent(evidenceId);
    expect(await screen.findByRole('link', { name: /Existing new-source Lesson/ })).toBeVisible();
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
      ).toBeEnabled(),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
    );
    await waitFor(() => expect(screen.queryByLabelText('Lesson-Titel')).toBeNull());
    expect(screen.getByRole('link', { name: /Existing new-source Lesson/ })).toHaveAttribute(
      'href',
      `/lessons/existing-lesson?trade_id=${tradeId}&journal_version_id=${draftId}&trade_return_view=journal&lesson_version_id=lv#lesson-history`,
    );
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
  });

  it.each([
    `journal_version_id=${finalId}`,
    `trade_id=&journal_version_id=${finalId}`,
    `trade_id=%20&journal_version_id=${finalId}`,
    `trade_id=${tradeId}&trade_id=${tradeId}&journal_version_id=${finalId}`,
    `trade_id=${tradeId}&trade_id=foreign-trade&journal_version_id=${finalId}`,
  ])(
    'rejects an explicit source with no unambiguous trade without mounting write forms: %s',
    async (query) => {
      mountPage(`/post-trade?${query}`);
      expect(await screen.findByRole('alert')).toHaveTextContent('genau eine nichtleere Trade-ID');
      expect(screen.queryByRole('region', { name: 'Trade-Journal' })).toBeNull();
      expect(screen.queryByLabelText('Review-Begründung')).toBeNull();
      expect(screen.queryByLabelText('Lesson-Titel')).toBeNull();
      expect(journalClient.history).not.toHaveBeenCalled();
      expect(postTradeApiClient.observation).not.toHaveBeenCalled();
      expect(journalClient.command).not.toHaveBeenCalled();
      expect(postTradeApiClient.createReviewDraft).not.toHaveBeenCalled();
      expect(postTradeApiClient.updateReviewDraft).not.toHaveBeenCalled();
      expect(postTradeApiClient.finalizeReview).not.toHaveBeenCalled();
      expect(ft011MaterializationClient.materialize).not.toHaveBeenCalled();
      expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
    },
  );

  it.each([false, true])(
    'blocks local journal discard while another form writes, with an already open dialog: %s',
    async (openDialog) => {
      mountPage();
      const journal = await editJournal();
      const rationale = await screen.findByLabelText('Review-Begründung');
      await waitFor(() => expect(rationale).toBeEnabled());
      fireEvent.change(rationale, { target: { value: 'Review save in progress' } });
      const writing = deferred<ExitReviewResponse>();
      const saved = { ...review, rationale: 'Review save in progress' };
      vi.mocked(postTradeApiClient.updateReviewDraft).mockReturnValue(writing.promise);
      vi.mocked(postTradeApiClient.review).mockResolvedValue(saved);
      if (openDialog)
        fireEvent.click(journal.getByRole('button', { name: 'Bearbeitung abbrechen' }));
      const discard = journal.getByRole('button', {
        name: openDialog ? 'Verwerfen und Lesemodus öffnen' : 'Bearbeitung abbrechen',
      });
      const loadSaved = journal.getByRole('button', {
        name: 'Gespeicherten Journalstand laden (lokalen Text verwerfen)',
      });
      act(() => {
        fireEvent.click(screen.getByRole('button', { name: 'Entwurf speichern' }));
        // The old enabled closure must consult the shared synchronous pending getter.
        fireEvent.click(discard);
        fireEvent.click(loadSaved);
      });
      expect(discard).toBeDisabled();
      expect(loadSaved).toBeDisabled();
      if (openDialog)
        expect(journal.getByRole('dialog')).toHaveTextContent('Bearbeitung verwerfen');
      else {
        expect(journal.queryByRole('dialog')).toBeNull();
        expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
      }
      await act(async () => {
        writing.resolve(saved);
        await writing.promise;
      });
      await waitFor(() => expect(loadSaved).toBeEnabled());
      if (openDialog) fireEvent.click(journal.getByRole('button', { name: 'Abbrechen' }));
      expect(journal.getByLabelText('Was lief gut?')).toHaveValue('Local journal interpretation');
      fireEvent.click(screen.getByRole('link', { name: 'Andere Seite' }));
      expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
      fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
      expect(journalClient.command).not.toHaveBeenCalled();
      expect(postTradeApiClient.updateReviewDraft).toHaveBeenCalledTimes(1);
    },
  );

  it('blocks a direct Lesson source reset synchronously while the Review write is pending', async () => {
    mountPage();
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    vi.mocked(ft011MaterializationClient.status).mockResolvedValue({
      ...ownerStatus,
      learning_evidence_id: 'new-evidence',
    });
    const reload = screen.getByRole('button', { name: 'Laden' });
    await waitFor(() => expect(reload).toBeEnabled());
    fireEvent.click(reload);
    const reset = await screen.findByRole('button', {
      name: 'Eingaben verwerfen und neue Evidence öffnen',
    });
    await waitFor(() => expect(reset).toBeEnabled());
    const writing = deferred<ExitReviewResponse>();
    const saved = { ...review, rationale: 'Review save during source decision' };
    vi.mocked(postTradeApiClient.updateReviewDraft).mockReturnValue(writing.promise);
    vi.mocked(postTradeApiClient.review).mockResolvedValue(saved);
    fireEvent.change(screen.getByLabelText('Review-Begründung'), {
      target: { value: saved.rationale },
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Entwurf speichern' }));
      fireEvent.click(reset);
    });
    expect(reset).toBeDisabled();
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    await act(async () => {
      writing.resolve(saved);
      await writing.promise;
    });
    await waitFor(() => expect(reset).toBeEnabled());
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Local Lesson title');
    fireEvent.click(reset);
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
    expect(journalClient.command).not.toHaveBeenCalled();
  });

  it('blocks a Review source reconciliation synchronously while a separate Lesson POST is pending', async () => {
    mountPage();
    const rationale = await screen.findByLabelText('Review-Begründung');
    await waitFor(() => expect(rationale).toBeEnabled());
    fireEvent.change(rationale, { target: { value: 'Local Review remains' } });
    await screen.findByLabelText('Lesson-Titel');
    fillLesson();
    vi.mocked(postTradeApiClient.review).mockResolvedValue({
      ...review,
      current_version_id: 'new-review',
      version: 2,
      rationale: 'New saved Review',
    });
    fireEvent.click(screen.getByRole('button', { name: 'Laden' }));
    const reset = await screen.findByRole('button', {
      name: 'Revieweingaben verwerfen und gespeicherten Stand laden',
    });
    await waitFor(() => expect(reset).toBeEnabled());
    const create = screen.getByRole('button', { name: 'Lesson anlegen' });
    await waitFor(() => expect(create).toBeEnabled());
    const writing = deferred<Awaited<ReturnType<typeof lessonDraftClient.createFromEvidence>>>();
    vi.mocked(lessonDraftClient.createFromEvidence).mockReturnValue(writing.promise);
    act(() => {
      fireEvent.click(create);
      fireEvent.click(reset);
    });
    expect(reset).toBeDisabled();
    expect(rationale).toHaveValue('Local Review remains');
    await act(async () => {
      writing.resolve({
        lesson_id: 'created-lesson',
        current_version_id: 'created-version',
        version: 1,
        current_state: 'CURRENT',
        title: 'Local Lesson title',
        main_category: 'Execution',
        content: 'Independent Lesson interpretation',
        evidence: [],
      });
      await writing.promise;
    });
    await waitFor(() => expect(reset).toBeEnabled());
    expect(rationale).toHaveValue('Local Review remains');
    fireEvent.click(reset);
    expect(rationale).toHaveValue('New saved Review');
    expect(postTradeApiClient.updateReviewDraft).not.toHaveBeenCalled();
    expect(lessonDraftClient.createFromEvidence).toHaveBeenCalledTimes(1);
  });
});
