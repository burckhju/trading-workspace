import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { lessonDraftClient } from '../services/lessonDraftClient';
import { LessonDraftFromEvidence } from './LessonDraftFromEvidence';

vi.mock('../services/lessonDraftClient', () => ({
  lessonDraftClient: {
    createFromEvidence: vi.fn(),
  },
}));

const client = vi.mocked(lessonDraftClient);

describe('LessonDraftFromEvidence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.createFromEvidence.mockResolvedValue({
      lesson_id: 'lesson-1',
      current_version_id: 'version-1',
      version: 1,
      current_state: 'CURRENT',
      title: 'Discipline',
      main_category: 'Execution',
      content: 'Wait for confirmation.',
      evidence: [],
    });
  });

  it('requires explicit interpretation fields and links directly to the created Lesson', async () => {
    render(
      <MemoryRouter>
        <LessonDraftFromEvidence learningEvidenceId="evidence-1" />
      </MemoryRouter>,
    );

    const button = screen.getByRole('button', { name: 'Lesson anlegen' });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Lesson-Titel'), {
      target: { value: 'Discipline' },
    });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), {
      target: { value: 'Execution' },
    });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), {
      target: { value: 'Wait for confirmation.' },
    });

    fireEvent.click(button);

    await waitFor(() =>
      expect(client.createFromEvidence).toHaveBeenCalledWith('evidence-1', {
        title: 'Discipline',
        main_category: 'Execution',
        content: 'Wait for confirmation.',
        tags: [],
      }),
    );
    expect(await screen.findByText('Lesson LS-LESSON-1 wurde angelegt.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Lesson öffnen' })).toHaveAttribute(
      'href',
      '/lessons/lesson-1',
    );
  });
});
