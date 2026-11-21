import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, Link, RouterProvider, useSearchParams } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  lessonListClient,
  type LessonListItem,
  type LessonListPageResponse,
} from '../services/lessonListClient';
import { lessonReviewClient, type ReviewContext } from '../services/lessonReviewClient';
import { lessonListReturnLink } from '../services/lessonNavigation';
import { LessonListPage } from './LessonListPage';

vi.mock('../services/lessonListClient', () => ({ lessonListClient: { list: vi.fn() } }));
vi.mock('../services/lessonReviewClient', () => ({
  lessonReviewClient: { context: vi.fn(), source: vi.fn() },
}));

const item: LessonListItem = {
  lesson_id: 'lesson-1',
  current_version_id: 'version-2',
  version: 2,
  current_state: 'CURRENT',
  title: 'Exit vorher begründen',
  main_category: 'Prozess',
  content: 'Synthetische Erkenntnis aus einem abgeschlossenen Trade.',
  created_at: '2026-11-01T10:00:00Z',
  created_by: 'synthetic-actor',
};

function LessonDetailReturn() {
  const [params] = useSearchParams();
  const href = lessonListReturnLink(params);
  return (
    <>
      <h1>Erkenntnisdetail</h1>
      {href && <Link to={href}>Zur Liste</Link>}
    </>
  );
}

