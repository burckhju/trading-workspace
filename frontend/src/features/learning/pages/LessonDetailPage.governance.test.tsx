import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LessonDetailPage } from './LessonDetailPage';

const mocks = vi.hoisted(() => ({
  getLesson: vi.fn(),
  context: vi.fn(),
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
}));
vi.mock('../services/lessonReadbackClient', () => ({ lessonReadbackClient: mocks }));
vi.mock('../services/lessonReviewClient', () => ({ lessonReviewClient: mocks }));
vi.mock('../../model/services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks }));
vi.mock('../../model/components/HypothesisProposalPanel', () => ({
  HypothesisProposalPanel: () => null,
}));
vi.mock('../components/JournalEvidenceOrigin', () => ({ JournalEvidenceOrigin: () => null }));

function renderLesson(version = 'l1') {
  return render(
    <MemoryRouter initialEntries={[`/lessons/lesson-1?lesson_version_id=${version}`]}>
      <Routes>
        <Route path="/lessons/:lessonId" element={<LessonDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('exact Lesson snapshot to Governance handoff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getLesson.mockResolvedValue({
      lesson_id: 'lesson-1',
      current_version_id: 'l2',
      current_state: 'CURRENT',
      version: 2,
      title: 'Synthetic Lesson',
      main_category: 'Process',
      content: 'L2 current',
      evidence: [],
    });
    mocks.context.mockResolvedValue({
      lesson: {
        id: 'lesson-1',
        title: 'Synthetic Lesson',
        current_version_id: 'l2',
        current_state: 'CURRENT',
      },
      history: [1, 2].map((n) => ({
        version: {
          id: `l${n}`,
          lesson_id: 'lesson-1',
          version: n,
          main_category: 'Process',
          content: `L${n} interpretation`,
          created_at: '2026-10-24T10:00:00Z',
          created_by: 'actor',
          supersedes_version_id: n === 2 ? 'l1' : null,
        },
        evidence_links: [],
      })),
      signals: [],
      transitions: [],
      read_at: '2026-10-25T10:00:00Z',
    });
    mocks.listForLessonVersion.mockResolvedValue([]);
    mocks.createFromLessonVersion.mockImplementation((id: string, input: object) =>
      Promise.resolve({
        ...input,
        id: 'h1',
        source_lesson_version_id: id,
        status: 'OPEN',
      }),
    );
  });

  it('creates only against the viewed historical L1 after L2 exists', async () => {
    renderLesson();
    expect(
      await screen.findByRole('article', { name: 'Lesson-Snapshot Version 1' }),
    ).toBeInTheDocument();
    await screen.findByRole('button', { name: 'Hypothese für FT-013 anlegen' });
    expect(mocks.listForLessonVersion).toHaveBeenCalledWith('l1', expect.any(AbortSignal));
    expect(mocks.listForLessonVersion).not.toHaveBeenCalledWith('l2', expect.any(AbortSignal));
    fireEvent.change(screen.getByLabelText('Titel'), { target: { value: 'Synthetic H1' } });
    fireEvent.change(screen.getByLabelText('Hypothese'), {
      target: { value: 'Synthetic interpretation only' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' }));
    await waitFor(() =>
      expect(mocks.createFromLessonVersion).toHaveBeenCalledWith('l1', {
        title: 'Synthetic H1',
        statement: 'Synthetic interpretation only',
      }),
    );
  });

  it('binds an explicit history selection and return to that exact snapshot', async () => {
    renderLesson();
    const selection = await screen.findByRole('combobox', { name: 'Lesson-Version ansehen' });
    await screen.findByRole('button', { name: 'Hypothese für FT-013 anlegen' });
    mocks.listForLessonVersion.mockClear();
    fireEvent.change(selection, { target: { value: 'l2' } });
    await waitFor(() =>
      expect(mocks.listForLessonVersion).toHaveBeenCalledWith('l2', expect.any(AbortSignal)),
    );
    fireEvent.change(selection, { target: { value: 'l1' } });
    await waitFor(() =>
      expect(mocks.listForLessonVersion).toHaveBeenCalledWith('l1', expect.any(AbortSignal)),
    );
  });

  it('does not offer a governance command for an unknown requested snapshot', async () => {
    renderLesson('foreign-version');
    expect(
      await screen.findByText(/angeforderte Lesson-Version wurde nicht gefunden/),
    ).toBeInTheDocument();
    expect(mocks.listForLessonVersion).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Hypothese für FT-013 anlegen' })).toBeNull();
  });
});
