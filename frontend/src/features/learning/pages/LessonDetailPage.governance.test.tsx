import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { StrictMode } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LessonDetailPage } from './LessonDetailPage';
import type { ReviewContext, ReviewReceipt } from '../services/lessonReviewClient';
import type { LessonHypothesis } from '../../model/types/lessonHypothesis';

const mocks = vi.hoisted(() => ({
  getLesson: vi.fn(),
  context: vi.fn(),
  source: vi.fn(),
  evidence: vi.fn(),
  execute: vi.fn(),
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
}));
vi.mock('../services/lessonReadbackClient', () => ({ lessonReadbackClient: mocks }));
vi.mock('../services/lessonReviewClient', async (original) => ({
  ...(await original<typeof import('../services/lessonReviewClient')>()),
  lessonReviewClient: mocks,
}));
vi.mock('../../model/services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks }));
vi.mock('../../model/components/HypothesisProposalPanel', () => ({
  HypothesisProposalPanel: () => <p>Existing proposal workflow</p>,
}));
vi.mock('../components/JournalEvidenceOrigin', () => ({
  JournalEvidenceOrigin: ({ evidenceId }: { evidenceId: string }) => (
    <p>Exact source origin: {evidenceId}</p>
  ),
}));

const at = '2026-10-26T12:00:00Z';
const confirmLabel = 'Prüfentscheidung verbindlich bestätigen';
const discardLabel = 'Eingaben verwerfen und wechseln';
const hypothesisLabel = 'Hypothese für FT-013 anlegen';
const sourceReviewLabel = 'Quellenbezogene Prüfung beginnen';
const routers: ReturnType<typeof createMemoryRouter>[] = [];

afterEach(() => {
  for (const router of routers.splice(0)) router.dispose();
});

function versionId(lessonId: string, version: number) {
  return lessonId === 'lesson-1' ? `l${version}` : `${lessonId}-l${version}`;
}

function reviewContext(
  state: ReviewContext['lesson']['current_state'] = 'CURRENT',
  lessonId = 'lesson-1',
  currentVersion = 2,
): ReviewContext {
  return {
    lesson: {
      id: lessonId,
      title: lessonId === 'lesson-1' ? 'Synthetic Lesson' : `Synthetic ${lessonId}`,
      current_version_id: versionId(lessonId, currentVersion),
      current_state: state,
    },
    history: Array.from({ length: currentVersion }, (_, index) => {
      const number = index + 1;
      const id = versionId(lessonId, number);
      return {
        version: {
          id,
          lesson_id: lessonId,
          version: number,
          main_category: 'Process',
          content: `L${number} interpretation`,
          created_at: at,
          created_by: 'actor',
          supersedes_version_id: number === 1 ? null : versionId(lessonId, number - 1),
        },
        evidence_links: (['SUPPORTS', 'CONTRADICTS', 'CONTEXTUAL'] as const).map(
          (relation, linkIndex) => ({
            id: `${id}-link${linkIndex + 1}`,
            lesson_version_id: id,
            learning_evidence_id: `${id}-e${linkIndex + 1}`,
            relation,
          }),
        ),
      };
    }),
    signals: [],
    transitions: [],
    read_at: at,
  };
}

function hypothesis(source: string): LessonHypothesis {
  return {
    id: `hypothesis-${source}`,
    source_lesson_version_id: source,
    title: 'Synthetic H1',
    statement: 'Synthetic interpretation only',
    status: 'OPEN',
    created_at: at,
    created_by: 'actor',
  };
}

const receipt: ReviewReceipt = {
  lesson_id: 'lesson-1',
  result_id: 'transition-1',
  result_type: 'LESSON_STATE_TRANSITION',
  replayed: false,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function renderLesson({
  entries = ['/lessons/lesson-1'],
  initialIndex = entries.length - 1,
  strict = false,
}: { entries?: string[]; initialIndex?: number; strict?: boolean } = {}) {
  const router = createMemoryRouter(
    [
      { path: '/lessons/:lessonId', element: <LessonDetailPage /> },
      { path: '/post-trade', element: <h1>Post-Trade target</h1> },
    ],
    { initialEntries: entries, initialIndex },
  );
  const provider = <RouterProvider router={router} />;
  routers.push(router);
  return { ...render(strict ? <StrictMode>{provider}</StrictMode> : provider), router };
}

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));
const reason = () => screen.getByLabelText(/Begründung der Prüfentscheidung/);
const versionSelect = () => screen.getByRole('combobox', { name: 'Lesson-Version ansehen' });