function show(entry = '/lessons') {
  const router = createMemoryRouter(
    [
      { path: '/lessons', element: <LessonListPage /> },
      { path: '/model-improvements', element: <LessonListPage purpose="models" /> },
      { path: '/lessons/:lessonId', element: <LessonDetailReturn /> },
    ],
    { initialEntries: [entry] },
  );
  render(<RouterProvider router={router} />);
  return router;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe('LessonListPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
    vi.mocked(lessonListClient.list).mockResolvedValue({ items: [item], next_cursor: null });
  });

  it('reads the existing page and links its exact version without inferring source health', async () => {
    show();
    expect(screen.getByRole('status')).toHaveTextContent('werden geladen');
    const link = await screen.findByRole('link', { name: item.title });
    const url = new URL(link.getAttribute('href')!, 'http://workspace.test');
    expect(url.searchParams.get('lesson_version_id')).toBe('version-2');
    expect(url.hash).toBe('#lesson-history');
    expect(screen.getByText('Aktuelle Interpretation')).toBeVisible();
    expect(screen.getByText(/Den heutigen Quellenstand können Sie/)).toBeVisible();
    expect(lessonReviewClient.context).not.toHaveBeenCalled();
    expect(lessonReviewClient.source).not.toHaveBeenCalled();
    expect(lessonListClient.list).toHaveBeenCalledWith(null, expect.any(AbortSignal));
  });

  it('pages with opaque cursors and carries the same list slice into a detail return link', async () => {
    vi.mocked(lessonListClient.list)
      .mockResolvedValueOnce({ items: [item], next_cursor: 'cursor:/+ synthetic' })
      .mockResolvedValueOnce({
        items: [{ ...item, lesson_id: 'lesson-2', title: 'Zweite Seite' }],
        next_cursor: null,
      });
    const router = show();
    fireEvent.click(await screen.findByRole('link', { name: 'Weitere Erkenntnisse' }));
    const link = await screen.findByRole('link', { name: 'Zweite Seite' });
    expect(new URLSearchParams(router.state.location.search).get('cursor')).toBe(
      'cursor:/+ synthetic',
    );
    expect(lessonListClient.list).toHaveBeenLastCalledWith(
      'cursor:/+ synthetic',
      expect.any(AbortSignal),
    );
    const destination = new URL(link.getAttribute('href')!, 'http://workspace.test');
    expect(lessonListReturnLink(destination.searchParams)).toBe(
      `/lessons?${new URLSearchParams({ cursor: 'cursor:/+ synthetic' })}`,
    );
    expect(screen.getByRole('link', { name: 'Vorige Seite' })).toHaveAttribute('href', '/lessons');
    expect(screen.getByText('Ende der Liste')).toBeVisible();
  });

  it('opens model work with the same pinned Lesson source and owned return route', async () => {
    show('/model-improvements?cursor=page-two');
    const link = await screen.findByRole('link', { name: 'Modellverbesserung zu dieser Version' });
    const url = new URL(link.getAttribute('href')!, 'http://workspace.test');
    expect(url.hash).toBe('#model-improvement');
    expect(url.searchParams.get('lesson_version_id')).toBe('version-2');
    expect(lessonListReturnLink(url.searchParams)).toBe('/model-improvements?cursor=page-two');
    expect(screen.getByText(/Freigabe und Aktivierung bleiben getrennte Schritte/)).toBeVisible();
  });

  it('returns through every previously visited page without changing opaque cursors', async () => {
    const cursors = [null, 'page:a/+ exact', 'page:b?=& exact', 'page:c%/ exact'];
    vi.mocked(lessonListClient.list).mockImplementation((cursor) => {
      const page = cursors.indexOf(cursor ?? null);
      if (page < 0) return Promise.reject(new Error('Unexpected cursor'));
      return Promise.resolve({
        items: [{ ...item, lesson_id: `lesson-${page}`, title: `Ausschnitt ${page + 1}` }],
        next_cursor: cursors[page + 1] ?? null,
      });
    });
    const router = show();
    for (let page = 1; page < cursors.length; page++) {
      fireEvent.click(await screen.findByRole('link', { name: 'Weitere Erkenntnisse' }));
      expect(await screen.findByRole('link', { name: `Ausschnitt ${page + 1}` })).toBeVisible();
      expect(new URLSearchParams(router.state.location.search).get('cursor')).toBe(cursors[page]);
    }
    for (let page = cursors.length - 2; page >= 0; page--) {
      fireEvent.click(screen.getByRole('link', { name: 'Vorige Seite' }));
      expect(await screen.findByRole('link', { name: `Ausschnitt ${page + 1}` })).toBeVisible();
      expect(new URLSearchParams(router.state.location.search).get('cursor')).toBe(cursors[page]);
      expect(lessonListClient.list).toHaveBeenLastCalledWith(
        cursors[page],
        expect.any(AbortSignal),
      );
    }
    expect(screen.queryByRole('link', { name: 'Vorige Seite' })).not.toBeInTheDocument();
  });

  it.each(['/lessons', '/model-improvements'])(
    'retains the page trail after a state-free detail return to %s',
    async (path) => {
      const cursors = [null, 'first:+/ exact', 'second:+=/ exact'];
      vi.mocked(lessonListClient.list).mockImplementation((cursor) => {
        const page = cursors.indexOf(cursor ?? null);
        if (page < 0) return Promise.reject(new Error('Unexpected cursor'));
        return Promise.resolve({
          items: [{ ...item, title: `Ausschnitt ${page + 1}` }],
          next_cursor: cursors[page + 1] ?? null,
        });
      });
      const router = show(path);
      fireEvent.click(await screen.findByRole('link', { name: 'Weitere Erkenntnisse' }));
      expect(await screen.findByRole('link', { name: 'Ausschnitt 2' })).toBeVisible();
      fireEvent.click(screen.getByRole('link', { name: 'Weitere Erkenntnisse' }));
      fireEvent.click(await screen.findByRole('link', { name: 'Ausschnitt 3' }));
      expect(await screen.findByRole('heading', { name: 'Erkenntnisdetail' })).toBeVisible();
      fireEvent.click(screen.getByRole('link', { name: 'Zur Liste' }));
      expect(await screen.findByRole('link', { name: 'Ausschnitt 3' })).toBeVisible();
      expect(router.state.location.state).toBeNull();
      expect(router.state.location.pathname).toBe(path);
      expect(new URLSearchParams(router.state.location.search).get('cursor')).toBe(cursors[2]);
      fireEvent.click(screen.getByRole('link', { name: 'Vorige Seite' }));
      expect(await screen.findByRole('link', { name: 'Ausschnitt 2' })).toBeVisible();
      fireEvent.click(screen.getByRole('link', { name: 'Vorige Seite' }));
      expect(await screen.findByRole('link', { name: 'Ausschnitt 1' })).toBeVisible();
    },
  );

  it('does not invent a previous page for an unrelated list purpose', async () => {
    vi.mocked(lessonListClient.list)
      .mockResolvedValueOnce({ items: [item], next_cursor: 'same-opaque-cursor' })
      .mockResolvedValue({ items: [item], next_cursor: null });
    const router = show();
    fireEvent.click(await screen.findByRole('link', { name: 'Weitere Erkenntnisse' }));
    expect(await screen.findByRole('link', { name: 'Vorige Seite' })).toHaveAttribute(
      'href',
      '/lessons',
    );
    await act(() => router.navigate('/model-improvements?cursor=same-opaque-cursor'));
    expect(await screen.findByRole('link', { name: item.title })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Vorige Seite' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zur ersten Seite' })).toHaveAttribute(
      'href',
      '/model-improvements',
    );
  });

  it('distinguishes empty and failed reads and retries the same cursor', async () => {
    vi.mocked(lessonListClient.list)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ items: [], next_cursor: null });
    show('/lessons?cursor=page-two');
    expect(await screen.findByRole('alert')).toHaveTextContent('nicht geladen');
    expect(screen.queryByText('Keine weiteren Erkenntnisse')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Erneut laden' }));
    expect(
      await screen.findByRole('heading', { name: 'Keine weiteren Erkenntnisse' }),
    ).toBeVisible();
    expect(lessonListClient.list).toHaveBeenLastCalledWith('page-two', expect.any(AbortSignal));
  });

  it.each(['/lessons?cursor=', '/lessons?cursor=a&cursor=b'])(
    'does not normalize an invalid cursor context: %s',
    (entry) => {
      show(entry);
      expect(screen.getByRole('alert')).toHaveTextContent('Listenausschnitt nicht eindeutig');
      expect(lessonListClient.list).not.toHaveBeenCalled();
    },
  );

  it('ignores a late prior page when the user returns to a different cursor', async () => {
    const old = deferred<LessonListPageResponse>();
    vi.mocked(lessonListClient.list)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce({
        items: [{ ...item, title: 'Aktueller Ausschnitt' }],
        next_cursor: null,
      });
    const router = show('/lessons?cursor=old');
    const signal = vi.mocked(lessonListClient.list).mock.calls[0][1]!;
    await act(() => router.navigate('/lessons?cursor=new'));
    expect(await screen.findByRole('link', { name: 'Aktueller Ausschnitt' })).toBeVisible();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      old.resolve({ items: [{ ...item, title: 'Veralteter Ausschnitt' }], next_cursor: null });
      await old.promise;
    });
    expect(screen.queryByText('Veralteter Ausschnitt')).not.toBeInTheDocument();
  });

  it('inspects only the explicitly opened exact version and retains inspection across collapse', async () => {
    vi.mocked(lessonReviewClient.context).mockResolvedValue({
      lesson: {
        id: item.lesson_id,
        title: item.title,
        current_version_id: 'version-3',
        current_state: 'REVIEW_RECOMMENDED',
      },
      history: [
        {
          version: {
            id: item.current_version_id,
            lesson_id: item.lesson_id,
            version: 2,
            main_category: item.main_category,
            content: item.content,
            created_at: item.created_at,
            created_by: item.created_by,
            supersedes_version_id: null,
          },
          evidence_links: [
            {
              id: 'link-1',
              lesson_version_id: item.current_version_id,
              learning_evidence_id: 'evidence-1',
              relation: 'SUPPORTS',
            },
          ],
        },
      ],
      signals: [],
      transitions: [],
      read_at: item.created_at,
    } satisfies ReviewContext);
    vi.mocked(lessonReviewClient.source).mockResolvedValue({
      evidence_id: 'evidence-1',
      source_type: 'FT011',
      source_version_id: 'review-1',
      source_currentness: 'SUPERSEDED',
      review_currentness: null,
      superseded_by_version_id: 'review-2',
      checked_at: item.created_at,
    });
    show();
    const summary = await screen.findByText('Quellenstatus für Version 2 prüfen');
    const details = summary.closest('details')!;
    details.open = true;
    fireEvent(details, new Event('toggle'));
    expect(
      await screen.findByText('Quellversion jetzt: Durch neuere Version ersetzt'),
    ).toBeVisible();
    expect(lessonReviewClient.source).toHaveBeenCalledWith('evidence-1', expect.any(AbortSignal));
    details.open = false;
    fireEvent(details, new Event('toggle'));
    details.open = true;
    fireEvent(details, new Event('toggle'));
    await waitFor(() =>
      expect(
        within(details).getByText('Quellversion jetzt: Durch neuere Version ersetzt'),
      ).toBeVisible(),
    );
    expect(lessonReviewClient.context).toHaveBeenCalledTimes(1);
    expect(lessonReviewClient.source).toHaveBeenCalledTimes(1);
  });
});
