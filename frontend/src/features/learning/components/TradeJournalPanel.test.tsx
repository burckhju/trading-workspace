import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { journalClient, type JournalHistory, type JournalVersion } from '../services/journalClient';
import { TradeJournalPanel } from './TradeJournalPanel';

vi.mock('../services/journalClient', () => ({
  journalClient: { history: vi.fn(), command: vi.fn() },
}));
vi.mock('./LessonDraftFromEvidence', () => ({
  LessonDraftFromEvidence: ({ learningEvidenceId }: { learningEvidenceId: string }) => (
    <p>Interpretation ausdrücklich: {learningEvidenceId}</p>
  ),
}));
const at = '2026-10-14T12:00:00Z';
function version(extra: Partial<JournalVersion> = {}): JournalVersion {
  return {
    id: 'j1',
    trade_journal_id: 'journal',
    version: 1,
    edit_revision: 1,
    status: 'DRAFT',
    source_exit_review_version_id: 'r1',
    supersedes_version_id: null,
    what_went_well: null,
    would_do_differently: null,
    additional_notes: null,
    created_at: at,
    updated_at: at,
    created_by: 'actor',
    updated_by: 'actor',
    finalized_at: null,
    finalized_by: null,
    ...extra,
  };
}
function history(v: JournalVersion | null = version()): JournalHistory {
  return {
    trade_id: 'trade',
    journal_id: v ? 'journal' : null,
    handoff: { ready: true, reason: 'READY', exit_review_version_id: 'r1' },
    versions: v
      ? [
          {
            version: v,
            is_latest: true,
            source_currentness: 'CURRENT',
            source_checked_at: at,
            learning_evidence_id: null,
          },
        ]
      : [],
  };
}
const confirm = () =>
  fireEvent.click(screen.getByRole('button', { name: 'Journalaktion bestätigen' }));
function mount(tradeId = 'trade') {
  return render(
    <MemoryRouter>
      <TradeJournalPanel key={tradeId} tradeId={tradeId} />
    </MemoryRouter>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(journalClient.history).mockResolvedValue(history());
  vi.mocked(journalClient.command).mockResolvedValue({
    result_id: 'j1',
    result_type: 'TRADE_JOURNAL_VERSION',
    replayed: false,
  });
});

it('loads an empty journal without creating it, and requires explicit first-draft confirmation', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(history(null));
  mount();
  await screen.findByText('Noch kein Journal gespeichert.');
  expect(journalClient.command).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Journalentwurf anlegen' }));
  expect(journalClient.command).not.toHaveBeenCalled();
  confirm();
  await waitFor(() => expect(journalClient.command).toHaveBeenCalledTimes(1));
  expect(vi.mocked(journalClient.command).mock.calls[0].slice(0, 2)).toEqual([
    'trade',
    {
      operation: 'CREATE_DRAFT',
      expected_latest_version_id: null,
      expected_exit_review_version_id: 'r1',
      confirmed: true,
    },
  ]);
});

it('saves optional text before allowing finalization, then confirms exactly the saved revision', async () => {
  mount();
  const input = await screen.findByLabelText('Was lief gut?');
  fireEvent.change(input, { target: { value: 'Bewusste Reflexion' } });
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  vi.mocked(journalClient.history).mockResolvedValue(
    history(version({ what_went_well: 'Bewusste Reflexion', edit_revision: 2 })),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Journalentwurf speichern' }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeEnabled(),
  );
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toEqual({
    operation: 'SAVE_DRAFT',
    version_id: 'j1',
    expected_edit_revision: 1,
    what_went_well: 'Bewusste Reflexion',
    would_do_differently: '',
    additional_notes: '',
  });
  fireEvent.click(screen.getByRole('button', { name: 'Journal finalisieren' }));
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('dialog')).toHaveTextContent('Bewusste Reflexion');
  confirm();
  await waitFor(() => expect(journalClient.command).toHaveBeenCalledTimes(2));
  expect(vi.mocked(journalClient.command).mock.calls[1][1]).toMatchObject({
    operation: 'FINALIZE',
    expected_edit_revision: 2,
    expected_exit_review_version_id: 'r1',
  });
});

