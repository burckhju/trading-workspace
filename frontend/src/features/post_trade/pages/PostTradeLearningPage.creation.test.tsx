import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, Link, RouterProvider, useParams } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { lessonDraftClient } from '../../learning/services/lessonDraftClient';
import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { LessonDraftCreateResponse } from '../../learning/types/lessonDraft';
import type { LessonEvidenceReference } from '../../learning/types/lessonReadback';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../../trade/services/client';
import { PostTradeLearningPage } from './PostTradeLearningPage';

vi.mock('./PostTradeReviewPage', () => ({
  PostTradeReviewPage: ({
    onLearningStateChanged,
    onNavigationStateChange,
  }: {
    onLearningStateChanged: () => void;
    onNavigationStateChange: (state: { dirty: boolean; pending: boolean }) => void;
  }) => (
    <>
      <button type="button" onClick={onLearningStateChanged}>
        Reviewstand erneut lesen
      </button>
      <button
        type="button"
        onClick={() => onNavigationStateChange({ dirty: true, pending: false })}
      >
        Review-Eingaben ändern
      </button>
    </>
  ),
}));
vi.mock('../../learning/components/TradeJournalPanel', () => ({
  TradeJournalPanel: () => null,
}));
vi.mock('../../learning/components/Ft011EvidenceHistory', () => ({
  Ft011EvidenceHistory: () => null,
}));
vi.mock('../../learning/services/lessonDraftClient', () => ({
  lessonDraftClient: { createFromEvidence: vi.fn() },
}));
vi.mock('../../learning/services/lessonReadbackClient', () => ({
  lessonReadbackClient: { listForEvidence: vi.fn() },
}));
vi.mock('../../learning/services/materializationClient', () => ({
  ft011MaterializationClient: { status: vi.fn(), materialize: vi.fn() },
}));
vi.mock('../../product/services/client', () => ({
  warrantApiClient: { get: vi.fn() },
}));
vi.mock('../../trade/services/client', () => ({
  tradeManagementApiClient: { trade: vi.fn() },
}));

const lessonId = '96f10d57-8d24-4c67-8e5c-479bdbb4d724';
const created: LessonDraftCreateResponse = {
  lesson_id: lessonId,
  current_version_id: 'lesson-version-a',
  current_state: 'CURRENT',
  version: 1,
  title: 'Exit discipline',
  main_category: 'Execution',
  content: 'Wait for the confirmed exit signal.',
  evidence: [],
};
const reference: LessonEvidenceReference = {
  lesson_id: lessonId,
  current_version_id: created.current_version_id,
  current_state: 'CURRENT',
  title: created.title,
};
const create = vi.mocked(lessonDraftClient.createFromEvidence);
const list = vi.mocked(lessonReadbackClient.listForEvidence);
const status = vi.mocked(ft011MaterializationClient.status);

function evidenceStatus(evidenceId = 'evidence-a') {
  return {
    ready: true,
    reason: 'READY',
    materialized: true,
    learning_evidence_id: evidenceId,
    exit_review_version_id: `review-${evidenceId}`,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function LessonDestination() {
  const { lessonId: openedLessonId } = useParams();
  return <h1>Geöffnete Lesson: {openedLessonId}</h1>;
}

function show() {
  const router = createMemoryRouter(
    [
      {
        path: '/post-trade',
        element: (
          <>
            <Link to="/post-trade?trade_id=trade-b">Anderen Trade öffnen</Link>
            <Link to="/post-trade?trade_id=trade-a&journal_version_id=journal-b">
              Andere Journalversion öffnen
            </Link>
            <PostTradeLearningPage />
          </>
        ),
      },
      { path: '/lessons/:lessonId', element: <LessonDestination /> },
    ],
    { initialEntries: ['/post-trade?trade_id=trade-a'] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

async function click(target: HTMLElement) {
  await act(async () => {
    fireEvent.click(target);
    await Promise.resolve();
  });
}

async function createLesson() {
  const title = await screen.findByLabelText('Lesson-Titel');
  await waitFor(() => expect(title).toBeEnabled());
  fireEvent.change(title, { target: { value: created.title } });
  fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), {
    target: { value: created.main_category },
  });
  fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), {
    target: { value: created.content },
  });
  await click(screen.getByRole('button', { name: 'Lesson anlegen' }));
}

function expectCreatedAction(journalId?: string) {
  const links = screen.getAllByRole('link', { name: 'Lesson öffnen' });
  expect(links).toHaveLength(1);
  expect(links[0]).toHaveAttribute(
    'href',
    `/lessons/${lessonId}?trade_id=trade-a${journalId ? `&journal_version_id=${journalId}` : ''}&trade_return_view=journal#lesson-history`,
  );
  expect(screen.getByText('Lesson angelegt: LS-96F10D57')).toHaveAttribute('role', 'status');
  expect(screen.getByText(lessonId)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Lesson anlegen' })).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Lesson-Titel')).not.toBeInTheDocument();
  expect(create).toHaveBeenCalledExactlyOnceWith('evidence-a', {
    title: created.title,
    main_category: created.main_category,
    content: created.content,
    tags: [],
  });
  return links[0];
}