async function fillHypothesis() {
  const title = await screen.findByLabelText('Titel');
  const statement = screen.getByLabelText('Hypothese');
  fireEvent.change(title, { target: { value: 'Synthetic H1' } });
  fireEvent.change(statement, { target: { value: 'Synthetic interpretation only' } });
  return { title, statement };
}

async function prepareReview(operation = sourceReviewLabel) {
  fireEvent.click(await screen.findByRole('button', { name: operation }));
  fireEvent.change(reason(), { target: { value: 'Explicit synthetic review.' } });
  if (operation === 'Neue Lesson-Version vorbereiten')
    await waitFor(() =>
      expect(screen.getByLabelText('Vorhandene Evidence ergänzen')).toBeEnabled(),
    );
  return screen.getByRole('form', { name: 'Lesson-Prüfentscheidung' });
}

async function navigate(router: ReturnType<typeof createMemoryRouter>, target: string | number) {
  await act(async () => {
    if (typeof target === 'number') await router.navigate(target);
    else await router.navigate(target);
  });
}

function openSource(label: string) {
  const details = screen.getByText(label).closest('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
}

describe('one exact Lesson context and guarded Governance handoff', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.context.mockImplementation((lessonId: string) =>
      Promise.resolve(reviewContext('CURRENT', lessonId)),
    );
    mocks.source.mockImplementation((id: string) =>
      Promise.resolve({
        evidence_id: id,
        source_type: 'TRADE_JOURNAL_VERSION',
        source_version_id: `source-${id}`,
        source_currentness: 'CURRENT',
        review_currentness: 'CURRENT',
        superseded_by_version_id: null,
        checked_at: at,
      }),
    );
    mocks.evidence.mockResolvedValue([]);
    mocks.execute.mockResolvedValue(receipt);
    mocks.listForLessonVersion.mockResolvedValue([]);
    mocks.createFromLessonVersion.mockImplementation(
      (id: string, input: { title: string; statement: string }) =>
        Promise.resolve({ ...hypothesis(id), ...input }),
    );
  });

  it('loads current content, category and its complete sources exactly once from review-context', async () => {
    const { router } = renderLesson();
    const article = await screen.findByRole('article', { name: 'Lesson-Snapshot Version 2' });
    expect(screen.getAllByText('L2 interpretation')).toHaveLength(1);
    expect(screen.getAllByText('Kategorie: Process')).toHaveLength(1);
    expect(within(article).getAllByRole('list')).toHaveLength(1);
    expect(within(article).getAllByRole('listitem')).toHaveLength(3);
    expect(screen.queryByText('L1 interpretation')).not.toBeInTheDocument();
    expect(screen.getByText('Heutiger Lesson-Status: CURRENT')).toBeInTheDocument();
    openSource('SUPPORTS · Evidence l2-e1');
    expect(await screen.findAllByText('Exact source origin: l2-e1')).toHaveLength(1);
    expect(screen.queryByText('SUPPORTS · Evidence l1-e1')).not.toBeInTheDocument();
    await screen.findByRole('button', { name: hypothesisLabel });
    expect(mocks.context).toHaveBeenCalledExactlyOnceWith('lesson-1');
    expect(mocks.getLesson).not.toHaveBeenCalled();
    expect(mocks.listForLessonVersion).toHaveBeenCalledWith('l2', expect.any(AbortSignal));
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
    expect(router.state.location.search).toBe('');
  });

  it('shows only historical L1 and its sources with today’s status, then creates an explicit L1 hypothesis', async () => {
    mocks.context.mockResolvedValue(reviewContext('REVIEW_RECOMMENDED'));
    renderLesson({ entries: ['/lessons/lesson-1?lesson_version_id=l1#lesson-history'] });
    const article = await screen.findByRole('article', { name: 'Lesson-Snapshot Version 1' });
    expect(within(article).getByText('L1 interpretation')).toBeInTheDocument();
    expect(screen.queryByText('L2 interpretation')).not.toBeInTheDocument();
    expect(screen.getByText('Heutiger Lesson-Status: REVIEW_RECOMMENDED')).toBeInTheDocument();
    expect(screen.getByText('Gewählte Inhaltsversion: Version 1 · historisch')).toBeInTheDocument();
    openSource('SUPPORTS · Evidence l1-e1');
    expect(await screen.findByText('Exact source origin: l1-e1')).toBeInTheDocument();
    expect(screen.queryByText('SUPPORTS · Evidence l2-e1')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Neue Lesson-Version vorbereiten' })).toBeNull();
    await fillHypothesis();
    click(hypothesisLabel);
    await screen.findByText('Bereits an FT-013 übergeben');
    expect(mocks.listForLessonVersion).toHaveBeenCalledWith('l1', expect.any(AbortSignal));
    expect(mocks.listForLessonVersion).not.toHaveBeenCalledWith('l2', expect.any(AbortSignal));
    expect(mocks.createFromLessonVersion).toHaveBeenCalledExactlyOnceWith('l1', {
      title: 'Synthetic H1',
      statement: 'Synthetic interpretation only',
    });
    expect(mocks.execute).not.toHaveBeenCalled();
  });

  it('keeps explicit selection, copied URL, reload and browser POP on the same source without writing', async () => {
    const view = renderLesson({
      entries: ['/lessons/lesson-1?lesson_version_id=l1#lesson-history'],
    });
    await screen.findByText('L1 interpretation');
    expect(screen.getByRole('link', { name: 'Genau diese Lesson-Version öffnen' })).toHaveAttribute(
      'href',
      '/lessons/lesson-1?lesson_version_id=l1#lesson-history',
    );
    fireEvent.change(versionSelect(), { target: { value: 'l2' } });
    await screen.findByText('L2 interpretation');
    expect(view.router.state.location.search).toBe('?lesson_version_id=l2');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await navigate(view.router, -1);
    await screen.findByText('L1 interpretation');
    expect(versionSelect()).toHaveValue('l1');
    const href = `${view.router.state.location.pathname}${view.router.state.location.search}${view.router.state.location.hash}`;
    view.unmount();
    renderLesson({ entries: [href] });
    await screen.findByText('L1 interpretation');
    await waitFor(() =>
      expect(mocks.listForLessonVersion).toHaveBeenLastCalledWith('l1', expect.any(AbortSignal)),
    );
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });

  it.each(['foreign-version', ''])(
    'rejects requested version %j without current fallback or Governance actions',
    async (requested) => {
      renderLesson({ entries: [`/lessons/lesson-1?lesson_version_id=${requested}`] });
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Keine andere Version wurde dafür eingesetzt',
      );
      expect(screen.queryByRole('article')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: hypothesisLabel })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: sourceReviewLabel })).not.toBeInTheDocument();
      expect(mocks.listForLessonVersion).not.toHaveBeenCalled();
      expect(mocks.execute).not.toHaveBeenCalled();
    },
  );

  it.each(['lesson', 'version', 'evidence link'])(
    'rejects a foreign %s owner before mounting Governance',
    async (invalidOwner) => {
      const invalid = reviewContext();
      if (invalidOwner === 'lesson') invalid.lesson.id = 'foreign';
      if (invalidOwner === 'version') invalid.history[1].version.lesson_id = 'foreign';
      if (invalidOwner === 'evidence link')
        invalid.history[1].evidence_links[0].lesson_version_id = 'l1';
      mocks.context.mockResolvedValue(invalid);
      renderLesson();
      await screen.findByText(/Keine neue Bestätigung bis zum erfolgreichen Neuladen/);
      expect(screen.queryByRole('article')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: hypothesisLabel })).not.toBeInTheDocument();
      expect(mocks.listForLessonVersion).not.toHaveBeenCalled();
      expect(mocks.execute).not.toHaveBeenCalled();
    },
  );

  it.each(['review', 'hypothesis'])(
    'keeps a dirty %s on stay and discards it only for the exact chosen version',
    async (kind) => {
      mocks.context.mockResolvedValue(reviewContext('REVIEW_RECOMMENDED'));
      const { router } = renderLesson({ entries: ['/lessons/lesson-1?marker=retained'] });
      if (kind === 'review') {
        await prepareReview('Neue Lesson-Version vorbereiten');
        fireEvent.change(
          screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version'),
          {
            target: { value: 'Unsaved revised interpretation' },
          },
        );
      } else await fillHypothesis();
      const field = kind === 'review' ? reason() : screen.getByLabelText('Titel');
      const previousValue = (field as HTMLInputElement).value;
      versionSelect().focus();
      fireEvent.change(versionSelect(), { target: { value: 'l1' } });
      expect(await screen.findAllByRole('alertdialog')).toHaveLength(1);
      expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
      expect(router.state.location.search).toBe('?marker=retained');
      click('Hier bleiben');
      expect(field).toHaveValue(previousValue);
      expect(versionSelect()).toHaveFocus();
      fireEvent.change(versionSelect(), { target: { value: 'l1' } });
      click(discardLabel);
      await screen.findByText('L1 interpretation');
      expect(router.state.location.search).toBe('?marker=retained&lesson_version_id=l1');
      expect(router.state.location.hash).toBe('#lesson-history');
      expect(
        screen.queryByRole('form', { name: 'Lesson-Prüfentscheidung' }),
      ).not.toBeInTheDocument();
      expect(await screen.findByLabelText('Titel')).toHaveValue('');
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(mocks.execute).not.toHaveBeenCalled();
      expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
    },
  );

  it('guards a dirty Lesson change and resumes exactly its original path, query and hash', async () => {
    const { router } = renderLesson();
    await fillHypothesis();
    const target = '/lessons/lesson-2?lesson_version_id=lesson-2-l1#lesson-history';
    await navigate(router, target);
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
    click('Hier bleiben');
    expect(screen.getByLabelText('Titel')).toHaveValue('Synthetic H1');
    await navigate(router, target);
    click(discardLabel);
    await screen.findByRole('heading', { name: 'Synthetic lesson-2' });
    expect(
      `${router.state.location.pathname}${router.state.location.search}${router.state.location.hash}`,
    ).toBe(target);
    expect(
      screen.getByText('Governance-Quelle: Lesson-Version 1 · lesson-2-l1'),
    ).toBeInTheDocument();
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
  });

  it('guards dirty browser Back and Forward and preserves their exact history targets', async () => {
    const { router } = renderLesson({
      entries: [
        '/lessons/lesson-1?lesson_version_id=l1#lesson-history',
        '/lessons/lesson-1?lesson_version_id=l2#lesson-history',
      ],
    });
    await fillHypothesis();
    await navigate(router, -1);
    await screen.findByRole('alertdialog');
    click('Hier bleiben');
    expect(router.state.location.search).toBe('?lesson_version_id=l2');
    expect(screen.getByLabelText('Titel')).toHaveValue('Synthetic H1');
    await navigate(router, -1);
    click(discardLabel);
    await screen.findByText('L1 interpretation');
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
    await fillHypothesis();
    await navigate(router, 1);
    await screen.findByRole('alertdialog');
    click(discardLabel);
    await screen.findByText('L2 interpretation');
    expect(router.state.location.search).toBe('?lesson_version_id=l2');
    expect(router.state.location.hash).toBe('#lesson-history');
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });

  it('publishes dirty input before the next render and protects native unload until cleared', async () => {
    const { router } = renderLesson();
    const title = await screen.findByLabelText('Titel');
    act(() => {
      fireEvent.change(title, { target: { value: 'Just typed' } });
      void router.navigate('/post-trade');
    });
    await screen.findByRole('alertdialog');
    expect(router.state.location.pathname).toBe('/lessons/lesson-1');
    expect(title).toHaveValue('Just typed');
    const dirtyUnload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(dirtyUnload);
    expect(dirtyUnload.defaultPrevented).toBe(true);
    click('Hier bleiben');
    fireEvent.change(title, { target: { value: '' } });
    const cleanUnload = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(cleanUnload);
    expect(cleanUnload.defaultPrevented).toBe(false);
    await navigate(router, '/post-trade');
    expect(await screen.findByRole('heading', { name: 'Post-Trade target' })).toBeInTheDocument();
  });

  it.each(['review', 'hypothesis'])(
    'synchronously blocks route changes and duplicate submits during a pending %s command',
    async (kind) => {
      const write = deferred<ReviewReceipt | LessonHypothesis>();
      if (kind === 'review') mocks.execute.mockReturnValue(write.promise);
      else mocks.createFromLessonVersion.mockReturnValue(write.promise);
      const { router } = renderLesson();
      const form =
        kind === 'review' ? await prepareReview() : (await fillHypothesis()).title.closest('form')!;
      act(() => {
        fireEvent.submit(form);
        fireEvent.submit(form);
        void router.navigate('/post-trade');
      });
      const dialog = await screen.findByRole('alertdialog');
      expect(
        within(dialog).getByRole('heading', { name: 'Speicherung läuft' }),
      ).toBeInTheDocument();
      expect(within(dialog).queryByRole('button', { name: discardLabel })).not.toBeInTheDocument();
      expect(screen.getAllByRole('alertdialog')).toHaveLength(1);
      expect(router.state.location.pathname).toBe('/lessons/lesson-1');
      expect(versionSelect()).toBeDisabled();
      expect(
        kind === 'review' ? mocks.execute : mocks.createFromLessonVersion,
      ).toHaveBeenCalledTimes(1);
      click('Hier bleiben');
      await act(async () => {
        write.resolve(kind === 'review' ? receipt : hypothesis('l2'));
        await write.promise;
      });
      expect(router.state.location.pathname).toBe('/lessons/lesson-1');
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      await navigate(router, '/post-trade');
      expect(await screen.findByRole('heading', { name: 'Post-Trade target' })).toBeInTheDocument();
    },
  );

  it('keeps the same-version form mounted and disabled throughout refresh failure and recovery', async () => {
    const readback = deferred<ReviewContext>();
    renderLesson({ entries: ['/lessons/lesson-1?lesson_version_id=l1'] });
    const { title, statement } = await fillHypothesis();
    mocks.context.mockReturnValueOnce(readback.promise);
    click('Lesson-Prüfstand neu laden');
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(statement).toHaveValue('Synthetic interpretation only');
    expect(title).toBeDisabled();
    expect(screen.getByRole('button', { name: hypothesisLabel })).toBeDisabled();
    fireEvent.submit(title.closest('form')!);
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
    await act(async () => {
      readback.reject(new Error('Synthetic context failure'));
      await readback.promise.catch(() => undefined);
    });
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toBeDisabled();
    mocks.context.mockResolvedValue({ ...reviewContext(), read_at: '2026-10-26T12:01:00Z' });
    click('Lesson-Prüfstand neu laden');
    await waitFor(() => expect(title).toBeEnabled());
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(statement).toHaveValue('Synthetic interpretation only');
    expect(mocks.listForLessonVersion).toHaveBeenCalledTimes(1);
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });

  it('rejects a refresh missing the selected historical snapshot while retaining its dirty form', async () => {
    renderLesson({ entries: ['/lessons/lesson-1?lesson_version_id=l1'] });
    const { title, statement } = await fillHypothesis();
    const incomplete = reviewContext();
    incomplete.history = incomplete.history.filter((entry) => entry.version.id !== 'l1');
    mocks.context.mockResolvedValue(incomplete);
    click('Lesson-Prüfstand neu laden');
    await screen.findByText(/Keine neue Bestätigung bis zum erfolgreichen Neuladen/);
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(screen.getByLabelText('Hypothese')).toBe(statement);
    expect(title).toHaveValue('Synthetic H1');
    expect(title).toBeDisabled();
    expect(screen.getByText('L1 interpretation')).toBeInTheDocument();
    expect(screen.queryByText('L2 interpretation')).not.toBeInTheDocument();
    expect(mocks.listForLessonVersion).toHaveBeenCalledTimes(1);
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });

  it('same-version URL actions and refresh preserve the confirmed receipt, draft and history entry', async () => {
    const { router } = renderLesson();
    await prepareReview();
    mocks.context.mockResolvedValue(reviewContext('REVIEW_RECOMMENDED'));
    click(confirmLabel);
    await screen.findByText(/Prüfentscheidung gespeichert: transition-1/);
    await screen.findByText('Heutiger Lesson-Status: REVIEW_RECOMMENDED');
    const { title, statement } = await fillHypothesis();
    const key = router.state.location.key;
    const link = screen.getByRole('link', { name: 'Genau diese Lesson-Version öffnen' });
    expect(link).toHaveAttribute('href', '/lessons/lesson-1?lesson_version_id=l2#lesson-history');
    fireEvent.click(link);
    fireEvent.change(versionSelect(), { target: { value: 'l2' } });
    expect(router.state.location.key).toBe(key);
    expect(router.state.location.search).toBe('');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(statement).toHaveValue('Synthetic interpretation only');
    click('Lesson-Prüfstand neu laden');
    await waitFor(() => expect(title).toBeEnabled());
    expect(screen.getByText(/Prüfentscheidung gespeichert: transition-1/)).toBeInTheDocument();
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(router.state.location.key).toBe(key);
    expect(mocks.execute).toHaveBeenCalledTimes(1);
    expect(mocks.listForLessonVersion).toHaveBeenCalledTimes(1);
    await navigate(router, '/lessons/lesson-1#lesson-history');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(screen.getByText(/Prüfentscheidung gespeichert: transition-1/)).toBeInTheDocument();
  });

  it('retains a successful successor receipt and releases mutation before result navigation despite readback failure', async () => {
    mocks.context.mockResolvedValue(reviewContext('REVIEW_RECOMMENDED'));
    mocks.execute.mockResolvedValue({ ...receipt, result_id: 'l3', result_type: 'LESSON_VERSION' });
    const { router } = renderLesson();
    await prepareReview('Neue Lesson-Version vorbereiten');
    expect(
      screen.queryByRole('article', { name: 'Lesson-Snapshot Version 2' }),
    ).not.toBeInTheDocument();
    const content = screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version');
    expect(content).toHaveValue('L2 interpretation');
    fireEvent.change(content, { target: { value: 'Explicit L3 interpretation' } });
    mocks.context.mockRejectedValueOnce(new Error('Confirmed successor readback unavailable'));
    click(confirmLabel);
    await screen.findByText(/Prüfentscheidung gespeichert: l3/);
    await waitFor(() => expect(router.state.location.search).toBe('?lesson_version_id=l3'));
    expect(router.state.location.hash).toBe('#lesson-history');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await screen.findByText(/Keine neue Bestätigung bis zum erfolgreichen Neuladen/);
    expect(screen.queryByRole('form', { name: 'Lesson-Prüfentscheidung' })).not.toBeInTheDocument();
    expect(screen.queryByText('L2 interpretation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: hypothesisLabel })).not.toBeInTheDocument();
    expect(mocks.execute).toHaveBeenCalledTimes(1);
    expect(mocks.execute.mock.calls[0][1]).toMatchObject({
      operation: 'NEW_VERSION',
      expected_current_version_id: 'l2',
      expected_current_state: 'REVIEW_RECOMMENDED',
      expected_open_signal_id: null,
      main_category: 'Process',
      content: 'Explicit L3 interpretation',
      evidence: [
        { learning_evidence_id: 'l2-e1', relation: 'SUPPORTS' },
        { learning_evidence_id: 'l2-e2', relation: 'CONTRADICTS' },
        { learning_evidence_id: 'l2-e3', relation: 'CONTEXTUAL' },
      ],
      confirmed: true,
    });
    const successor = reviewContext('CURRENT', 'lesson-1', 3);
    successor.history[2].version.content = 'Explicit L3 interpretation';
    successor.history[2].evidence_links = successor.history[1].evidence_links.map(
      (link, index) => ({
        ...link,
        id: `l3-link${index + 1}`,
        lesson_version_id: 'l3',
      }),
    );
    mocks.context.mockResolvedValue(successor);
    click('Lesson-Prüfstand neu laden');
    await screen.findByText('Explicit L3 interpretation');
    await screen.findByRole('button', { name: hypothesisLabel });
    expect(screen.getByText(/Prüfentscheidung gespeichert: l3/)).toBeInTheDocument();
    expect(mocks.execute).toHaveBeenCalledTimes(1);
    expect(mocks.listForLessonVersion).toHaveBeenLastCalledWith('l3', expect.any(AbortSignal));
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });

  it('does not discard an independent hypothesis draft when a confirmed successor requests navigation', async () => {
    mocks.context.mockResolvedValue(reviewContext('REVIEW_RECOMMENDED'));
    mocks.execute.mockResolvedValue({ ...receipt, result_id: 'l3', result_type: 'LESSON_VERSION' });
    const { router } = renderLesson();
    await fillHypothesis();
    await prepareReview('Neue Lesson-Version vorbereiten');
    mocks.context.mockResolvedValue(reviewContext('CURRENT', 'lesson-1', 3));
    click(confirmLabel);
    await screen.findByText(/Prüfentscheidung gespeichert: l3/);
    await screen.findByRole('alertdialog');
    expect(screen.getByRole('button', { name: discardLabel })).toBeEnabled();
    expect(router.state.location.search).toBe('');
    click('Hier bleiben');
    expect(screen.getByLabelText('Titel')).toHaveValue('Synthetic H1');
    expect(screen.getByText('L2 interpretation')).toBeInTheDocument();
    fireEvent.change(versionSelect(), { target: { value: 'l3' } });
    click(discardLabel);
    await screen.findByText('L3 interpretation');
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
    expect(screen.getByText(/Prüfentscheidung gespeichert: l3/)).toBeInTheDocument();
    expect(router.state.location.search).toBe('?lesson_version_id=l3');
    expect(mocks.execute).toHaveBeenCalledTimes(1);
  });

  it('isolates an old A read from a later A visit after A to B to A navigation', async () => {
    const old = deferred<ReviewContext>();
    mocks.context.mockImplementationOnce(() => old.promise);
    const { router } = renderLesson();
    await waitFor(() => expect(mocks.context).toHaveBeenCalledTimes(1));
    await navigate(router, '/lessons/lesson-2?lesson_version_id=lesson-2-l1');
    await screen.findByRole('heading', { name: 'Synthetic lesson-2' });
    await navigate(router, '/lessons/lesson-1?lesson_version_id=l1');
    await screen.findByRole('heading', { name: 'Synthetic Lesson' });
    const { title } = await fillHypothesis();
    const stale = reviewContext();
    stale.lesson.title = 'Stale first A visit';
    stale.history[0].version.content = 'Stale A interpretation';
    await act(async () => {
      old.resolve(stale);
      await old.promise;
    });
    expect(screen.queryByText('Stale first A visit')).not.toBeInTheDocument();
    expect(screen.queryByText('Stale A interpretation')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(screen.getByText('Governance-Quelle: Lesson-Version 1 · l1')).toBeInTheDocument();
    expect(mocks.execute).not.toHaveBeenCalled();
  });

  it('retains the live StrictMode snapshot and hypothesis draft when its superseded read settles', async () => {
    const firstRead = deferred<ReviewContext>();
    mocks.context.mockReturnValueOnce(firstRead.promise);
    renderLesson({ entries: ['/lessons/lesson-1?lesson_version_id=l1'], strict: true });
    await screen.findByText('L1 interpretation');
    const { title } = await fillHypothesis();
    const stale = reviewContext();
    stale.history[0].version.content = 'Superseded StrictMode read';
    await act(async () => {
      firstRead.resolve(stale);
      await firstRead.promise;
    });
    expect(screen.queryByText('Superseded StrictMode read')).not.toBeInTheDocument();
    expect(screen.getByText('L1 interpretation')).toBeInTheDocument();
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(title).toHaveValue('Synthetic H1');
    expect(mocks.execute).not.toHaveBeenCalled();
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });
});
