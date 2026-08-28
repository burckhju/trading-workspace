import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { LessonEvidenceReference } from '../../learning/types/lessonReadback';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { PostTradeLearningPage } from './PostTradeLearningPage';

vi.mock('./PostTradeReviewPage', () => ({
  PostTradeReviewPage: () => <div>review</div>,
}));

vi.mock('../../learning/components/LessonDraftFromEvidence', () => ({
  LessonDraftFromEvidence: () => <div>lesson-form</div>,
}));

const status = vi.fn(
  async (_tradeId: string, _signal?: AbortSignal): Promise<Ft011MaterializationStatus> => ({
    ready: true,
    reason: 'READY',
    materialized: true,
    learning_evidence_id: 'evidence-1',
    exit_review_version_id: 'version-1',
  }),
);
const listForEvidence = vi.fn(
  async (
    _learningEvidenceId: string,
    _signal?: AbortSignal,
  ): Promise<LessonEvidenceReference[]> => [],
);

vi.mock('../../learning/services/materializationClient', () => ({
  ft011MaterializationClient: { status },
}));

vi.mock('../../learning/services/lessonReadbackClient', () => ({
  lessonReadbackClient: { listForEvidence },
}));

describe('PostTradeLearningPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows existing Lessons and suppresses duplicate creation form', async () => {
    listForEvidence.mockResolvedValue([
      {
        lesson_id: 'lesson-1',
        current_version_id: 'lesson-version-1',
        current_state: 'CURRENT',
        title: 'Exit discipline',
      },
    ]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Bereits interpretiert')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Exit discipline/ })).toHaveAttribute(
      'href',
      '/lessons/lesson-1',
    );
    expect(screen.queryByText('lesson-form')).not.toBeInTheDocument();
  });

  it('shows the create form when no Lesson references the Evidence', async () => {
    listForEvidence.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(listForEvidence).toHaveBeenCalledWith('evidence-1', expect.anything()),
    );
    expect(screen.getByText('lesson-form')).toBeInTheDocument();
  });
});
