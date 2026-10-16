import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { LessonReviewPanel } from './LessonReviewPanel';
import {
  lessonReviewClient,
  type ReviewContext,
  type ReviewReceipt,
} from '../services/lessonReviewClient';

vi.mock('../services/lessonReviewClient', async (original) => ({
  ...(await original<typeof import('../services/lessonReviewClient')>()),
  lessonReviewClient: { context: vi.fn(), source: vi.fn(), evidence: vi.fn(), execute: vi.fn() },
}));
vi.mock('./JournalEvidenceOrigin', () => ({
  JournalEvidenceOrigin: ({ evidenceId }: { evidenceId: string }) => (
    <p>Exact journal origin: {evidenceId}</p>
  ),
}));
const at = '2026-10-15T08:00:00Z';
function context(
  state: ReviewContext['lesson']['current_state'] = 'CURRENT',
  id = 'A',
): ReviewContext {
  return {
    lesson: { id, title: `Lesson ${id}`, current_version_id: 'v1', current_state: state },
    history: [
      {
        version: {
          id: 'v1',
          lesson_id: id,
          version: 1,
          main_category: 'Process',
          content: 'Original interpretation',
          created_at: at,
          created_by: 'actor',
          supersedes_version_id: null,
        },
        evidence_links: [
          {
            id: 'link1',
            lesson_version_id: 'v1',
            learning_evidence_id: 'e1',
            relation: 'SUPPORTS',
          },
          {
            id: 'link2',
            lesson_version_id: 'v1',
            learning_evidence_id: 'e2',
            relation: 'CONTRADICTS',
          },
        ],
      },
    ],
    signals: [],
    transitions: [],
    read_at: at,
  };
}
const onChanged = vi.fn();
function mount(id = 'A') {
  return render(
    <MemoryRouter>
      <LessonReviewPanel key={id} lessonId={id} onChanged={onChanged} />
    </MemoryRouter>,
  );
}
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));
const reason = () => screen.getByLabelText(/Begründung der Prüfentscheidung/);
const confirm = () =>
  screen.getByRole('button', { name: 'Prüfentscheidung verbindlich bestätigen' });
const receipt: ReviewReceipt = {
  lesson_id: 'A',
  result_id: 'result',
  result_type: 'LESSON_STATE_TRANSITION',
  replayed: false,
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context());
  vi.mocked(lessonReviewClient.source).mockImplementation((eid) =>
    Promise.resolve({
      evidence_id: eid,
      source_type: 'TRADE_JOURNAL_VERSION',
      source_version_id: `source-${eid}`,
      source_currentness: 'CURRENT',
      review_currentness: 'STALE',
      checked_at: at,
      superseded_by_version_id: null,
    }),
  );
  vi.mocked(lessonReviewClient.evidence).mockResolvedValue([
    {
      evidence_id: 'e3',
      source_type: 'TRADE_JOURNAL_VERSION',
      source: { type: 'TRADE_JOURNAL_VERSION', trade_journal_version_id: 'journal-v2' },
      created_at: at,
    },
  ]);
  vi.mocked(lessonReviewClient.execute).mockResolvedValue(receipt);
});

it('read and prepare never write; confirms exact complete source snapshot with nonblank reason', async () => {
  mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
  click('Quellenbezogene Prüfung beginnen');
  expect(confirm()).toBeDisabled();
  fireEvent.change(reason(), { target: { value: '  ' } });
  expect(confirm()).toBeDisabled();
  fireEvent.change(reason(), { target: { value: 'Quelle wurde korrigiert.' } });
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  fireEvent.click(confirm());
  await screen.findByText(/Prüfentscheidung gespeichert/);
  expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1);
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[0]).toEqual([
    'A',
    {
      operation: 'OPEN_SOURCE_REVIEW',
      expected_current_version_id: 'v1',
      expected_current_state: 'CURRENT',
      expected_open_signal_id: null,
      reviewed_evidence_ids: ['e1', 'e2'],
      reason: 'Quelle wurde korrigiert.',
      confirmed: true,
    },
    expect.any(String),
  ]);
  expect(onChanged).toHaveBeenCalledTimes(1);
  expect(screen.getByText(/Lesson-Status: REVIEW_RECOMMENDED/)).toBeVisible();
});

