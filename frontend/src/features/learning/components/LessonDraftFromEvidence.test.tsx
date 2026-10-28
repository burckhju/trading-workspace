import { act, fireEvent, render as renderView, screen, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MarketApiError } from '../../market/services/http';
import { lessonDraftClient } from '../services/lessonDraftClient';
import { LessonDraftFromEvidence } from './LessonDraftFromEvidence';

vi.mock('../services/lessonDraftClient', () => ({
  lessonDraftClient: {
    createFromEvidence: vi.fn(),
  },
}));

const client = vi.mocked(lessonDraftClient);

function render(ui: ReactElement) {
  return renderView(ui, { wrapper: MemoryRouter });
}

function fillInterpretation() {
  fireEvent.change(screen.getByLabelText('Lesson-Titel'), { target: { value: 'Discipline' } });
  fireEvent.change(screen.getByLabelText('Lesson-Kategorie'), { target: { value: 'Execution' } });
  fireEvent.change(screen.getByLabelText('Lesson-Inhalt'), {
    target: { value: 'Wait for confirmation.' },
  });
}

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

  it('opens the exact confirmed Lesson only on explicit navigation and preserves its full ID', async () => {
    const lessonId = '12345678-abcd-4123-8123-123456789abc';
    const onCreated = vi.fn();
    client.createFromEvidence.mockResolvedValue({
      lesson_id: lessonId,
      current_version_id: 'version-1',
      version: 1,
      current_state: 'CURRENT',
      title: 'Discipline',
      main_category: 'Execution',
      content: 'Wait for confirmation.',
      evidence: [],
    });
    render(
      <Routes>
        <Route
          path="/"
          element={
            <LessonDraftFromEvidence learningEvidenceId="evidence-1" onCreated={onCreated} />
          }
        />
        <Route path="/lessons/:lessonId" element={<h1>Lesson-Detailansicht</h1>} />
      </Routes>,
    );
    fillInterpretation();
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    const link = await screen.findByRole('link', { name: 'Lesson öffnen' });
    expect(screen.getByRole('status')).toHaveTextContent('LS-12345678');
    expect(screen.getByRole('status')).not.toHaveTextContent(lessonId);
    expect(
      screen.getByText('Technische Lesson-ID anzeigen').closest('details'),
    ).not.toHaveAttribute('open');
    expect(screen.getByText(lessonId).closest('details')).toBeInTheDocument();
    expect(link).toHaveAttribute('href', `/lessons/${lessonId}`);
    expect(onCreated).toHaveBeenCalledExactlyOnceWith(lessonId);
    expect(screen.queryByRole('heading', { name: 'Lesson-Detailansicht' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Lesson anlegen' })).not.toBeInTheDocument();
    fireEvent.click(link);
    expect(
      await screen.findByRole('heading', { name: 'Lesson-Detailansicht' }),
    ).toBeInTheDocument();
    expect(client.createFromEvidence).toHaveBeenCalledTimes(1);
  });

  it('keeps a rejected interpretation editable and offers no open action before success', async () => {
    const onCreated = vi.fn();
    client.createFromEvidence.mockRejectedValueOnce(
      new MarketApiError(409, {
        code: 'SOURCE_VERSION_MISMATCH',
        message: 'Die Evidence muss erneut geprüft werden.',
        details: [],
        timestamp: '2026-10-28T08:00:00Z',
      }),
    );
    render(<LessonDraftFromEvidence learningEvidenceId="evidence-1" onCreated={onCreated} />);
    fillInterpretation();
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Evidence muss erneut geprüft');
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Discipline');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeEnabled();
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
    expect(onCreated).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(await screen.findByRole('link', { name: 'Lesson öffnen' })).toHaveAttribute(
      'href',
      '/lessons/lesson-1',
    );
    expect(client.createFromEvidence).toHaveBeenCalledTimes(2);
    expect(onCreated).toHaveBeenCalledExactlyOnceWith('lesson-1');
  });

  it('does not carry a completed Lesson link into a different clean evidence context', async () => {
    const view = render(<LessonDraftFromEvidence learningEvidenceId="evidence-1" />);
    fillInterpretation();
    fireEvent.click(screen.getByRole('button', { name: 'Lesson anlegen' }));
    expect(await screen.findByRole('link', { name: 'Lesson öffnen' })).toBeInTheDocument();
    view.rerender(<LessonDraftFromEvidence learningEvidenceId="evidence-2" />);
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
    expect(client.createFromEvidence).toHaveBeenCalledTimes(1);
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
    expect(await screen.findByText(/Lesson angelegt:/)).toHaveTextContent('LS-LESSON-2');
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
    expect(await screen.findByText(/Lesson angelegt:/)).toHaveTextContent('LS-LESSON-3');
    expect(screen.getByRole('alert')).toHaveTextContent('Evidence evidence-1');
    expect(screen.getByRole('link', { name: 'Lesson öffnen' })).toHaveAttribute(
      'href',
      '/lessons/lesson-3',
    );
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
    expect(screen.queryByRole('link', { name: 'Lesson öffnen' })).not.toBeInTheDocument();
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