describe('PostTradeLearningPage confirmed Lesson creation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    create.mockResolvedValue(created);
    list.mockResolvedValue([]);
    status.mockResolvedValue(evidenceStatus());
    vi.mocked(tradeManagementApiClient.trade).mockImplementation((id) =>
      Promise.resolve({
        id,
        product_id: 'product-a',
        origin: 'WORKSPACE_SELECTION',
        trade_plan_id: 'plan-a',
        trade_plan_version_id: 'plan-version-a',
        product_selection_id: 'selection-a',
        product_evaluation_id: 'evaluation-a',
        created_at: '2026-10-28T08:00:00Z',
      }),
    );
    vi.mocked(warrantApiClient.get).mockRejectedValue(new Error('optional display unavailable'));
  });

  it.each([
    ['the created reference', [reference]],
    ['an empty readback', []],
  ] as const)(
    'keeps the exact action through loading and %s, then opens without another POST',
    async (_, references) => {
      const readback = deferred<LessonEvidenceReference[]>();
      list.mockResolvedValueOnce([]).mockReturnValueOnce(readback.promise);
      const router = show();
      await createLesson();

      await screen.findByRole('link', { name: 'Lesson öffnen' });
      await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
      expect(screen.getByText('Lesson-Verweise werden geladen …')).toBeInTheDocument();
      expectCreatedAction();

      await act(async () => {
        readback.resolve([...references]);
        await readback.promise;
      });
      if (references.length) expect(screen.getByText('Bereits interpretiert')).toBeInTheDocument();
      await click(expectCreatedAction());
      expect(
        await screen.findByRole('heading', { name: `Geöffnete Lesson: ${lessonId}` }),
      ).toBeInTheDocument();
      expect(router.state.location.pathname).toBe(`/lessons/${lessonId}`);
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(create).toHaveBeenCalledTimes(1);
      expect(ft011MaterializationClient.materialize).not.toHaveBeenCalled();
    },
  );

  it('keeps the confirmed action after a failed reference read and a successful read-only retry', async () => {
    list
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('reference read failed'))
      .mockResolvedValueOnce([reference]);
    show();
    await createLesson();

    expect(
      await screen.findByText('Lesson-Verweise konnten nicht geladen werden.'),
    ).toBeInTheDocument();
    expectCreatedAction();
    await click(screen.getByRole('button', { name: 'Lesson-Verweise erneut laden' }));
    expect(await screen.findByText('Bereits interpretiert')).toBeInTheDocument();
    expectCreatedAction();
    expect(list).toHaveBeenCalledTimes(3);
    expect(list.mock.calls.every(([id]) => id === 'evidence-a')).toBe(true);
  });

  it('shows an existing Lesson without a new form or a fabricated creation confirmation', async () => {
    list.mockResolvedValue([reference]);
    show();
    expect(await screen.findByText('Bereits interpretiert')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Exit discipline · CURRENT' })).toHaveAttribute(
      'href',
      `/lessons/${lessonId}?trade_id=trade-a&trade_return_view=journal&lesson_version_id=lesson-version-a#lesson-history`,
    );
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Lesson-Titel')).not.toBeInTheDocument();
    expect(screen.queryByText(/Lesson angelegt:/)).not.toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  it.each(['resolved', 'empty', 'failed'] as const)(
    'keeps a confirmed Lesson after discarding another participant during a same-trade query change (%s readback)',
    async (readback) => {
      list.mockResolvedValueOnce([]);
      if (readback === 'failed') list.mockRejectedValue(new Error('reference read failed'));
      else list.mockResolvedValue(readback === 'resolved' ? [reference] : []);
      const router = show();
      await createLesson();
      await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
      if (readback === 'resolved') await screen.findByText('Bereits interpretiert');
      else if (readback === 'failed')
        await screen.findByText('Lesson-Verweise konnten nicht geladen werden.');
      expectCreatedAction();

      await click(screen.getByRole('button', { name: 'Review-Eingaben ändern' }));
      await click(screen.getByRole('link', { name: 'Andere Journalversion öffnen' }));
      expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
      expect(router.state.location.search).toBe('?trade_id=trade-a');
      await click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
      await waitFor(() =>
        expect(router.state.location.search).toBe('?trade_id=trade-a&journal_version_id=journal-b'),
      );

      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      await click(expectCreatedAction('journal-b'));
      expect(
        await screen.findByRole('heading', { name: `Geöffnete Lesson: ${lessonId}` }),
      ).toBeInTheDocument();
      expect(create).toHaveBeenCalledTimes(1);
      expect(ft011MaterializationClient.materialize).not.toHaveBeenCalled();
    },
  );

  it('drops a completed action when the current review changes to a different evidence source', async () => {
    list.mockResolvedValueOnce([]).mockResolvedValueOnce([reference]).mockResolvedValue([]);
    show();
    await createLesson();
    await screen.findByText('Bereits interpretiert');
    expectCreatedAction();

    status.mockResolvedValue(evidenceStatus('evidence-b'));
    await click(screen.getByRole('button', { name: 'Reviewstand erneut lesen' }));
    await waitFor(() => expect(list).toHaveBeenCalledWith('evidence-b', expect.any(AbortSignal)));
    const title = await screen.findByLabelText('Lesson-Titel');
    await waitFor(() => expect(title).toBeEnabled());
    expect(title).toHaveValue('');
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
    expect(screen.queryByText(lessonId)).not.toBeInTheDocument();
    expect(screen.queryByText(/Lesson angelegt:/)).not.toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('does not revive a previous trade success from a late reference response after navigation', async () => {
    const oldRead = deferred<LessonEvidenceReference[]>();
    list.mockResolvedValueOnce([]).mockReturnValueOnce(oldRead.promise).mockResolvedValue([]);
    status.mockImplementation((id) =>
      Promise.resolve(evidenceStatus(id === 'trade-a' ? 'evidence-a' : 'evidence-b')),
    );
    const router = show();
    await createLesson();
    await screen.findByRole('link', { name: 'Lesson öffnen' });
    expectCreatedAction();
    await click(screen.getByRole('link', { name: 'Anderen Trade öffnen' }));
    await waitFor(() => expect(list).toHaveBeenCalledWith('evidence-b', expect.any(AbortSignal)));
    expect(router.state.location.search).toBe('?trade_id=trade-b');

    await act(async () => {
      oldRead.resolve([reference]);
      await oldRead.promise;
    });
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Lesson angelegt:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('blocks trade navigation while creation is pending and opens the confirmed result after staying', async () => {
    const pendingCreate = deferred<LessonDraftCreateResponse>();
    create.mockReturnValue(pendingCreate.promise);
    const router = show();
    await createLesson();
    await click(screen.getByRole('link', { name: 'Anderen Trade öffnen' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(router.state.location.search).toBe('?trade_id=trade-a');
    expect(
      screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
    ).not.toBeInTheDocument();
    await click(screen.getByRole('button', { name: 'Hier bleiben' }));

    await act(async () => {
      pendingCreate.resolve(created);
      await pendingCreate.promise;
    });
    await click(expectCreatedAction());
    expect(
      await screen.findByRole('heading', { name: `Geöffnete Lesson: ${lessonId}` }),
    ).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});