it('contradiction opening accepts explicit current CONTRADICTS link IDs, never supporting IDs', async () => {
  mount();
  await screen.findByRole('button', { name: 'Widerspruchsprüfung beginnen' });
  click('Widerspruchsprüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Konkreter inhaltlicher Widerspruch.' } });
  expect(confirm()).toBeDisabled();
  const form = screen.getByRole('form', { name: 'Lesson-Prüfentscheidung' });
  expect(within(form).getAllByRole('checkbox')).toHaveLength(1);
  fireEvent.click(within(form).getByRole('checkbox', { name: 'CONTRADICTS · e2' }));
  fireEvent.click(confirm());
  await waitFor(() => expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1));
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[0][1]).toMatchObject({
    operation: 'OPEN_CONTRADICTION_REVIEW',
    contradiction_link_ids: ['link2'],
  });
});

it('successor explicitly chooses relation and source; no automatic replacement or judgement', async () => {
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  mount();
  await screen.findByRole('button', { name: 'Neue Lesson-Version vorbereiten' });
  click('Neue Lesson-Version vorbereiten');
  expect(screen.getByLabelText('Bezug 1')).toHaveValue('SUPPORTS');
  expect(screen.getByLabelText('Bezug 2')).toHaveValue('CONTRADICTS');
  expect(
    screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version'),
  ).toHaveValue('Original interpretation');
  await waitFor(() => expect(screen.getByLabelText('Vorhandene Evidence ergänzen')).toBeEnabled());
  expect(screen.getByRole('option', { name: /journal-v2/ })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Vorhandene Evidence ergänzen'), {
    target: { value: 'e3' },
  });
  click('Ausgewählte Evidence hinzufügen');
  expect(screen.getByLabelText('Bezug 3')).toHaveValue('CONTEXTUAL');
  fireEvent.change(screen.getByLabelText('Bezug 1'), { target: { value: 'CONTEXTUAL' } });
  fireEvent.change(reason(), { target: { value: 'Neue Quelle ausdrücklich geprüft.' } });
  expect(confirm()).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Bezug 3'), { target: { value: 'SUPPORTS' } });
  fireEvent.change(screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version'), {
    target: { value: 'Meine neue Interpretation.' },
  });
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
  fireEvent.click(confirm());
  await waitFor(() => expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1));
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[0][1]).toMatchObject({
    operation: 'NEW_VERSION',
    content: 'Meine neue Interpretation.',
    evidence: [
      { learning_evidence_id: 'e1', relation: 'CONTEXTUAL' },
      { learning_evidence_id: 'e2', relation: 'CONTRADICTS' },
      { learning_evidence_id: 'e3', relation: 'SUPPORTS' },
    ],
  });
});

it('failed write preserves input, blocks synchronous double submit, and manually retries same key', async () => {
  let reject!: (value: Error) => void;
  vi.mocked(lessonReviewClient.execute).mockImplementationOnce(
    () =>
      new Promise((_, r) => {
        reject = r;
      }),
  );
  mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  click('Quellenbezogene Prüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Prüfen.' } });
  fireEvent.click(confirm());
  fireEvent.click(confirm());
  expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1);
  expect(reason()).toBeDisabled();
  await act(async () => {
    reject(new Error('unknown transport result'));
    await Promise.resolve();
  });
  expect(reason()).toHaveValue('Prüfen.');
  expect(confirm()).toBeEnabled();
  expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1);
  const first = vi.mocked(lessonReviewClient.execute).mock.calls[0];
  fireEvent.click(confirm());
  await waitFor(() => expect(lessonReviewClient.execute).toHaveBeenCalledTimes(2));
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[1]).toEqual(first);
});

