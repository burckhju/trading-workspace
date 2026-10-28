import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
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

  it('requires explicit interpretation fields before creating a Lesson', async () => {
    render(<LessonDraftFromEvidence learningEvidenceId="evidence-1" />);

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
    expect(await screen.findByText(/Lesson angelegt:/)).toBeInTheDocument();
  });

  it('reports edits and submit start synchronously, and guards duplicate submission', async () => {
    const report = vi.fn();
    let resolve!: (value: Awaited<ReturnType<typeof client.createFromEvidence>>) => void;
    const response = new Promise<Awaited<ReturnType<typeof client.createFromEvidence>>>((done) => {
      resolve = done;
    });
    client.createFromEvidence.mockImplementation(() => {
      expect(report).toHaveBeenLastCalledWith({ dirty: true, pending: true });
      return response;
    });
    render(
      <LessonDraftFromEvidence learningEvidenceId="evidence-1" onNavigationStateChange={report} />,
    );
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), { target: { value: 'Local title' } });
    expect(report).toHaveBeenLastCalledWith({ dirty: true, pending: false });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), {
      target: { value: 'Local meaning' },
    });
    const form = screen.getByRole('button', { name: 'Lesson anlegen' }).closest('form')!;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(client.createFromEvidence).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Lesson-Titel')).toBeDisabled();
    await act(async () => {
      resolve({
        lesson_id: 'lesson-2',
        current_version_id: 'lv-2',
        version: 1,
        current_state: 'CURRENT',
        title: 'Local title',
        main_category: 'Execution',
        content: 'Local meaning',
        evidence: [],
      });
      await response;
    });
    expect(report).toHaveBeenLastCalledWith({ dirty: false, pending: false });
    expect(await screen.findByText(/Lesson angelegt:/)).toHaveTextContent('lesson-2');
  });

  it('keeps input pinned to its original evidence and requires explicit context discard', () => {
    const report = vi.fn();
    const view = render(
      <LessonDraftFromEvidence learningEvidenceId="evidence-1" onNavigationStateChange={report} />,
    );
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), {
      target: { value: 'Original interpretation' },
    });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), {
      target: { value: 'Meaning for source one' },
    });
    view.rerender(
      <LessonDraftFromEvidence learningEvidenceId="evidence-2" onNavigationStateChange={report} />,
    );
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Original interpretation');
    expect(screen.getByRole('alert')).toHaveTextContent('Evidence evidence-1');
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(client.createFromEvidence).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
    );
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    expect(report).toHaveBeenLastCalledWith({ dirty: false, pending: false });
    expect(client.createFromEvidence).not.toHaveBeenCalled();
  });

  it('keeps a pending POST bound to its source through a context change', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof client.createFromEvidence>>) => void;
    const response = new Promise<Awaited<ReturnType<typeof client.createFromEvidence>>>((done) => {
      resolve = done;
    });
    client.createFromEvidence.mockReturnValue(response);
    const view = render(<LessonDraftFromEvidence learningEvidenceId="evidence-1" />);
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), { target: { value: 'Title' } });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), { target: { value: 'Meaning' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    view.rerender(<LessonDraftFromEvidence learningEvidenceId="evidence-2" discardVersion={1} />);
    expect(
      screen.getByRole('button', { name: 'Eingaben verwerfen und neue Evidence öffnen' }),
    ).toBeDisabled();
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Title');
    expect(client.createFromEvidence).toHaveBeenCalledExactlyOnceWith(
      'evidence-1',
      expect.objectContaining({ title: 'Title' }),
    );
    await act(async () => {
      resolve({
        lesson_id: 'lesson-3',
        current_version_id: 'lv-3',
        version: 1,
        current_state: 'CURRENT',
        title: 'Title',
        main_category: 'Execution',
        content: 'Meaning',
        evidence: [],
      });
      await response;
    });
    expect(await screen.findByText(/Lesson angelegt:/)).toHaveTextContent('lesson-3');
    expect(screen.getByRole('alert')).toHaveTextContent('Evidence evidence-1');
  });

  it('preserves input after an unknown outcome without repeating a non-idempotent POST', async () => {
    client.createFromEvidence.mockRejectedValue(new Error('connection ended after commit'));
    render(<LessonDraftFromEvidence learningEvidenceId="evidence-1" />);
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), {
      target: { value: 'Uncertain title' },
    });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), { target: { value: 'Meaning' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('nicht idempotent wiederholt');
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Uncertain title');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(client.createFromEvidence).toHaveBeenCalledTimes(1);
  });

  it('discards only on an explicit parent decision and ignores a late unmounted result', async () => {
    const onCreated = vi.fn();
    const report = vi.fn();
    const view = render(
      <LessonDraftFromEvidence
        learningEvidenceId="evidence-1"
        onNavigationStateChange={report}
        discardVersion={0}
        onCreated={onCreated}
      />,
    );
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), { target: { value: 'Unsaved' } });
    view.rerender(
      <LessonDraftFromEvidence
        learningEvidenceId="evidence-1"
        onNavigationStateChange={report}
        discardVersion={1}
        onCreated={onCreated}
      />,
    );
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    expect(client.createFromEvidence).not.toHaveBeenCalled();
    let resolve!: (value: Awaited<ReturnType<typeof client.createFromEvidence>>) => void;
    const response = new Promise<Awaited<ReturnType<typeof client.createFromEvidence>>>((done) => {
      resolve = done;
    });
    client.createFromEvidence.mockReturnValue(response);
    fireEvent.change(screen.getByLabelText('Lesson-Titel'), { target: { value: 'Title' } });
    fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
    fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), { target: { value: 'Meaning' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    view.unmount();
    await act(async () => {
      resolve({
        lesson_id: 'old-lesson',
        current_version_id: 'lv',
        version: 1,
        current_state: 'CURRENT',
        title: 'Title',
        main_category: 'Execution',
        content: 'Meaning',
        evidence: [],
      });
      await response;
    });
    expect(onCreated).not.toHaveBeenCalled();
    expect(report).toHaveBeenLastCalledWith({ dirty: false, pending: false });
  });
});
