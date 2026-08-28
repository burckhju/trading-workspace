import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LessonHypothesisPanel } from './LessonHypothesisPanel';

const mocks = vi.hoisted(() => ({
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
}));

vi.mock('../services/lessonHypothesisClient', () => ({
  lessonHypothesisClient: mocks,
}));

vi.mock('./HypothesisProposalPanel', () => ({
  HypothesisProposalPanel: ({ hypothesisId }: { hypothesisId: string }) => (
    <div>Proposal workflow {hypothesisId}</div>
  ),
}));

describe('LessonHypothesisPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listForLessonVersion.mockResolvedValue([]);
  });

  it('shows existing FT-013 hypotheses and suppresses duplicate creation by default', async () => {
    mocks.listForLessonVersion.mockResolvedValue([
      {
        id: 'hypothesis-1',
        title: 'Exit discipline',
        statement: 'Late exits reduce expectancy.',
        status: 'OPEN',
        source_lesson_version_id: 'lesson-version-1',
        created_at: '2026-08-28T12:00:00Z',
        created_by: 'actor-1',
      },
    ]);

    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);

    expect(await screen.findByText('Bereits an FT-013 übergeben')).toBeInTheDocument();
    expect(screen.getByText('Exit discipline')).toBeInTheDocument();
    expect(screen.getByText('Proposal workflow hypothesis-1')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hypothese für FT-013 anlegen' })).toBeNull();
  });

  it('creates an explicit hypothesis from the current LessonVersion', async () => {
    mocks.createFromLessonVersion.mockResolvedValue({
      id: 'hypothesis-1',
      title: 'Exit discipline',
      statement: 'Late exits reduce expectancy.',
      status: 'OPEN',
      source_lesson_version_id: 'lesson-version-1',
      created_at: '2026-08-28T12:00:00Z',
      created_by: 'actor-1',
    });

    render(<LessonHypothesisPanel lessonVersionId="lesson-version-1" />);

    await screen.findByRole('button', { name: 'Hypothese für FT-013 anlegen' });
    fireEvent.change(screen.getByLabelText('Titel'), { target: { value: 'Exit discipline' } });
    fireEvent.change(screen.getByLabelText('Hypothese'), {
      target: { value: 'Late exits reduce expectancy.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' }));

    await waitFor(() =>
      expect(mocks.createFromLessonVersion).toHaveBeenCalledWith('lesson-version-1', {
        title: 'Exit discipline',
        statement: 'Late exits reduce expectancy.',
      }),
    );
    expect(await screen.findByText('Bereits an FT-013 übergeben')).toBeInTheDocument();
  });
});