it('changed input after a failure is a new explicit command, not reuse of an earlier receipt key', async () => {
  vi.mocked(lessonReviewClient.execute).mockRejectedValueOnce(new Error('failed'));
  mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  click('Quellenbezogene Prüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Erste Begründung.' } });
  fireEvent.click(confirm());
  await waitFor(() => expect(confirm()).toBeEnabled());
  const key = vi.mocked(lessonReviewClient.execute).mock.calls[0][2];
  fireEvent.change(reason(), { target: { value: 'Neue Begründung.' } });
  fireEvent.click(confirm());
  await waitFor(() => expect(lessonReviewClient.execute).toHaveBeenCalledTimes(2));
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[1][2]).not.toBe(key);
});

it('readback failure preserves receipt and never recreates the committed operation', async () => {
  mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  click('Quellenbezogene Prüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Prüfen.' } });
  vi.mocked(lessonReviewClient.context).mockRejectedValueOnce(new Error('readback failed'));
  fireEvent.click(confirm());
  await screen.findByText(/Prüfentscheidung gespeichert/);
  await screen.findByText(/Keine neue Bestätigung bis zum erfolgreichen Neuladen/);
  expect(
    screen.queryByRole('button', { name: 'Weitere ausdrückliche Prüfung vorbereiten' }),
  ).not.toBeInTheDocument();
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  click('Lesson-Prüfstand neu laden');
  await screen.findByText(/Lesson-Status: REVIEW_RECOMMENDED/);
  expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1);
});

it('refresh cannot silently rebase a prepared decision or discard the user rationale', async () => {
  mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  click('Quellenbezogene Prüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Begründung bleibt.' } });
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  click('Lesson-Prüfstand neu laden');
  await screen.findByText(/Der Lesson-Stand hat sich geändert/);
  expect(reason()).toHaveValue('Begründung bleibt.');
  expect(confirm()).toBeDisabled();
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
});

it('historical snapshot is read-only and does not borrow current evidence links', async () => {
  const c = context();
  c.lesson.current_version_id = 'v2';
  c.history.unshift({
    version: {
      ...c.history[0].version,
      id: 'v2',
      version: 2,
      content: 'New interpretation',
      supersedes_version_id: 'v1',
    },
    evidence_links: [],
  });
  vi.mocked(lessonReviewClient.context).mockResolvedValue(c);
  mount();
  await screen.findByLabelText('Lesson-Version ansehen');
  fireEvent.change(screen.getByLabelText('Lesson-Version ansehen'), { target: { value: 'v1' } });
  expect(screen.getByText('Original interpretation')).toBeVisible();
  expect(
    screen.queryByRole('button', { name: 'Quellenbezogene Prüfung beginnen' }),
  ).not.toBeInTheDocument();

  const details = screen.getByText('SUPPORTS · Evidence e1').closest('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
  await screen.findByText('Unveränderlicher Link: link1');
  await screen.findByText('Review-Quelle jetzt: STALE');
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
});

it('keyed lesson navigation ignores an old pending command result and calls no new consumer', async () => {
  let resolve!: (value: ReviewReceipt) => void;
  vi.mocked(lessonReviewClient.execute).mockImplementationOnce(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  const view = mount();
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  click('Quellenbezogene Prüfung beginnen');
  fireEvent.change(reason(), { target: { value: 'Nur A.' } });
  fireEvent.click(confirm());
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('CURRENT', 'B'));
  view.rerender(
    <MemoryRouter>
      <LessonReviewPanel key="B" lessonId="B" onChanged={onChanged} />
    </MemoryRouter>,
  );
  await screen.findByRole('button', { name: 'Quellenbezogene Prüfung beginnen' });
  await act(async () => {
    resolve(receipt);
    await Promise.resolve();
  });
  expect(onChanged).not.toHaveBeenCalled();
  expect(screen.queryByText(/Prüfentscheidung gespeichert/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Begründung der Prüfentscheidung/)).not.toBeInTheDocument();
});

it('unchanged and retirement decisions both require an explicit reason and preserve exact signal pin', async () => {
  const c = context('REVIEW_RECOMMENDED');
  c.signals = [
    {
      signal: {
        id: 'signal1',
        lesson_version_id: 'v1',
        status: 'OPEN',
        resolution: null,
        raised_at: at,
        resolved_at: null,
        resulting_lesson_version_id: null,
      },
      trigger_link_ids: ['link2'],
    },
  ];
  vi.mocked(lessonReviewClient.context).mockResolvedValue(c);
  mount();
  await screen.findByRole('button', { name: 'Interpretation unverändert bestätigen' });
  click('Interpretation unverändert bestätigen');
  expect(confirm()).toBeDisabled();
  expect(
    screen.getByText(/Quellversionen, Relation und Quellenwarnungen bleiben unverändert/),
  ).toBeVisible();
  click('Prüfentwurf abbrechen');
  click('Lesson außer Gebrauch nehmen');
  expect(confirm()).toBeDisabled();
  fireEvent.change(reason(), { target: { value: 'Nicht weiter verwenden.' } });
  fireEvent.click(confirm());
  await waitFor(() => expect(lessonReviewClient.execute).toHaveBeenCalledTimes(1));
  expect(vi.mocked(lessonReviewClient.execute).mock.calls[0][1]).toMatchObject({
    operation: 'RETIRE',
    expected_open_signal_id: 'signal1',
  });
});

it('failed or mismatched initial context is not a blank editable lesson', async () => {
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('CURRENT', 'foreign'));
  mount();
  await screen.findByText(/Keine neue Bestätigung bis zum erfolgreichen Neuladen/);
  expect(
    screen.queryByRole('button', { name: 'Quellenbezogene Prüfung beginnen' }),
  ).not.toBeInTheDocument();
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
});
it('failed evidence catalog retains the draft and only reloads the catalog on retry', async () => {
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  vi.mocked(lessonReviewClient.evidence)
    .mockRejectedValueOnce(new Error('catalog unavailable'))
    .mockResolvedValueOnce([]);
  mount();
  await screen.findByRole('button', { name: 'Neue Lesson-Version vorbereiten' });
  click('Neue Lesson-Version vorbereiten');
  fireEvent.change(screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version'), {
    target: { value: 'Mein ungespeicherter Text.' },
  });
  await screen.findByText(/Evidence-Auswahl nicht geladen/);
  click('Evidence-Auswahl erneut laden');
  await waitFor(() => expect(screen.getByLabelText('Vorhandene Evidence ergänzen')).toBeEnabled());
  expect(
    screen.getByLabelText('Ausdrückliche Interpretation der neuen Lesson-Version'),
  ).toHaveValue('Mein ungespeicherter Text.');
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
});