it('keeps text after conflict, retries the same failed request key and never auto-retries', async () => {
  vi.mocked(journalClient.command).mockRejectedValue(new Error('JOURNAL_CONFLICT'));
  mount();
  fireEvent.change(await screen.findByLabelText('Weitere Notizen'), {
    target: { value: 'Nicht verlieren' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Journalentwurf speichern' }));
  await screen.findByRole('alert');
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Weitere Notizen')).toHaveValue('Nicht verlieren');
  fireEvent.click(screen.getByRole('button', { name: 'Journalentwurf speichern' }));
  await waitFor(() => expect(journalClient.command).toHaveBeenCalledTimes(2));
  const calls = vi.mocked(journalClient.command).mock.calls;
  expect(calls[0]).toEqual(calls[1]);
});

it('preserves a dirty draft when a refresh discovers stale source, with no implicit rebind', async () => {
  const view = mount();
  fireEvent.change(await screen.findByLabelText('Was lief gut?'), {
    target: { value: 'Lokaler Text' },
  });
  const stale = history();
  stale.handoff = { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'r1' };
  stale.versions[0].source_currentness = 'STALE';
  vi.mocked(journalClient.history).mockResolvedValue(stale);
  view.rerender(
    <MemoryRouter>
      <TradeJournalPanel key="trade" tradeId="trade" refreshVersion={1} />
    </MemoryRouter>,
  );
  await screen.findByText(/Abschluss noch nicht bereit/);
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Lokaler Text');
  expect(screen.getByRole('button', { name: 'Journalentwurf speichern' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('renders immutable empty finals and materializes only after separate confirmation', async () => {
  const h = history(version({ status: 'FINALIZED', finalized_at: at, finalized_by: 'actor' }));
  vi.mocked(journalClient.history).mockResolvedValue(h);
  mount();
  await screen.findByText(/Inhaltsleerer Abschluss/);
  expect(screen.queryByLabelText('Was lief gut?')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Journalversion als Evidence übergeben' }));
  expect(journalClient.command).not.toHaveBeenCalled();
  vi.mocked(journalClient.command).mockResolvedValue({
    result_id: 'evidence',
    result_type: 'LEARNING_EVIDENCE',
    replayed: false,
  });
  vi.mocked(journalClient.history).mockResolvedValue({
    ...h,
    versions: [{ ...h.versions[0], learning_evidence_id: 'evidence' }],
  });
  confirm();
  await screen.findByText('Interpretation ausdrücklich: evidence');
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toEqual({
    operation: 'MATERIALIZE',
    version_id: 'j1',
    confirmed: true,
  });
});

it('starts an explicit successor referencing the last final without mutating it', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(
    history(version({ status: 'FINALIZED', finalized_at: at, finalized_by: 'actor' })),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Folgeversion vorbereiten' }));
  confirm();
  await waitFor(() => expect(journalClient.command).toHaveBeenCalledTimes(1));
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toEqual({
    operation: 'CREATE_DRAFT',
    expected_latest_version_id: 'j1',
    expected_exit_review_version_id: 'r1',
    confirmed: true,
  });
});

it('distinguishes read failure from an empty journal and supports deliberate reload', async () => {
  vi.mocked(journalClient.history).mockRejectedValue(new Error('unavailable'));
  mount();
  await screen.findByRole('alert');
  expect(screen.queryByText('Noch kein Journal gespeichert.')).not.toBeInTheDocument();
  vi.mocked(journalClient.history).mockResolvedValue(history(null));
  fireEvent.click(screen.getByRole('button', { name: 'Quellenstand neu laden' }));
  await screen.findByText('Noch kein Journal gespeichert.');
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('isolates a pending command from navigation to a different trade', async () => {
  let resolve!: (v: { result_id: string; result_type: string; replayed: boolean }) => void;
  vi.mocked(journalClient.command).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const view = mount();
  fireEvent.change(await screen.findByLabelText('Weitere Notizen'), { target: { value: 'A' } });
  fireEvent.click(screen.getByRole('button', { name: 'Journalentwurf speichern' }));
  vi.mocked(journalClient.history).mockResolvedValue({ ...history(null), trade_id: 'B' });
  view.rerender(
    <MemoryRouter>
      <TradeJournalPanel key="B" tradeId="B" />
    </MemoryRouter>,
  );
  await screen.findByText('Noch kein Journal gespeichert.');
  await act(() => {
    resolve({ result_id: 'j1', result_type: 'TRADE_JOURNAL_VERSION', replayed: false });
    return Promise.resolve();
  });
  expect(screen.queryByDisplayValue('A')).not.toBeInTheDocument();
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});
