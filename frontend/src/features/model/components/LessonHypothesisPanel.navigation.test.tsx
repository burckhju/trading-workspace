import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LessonHypothesisPanel } from './LessonHypothesisPanel';
import type { LessonHypothesisNavigationState } from './LessonHypothesisPanel';
import type { LessonHypothesis } from '../types/lessonHypothesis';

const mocks = vi.hoisted(() => ({
  listForLessonVersion: vi.fn(),
  createFromLessonVersion: vi.fn(),
  nestedCommand: vi.fn(),
}));

vi.mock('../services/lessonHypothesisClient', () => ({ lessonHypothesisClient: mocks }));
vi.mock('./HypothesisProposalPanel', () => ({
  HypothesisProposalPanel: () => (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        mocks.nestedCommand();
      }}
    >
      <label>
        Proposal draft
        <input defaultValue="" />
      </label>
      <button type="submit">Nested proposal command</button>
      <button
        type="button"
        onClick={() => {
          mocks.nestedCommand();
        }}
      >
        Nested approval command
      </button>
    </form>
  ),
}));

function hypothesis(source = 'lesson-version-1'): LessonHypothesis {
  return {
    id: 'hypothesis-1',
    title: 'Explicit hypothesis',
    statement: 'Synthetic interpretation.',
    status: 'OPEN',
    source_lesson_version_id: source,
    created_at: '2026-10-26T12:00:00Z',
    created_by: 'actor-1',
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function fillHypothesis() {
  const title = await screen.findByLabelText('Titel');
  const statement = screen.getByLabelText('Hypothese');
  fireEvent.change(title, { target: { value: 'Explicit hypothesis' } });
  fireEvent.change(statement, { target: { value: 'Synthetic interpretation.' } });
  return { title, statement };
}

describe('Lesson hypothesis navigation ownership', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.listForLessonVersion.mockResolvedValue([]);
    mocks.createFromLessonVersion.mockResolvedValue(hypothesis());
  });

  it('reports dirty input and pending writes synchronously and clears them only after confirmation', async () => {
    let navigation: LessonHypothesisNavigationState = { dirty: false, busy: false };
    const pending = deferred<LessonHypothesis>();
    mocks.createFromLessonVersion.mockImplementation(() => {
      expect(navigation).toEqual({ dirty: true, busy: true });
      return pending.promise;
    });
    render(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        onNavigationStateChange={(state) => {
          navigation = state;
        }}
      />,
    );
    const { title } = await fillHypothesis();
    expect(navigation).toEqual({ dirty: true, busy: false });
    const form = title.closest('form');
    expect(form).not.toBeNull();
    act(() => {
      fireEvent.submit(form!);
      fireEvent.submit(form!);
      expect(navigation).toEqual({ dirty: true, busy: true });
    });
    expect(mocks.createFromLessonVersion).toHaveBeenCalledTimes(1);
    expect(title).toBeDisabled();

    await act(async () => {
      pending.resolve(hypothesis());
      await pending.promise;
    });
    expect(screen.getByText('Bereits an FT-013 übergeben')).toBeInTheDocument();
    expect(navigation).toEqual({ dirty: false, busy: false });
  });

  it('preserves the exact historical form through a context refresh and creates only its explicit source', async () => {
    const source = 'lesson-version-history';
    mocks.createFromLessonVersion.mockResolvedValue(hypothesis(source));
    const onNavigationStateChange = vi.fn();
    const view = render(
      <LessonHypothesisPanel
        lessonVersionId={source}
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    const { title, statement } = await fillHypothesis();
    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId={source}
        actionsDisabled
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    expect(screen.getByLabelText('Titel')).toBe(title);
    expect(screen.getByLabelText('Hypothese')).toBe(statement);
    expect(title).toHaveValue('Explicit hypothesis');
    expect(statement).toHaveValue('Synthetic interpretation.');
    expect(title).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' })).toBeDisabled();
    fireEvent.submit(title.closest('form')!);
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: true, busy: false });

    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId={source}
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    expect(screen.getByLabelText('Titel')).toBe(title);
    fireEvent.click(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' }));
    await screen.findByText('Bereits an FT-013 übergeben');
    expect(mocks.createFromLessonVersion).toHaveBeenCalledExactlyOnceWith(source, {
      title: 'Explicit hypothesis',
      statement: 'Synthetic interpretation.',
    });
    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId={source}
        actionsDisabled
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    expect(screen.getByText('Bereits an FT-013 übergeben')).toBeInTheDocument();
    expect(screen.getByText(`Gebundene Quellversion ${source}`)).toBeInTheDocument();
    expect(mocks.listForLessonVersion).toHaveBeenCalledTimes(1);
    expect(mocks.createFromLessonVersion).toHaveBeenCalledTimes(1);
  });

  it('checks a newly invalidated owner before its next render', async () => {
    let disabled = false;
    render(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        isActionsDisabled={() => disabled}
      />,
    );
    const { title, statement } = await fillHypothesis();
    disabled = true;
    fireEvent.submit(title.closest('form')!);
    fireEvent.change(statement, { target: { value: 'Must not replace the retained draft.' } });
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
    expect(statement).toHaveValue('Synthetic interpretation.');
    disabled = false;
    fireEvent.submit(title.closest('form')!);
    await screen.findByText('Bereits an FT-013 übergeben');
    expect(mocks.createFromLessonVersion).toHaveBeenCalledExactlyOnceWith('lesson-version-1', {
      title: 'Explicit hypothesis',
      statement: 'Synthetic interpretation.',
    });
  });

  it('retains dirty input after an unsuccessful command and permits clearing all input', async () => {
    const onNavigationStateChange = vi.fn();
    mocks.createFromLessonVersion.mockRejectedValue(new Error('Synthetic write failure'));
    render(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    await fillHypothesis();
    fireEvent.click(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' }));
    await screen.findByRole('alert');
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: true, busy: false });
    expect(screen.getByLabelText('Titel')).toHaveValue('Explicit hypothesis');
    expect(screen.getByLabelText('Hypothese')).toHaveValue('Synthetic interpretation.');
    fireEvent.click(screen.getByRole('button', { name: 'Hypothesenstand neu laden' }));
    await waitFor(() => expect(screen.getByLabelText('Titel')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Titel'), { target: { value: '' } });
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: true, busy: false });
    fireEvent.change(screen.getByLabelText('Hypothese'), { target: { value: '' } });
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: false, busy: false });
    expect(mocks.createFromLessonVersion).toHaveBeenCalledTimes(1);
  });

  it('keeps nested draft controls mounted while blocking their commands for an unresolved source', async () => {
    mocks.listForLessonVersion.mockResolvedValue([hypothesis()]);
    let disabled = false;
    const isActionsDisabled = () => disabled;
    const view = render(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        isActionsDisabled={isActionsDisabled}
      />,
    );
    const input = await screen.findByLabelText('Proposal draft');
    fireEvent.change(input, { target: { value: 'Retained proposal input' } });
    disabled = true;
    fireEvent.submit(input.closest('form')!);
    fireEvent.click(screen.getByRole('button', { name: 'Nested approval command' }));
    expect(mocks.nestedCommand).not.toHaveBeenCalled();

    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        actionsDisabled
        isActionsDisabled={isActionsDisabled}
      />,
    );
    expect(screen.getByLabelText('Proposal draft')).toBe(input);
    expect(input).toHaveValue('Retained proposal input');
    expect(input).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Nested proposal command' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Nested approval command' })).toBeDisabled();
    disabled = false;
    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        isActionsDisabled={isActionsDisabled}
      />,
    );
    expect(screen.getByLabelText('Proposal draft')).toBe(input);
    fireEvent.click(screen.getByRole('button', { name: 'Nested approval command' }));
    expect(mocks.nestedCommand).toHaveBeenCalledTimes(1);
  });

  it('isolates A to B to A drafts and ignores an old confirmed response after unmount', async () => {
    const pending = deferred<LessonHypothesis>();
    mocks.createFromLessonVersion.mockReturnValue(pending.promise);
    const onNavigationStateChange = vi.fn();
    const view = render(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    await fillHypothesis();
    fireEvent.click(screen.getByRole('button', { name: 'Hypothese für FT-013 anlegen' }));
    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-2"
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
    view.rerender(
      <LessonHypothesisPanel
        lessonVersionId="lesson-version-1"
        onNavigationStateChange={onNavigationStateChange}
      />,
    );
    expect(await screen.findByLabelText('Titel')).toHaveValue('');
    await act(async () => {
      pending.resolve(hypothesis());
      await pending.promise;
    });
    expect(screen.getByLabelText('Titel')).toHaveValue('');
    expect(screen.queryByText('Bereits an FT-013 übergeben')).not.toBeInTheDocument();
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: false, busy: false });
    expect(mocks.createFromLessonVersion).toHaveBeenCalledTimes(1);
  });

  it('reports the live StrictMode visit and cleans up its guard state', async () => {
    const onNavigationStateChange = vi.fn();
    const view = render(
      <StrictMode>
        <LessonHypothesisPanel
          lessonVersionId="lesson-version-1"
          onNavigationStateChange={onNavigationStateChange}
        />
      </StrictMode>,
    );
    await fillHypothesis();
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: true, busy: false });
    view.unmount();
    expect(onNavigationStateChange).toHaveBeenLastCalledWith({ dirty: false, busy: false });
    expect(mocks.createFromLessonVersion).not.toHaveBeenCalled();
  });
});