it('relation selects have exact accessible names independent of their option text', async () => {
  vi.mocked(lessonReviewClient.context).mockResolvedValue(context('REVIEW_RECOMMENDED'));
  mount();
  await screen.findByRole('button', { name: 'Neue Lesson-Version vorbereiten' });
  click('Neue Lesson-Version vorbereiten');
  const relation = screen.getByRole('combobox', { name: 'Bezug 1' });
  const label = document.querySelector(`label[for="${relation.id}"]`);
  expect(label?.textContent).toBe('Bezug 1');
  expect(screen.getByLabelText('Bezug 1', { exact: true })).toBe(relation);
  expect(relation).toHaveValue('SUPPORTS');
  expect(screen.getByRole('combobox', { name: 'Bezug 2' })).toHaveValue('CONTRADICTS');
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
});

it('StrictMode cleanup invalidates its pending read without erasing the newer context', async () => {
  let resolve!: (value: ReviewContext) => void;
  vi.mocked(lessonReviewClient.context)
    .mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    )
    .mockResolvedValue(context('REVIEW_RECOMMENDED'));
  render(
    <StrictMode>
      <MemoryRouter>
        <LessonReviewPanel lessonId="A" onChanged={onChanged} />
      </MemoryRouter>
    </StrictMode>,
  );
  await screen.findByText(/Lesson-Status: REVIEW_RECOMMENDED/);
  await act(async () => {
    resolve(context('CURRENT'));
    await Promise.resolve();
  });
  expect(screen.getByText(/Lesson-Status: REVIEW_RECOMMENDED/)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Quellenbezogene Prüfung beginnen' })).toBeNull();
  expect(lessonReviewClient.execute).not.toHaveBeenCalled();
  expect(onChanged).not.toHaveBeenCalled();
});
