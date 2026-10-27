import { StrictMode, useCallback, useRef, useState } from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, Link, RouterProvider, useSearchParams } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { MarketApiError } from '../../market/services/http';
import {
  journalClient,
  type JournalHistory,
  type JournalReceipt,
  type JournalVersion,
} from '../services/journalClient';
import { lessonDraftClient } from '../services/lessonDraftClient';
import { TradeJournalPanel } from './TradeJournalPanel';
import type { JournalNavigationState } from './useTradeJournal';

vi.mock('../services/journalClient', async (original) => ({
  ...(await original<typeof import('../services/journalClient')>()),
  journalClient: { history: vi.fn(), version: vi.fn(), command: vi.fn() },
}));
vi.mock('../services/lessonDraftClient', () => ({
  lessonDraftClient: { createFromEvidence: vi.fn() },
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
function final(extra: Partial<JournalVersion> = {}): JournalVersion {
  return version({ status: 'FINALIZED', finalized_at: at, finalized_by: 'actor', ...extra });
}
function history(versions: JournalVersion[] = [version()], tradeId = 'trade'): JournalHistory {
  return {
    trade_id: tradeId,
    journal_id: versions.length ? 'journal' : null,
    handoff: { ready: true, reason: 'READY', exit_review_version_id: 'r1' },
    versions: versions.map((item, index) => ({
      version: item,
      is_latest: index === 0,
      source_currentness: 'CURRENT',
      source_checked_at: at,
      learning_evidence_id: null,
    })),
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (value: unknown) => void;
  const promise = new Promise<T>((accept, fail) => {
    resolve = accept;
    reject = fail;
  });
  return { promise, resolve, reject };
}
function TestPage({ guard = true }: { guard?: boolean }) {
  const [params] = useSearchParams();
  const [refresh, setRefresh] = useState(0);
  const [discard, setDiscard] = useState(0);
  const [busy, setBusy] = useState(false);
  const state = useRef<JournalNavigationState>({ dirty: false, pending: false });
  const changed = useCallback((next: JournalNavigationState) => {
    state.current = next;
    setBusy(next.pending);
  }, []);
  return (
    <>
      <PendingNavigationGuard
        shouldBlock={() => guard && (state.current.dirty || state.current.pending)}
        busy={busy}
        onDiscard={() => {
          state.current = { dirty: false, pending: false };
          setDiscard((n) => n + 1);
        }}
      />
      <Link to="/else">Andere Seite</Link>
      <button onClick={() => setRefresh((n) => n + 1)}>Parent refresh</button>
      <TradeJournalPanel
        tradeId={params.get('trade_id') ?? ''}
        refreshVersion={refresh}
        discardVersion={discard}
        onNavigationStateChange={changed}
      />
    </>
  );
}
function mount(
  initial = '/post-trade?trade_id=trade',
  options: { strict?: boolean; guard?: boolean } = {},
) {
  const router = createMemoryRouter(
    [
      { path: '/post-trade', element: <TestPage guard={options.guard} /> },
      { path: '/else', element: <h1>Andere Seite geöffnet</h1> },
    ],
    { initialEntries: [initial] },
  );
  const view = render(
    options.strict ? (
      <StrictMode>
        <RouterProvider router={router} />
      </StrictMode>
    ) : (
      <RouterProvider router={router} />
    ),
  );
  return { ...view, router };
}
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));
const confirm = () => click('Journalaktion bestätigen');
async function edit() {
  fireEvent.click(await screen.findByRole('button', { name: 'Journal bearbeiten' }));
  return screen.getByLabelText('Was lief gut?');
}
async function refreshed() {
  click('Quellenstand neu laden');
  await waitFor(() => expect(screen.queryByText(/Journal wird geladen/)).not.toBeInTheDocument());
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

it('reads without writes, then creates the explicitly confirmed first draft and opens its exact URL in edit mode', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(history([]));
  const { router } = mount();
  await screen.findByText('Noch kein Journal gespeichert.');
  expect(journalClient.command).not.toHaveBeenCalled();
  expect(router.state.location.search).toBe('?trade_id=trade');
  click('Journalentwurf anlegen');
  expect(journalClient.command).not.toHaveBeenCalled();
  vi.mocked(journalClient.history).mockResolvedValue(history());
  confirm();
  expect(await screen.findByLabelText('Was lief gut?')).toHaveValue('');
  expect(router.state.location.search).toBe('?trade_id=trade&journal_version_id=j1');
  expect(journalClient.command).toHaveBeenCalledWith(
    'trade',
    {
      operation: 'CREATE_DRAFT',
      expected_latest_version_id: null,
      expected_exit_review_version_id: 'r1',
      confirmed: true,
    },
    expect.any(String),
    expect.objectContaining({ actorId: expect.any(String) }),
  );
});

it('keeps the exact historical source across newer history and a source refresh', async () => {
  const old = final({ what_went_well: 'Historische Reflexion' });
  const newer = final({ id: 'j2', version: 2, what_went_well: 'Neuere Reflexion' });
  vi.mocked(journalClient.history).mockResolvedValue(history([newer, old]));
  const { router } = mount('/post-trade?trade_id=trade&journal_version_id=j1');
  await screen.findByText('Historische Reflexion');
  expect(screen.queryByText('Neuere Reflexion')).not.toBeInTheDocument();
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ id: 'j3', version: 3 }), newer, old]),
  );
  await refreshed();
  expect(screen.getByText('Historische Reflexion')).toBeInTheDocument();
  expect(screen.getByLabelText('Journalversion ansehen')).toHaveValue('j1');
  expect(router.state.location.search).toContain('journal_version_id=j1');
  expect(journalClient.command).not.toHaveBeenCalled();
});

it.each([
  'trade_id=trade&journal_version_id=unknown',
  'trade_id=trade&journal_version_id=foreign-version',
  'trade_id=trade&journal_version_id=',
  'trade_id=trade&journal_version_id=%20',
  'trade_id=trade&journal_version_id=j1&journal_version_id=j2',
  'trade_id=trade&trade_id=foreign&journal_version_id=j1',
])('rejects unresolved URL identity without latest fallback or writes: %s', async (query) => {
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ what_went_well: 'Latest darf nicht erscheinen' })]),
  );
  mount(`/post-trade?${query}`);
  await screen.findByRole('alert');
  expect(screen.queryByText('Latest darf nicht erscheinen')).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'Folgeversion vorbereiten' }),
  ).not.toBeInTheDocument();
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('rejects a foreign history and a wrong journal membership', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(history([final()], 'foreign'));
  mount('/post-trade?trade_id=trade&journal_version_id=j1');
  await screen.findByText(/gehört nicht zum angefragten Trade/);
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ trade_journal_id: 'foreign-journal' })]),
  );
  await refreshed();
  expect(screen.getByRole('alert')).toHaveTextContent('gehört nicht zum gelesenen Journal');
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('maps local selection, same-trade query changes and back/forward to one exact URL, preserving other context', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(
    history([
      final({ id: 'j2', version: 2, what_went_well: 'Text V2' }),
      final({ what_went_well: 'Text V1' }),
    ]),
  );
  const { router } = mount('/post-trade?trade_id=trade&journal_version_id=j1&tab=review');
  await screen.findByText('Text V1');
  fireEvent.change(screen.getByLabelText('Journalversion ansehen'), { target: { value: 'j2' } });
  await screen.findByText('Text V2');
  expect(router.state.location.search).toContain('tab=review');
  expect(router.state.location.search).toContain('journal_version_id=j2');
  await act(() => router.navigate(-1));
  await screen.findByText('Text V1');
  await act(() => router.navigate(1));
  await screen.findByText('Text V2');
  await act(() => router.navigate('/post-trade?trade_id=trade&journal_version_id=j1&tab=source'));
  await screen.findByText('Text V1');
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('pins the implicit initial selection when a newer version appears without normalizing the URL', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ what_went_well: 'V1 bleibt' })]),
  );
  const { router } = mount();
  await screen.findByText('V1 bleibt');
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ id: 'j2', version: 2 }), final({ what_went_well: 'V1 bleibt' })]),
  );
  await refreshed();
  expect(screen.getByLabelText('Journalversion ansehen')).toHaveValue('j1');
  expect(router.state.location.search).toBe('?trade_id=trade');
});

it('shows each text once, prefills every field and finalizes only the exact saved readback', async () => {
  const saved = version({
    what_went_well: 'Gut gespeichert',
    would_do_differently: 'Anders gespeichert',
    additional_notes: 'Notizen gespeichert',
  });
  vi.mocked(journalClient.history).mockResolvedValue(history([saved]));
  mount();
  await screen.findByText('Gut gespeichert');
  expect(screen.getAllByText('Gut gespeichert')).toHaveLength(1);
  await edit();
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Gut gespeichert');
  expect(screen.getByLabelText('Was würde ich anders machen?')).toHaveValue('Anders gespeichert');
  expect(screen.getByLabelText('Weitere Notizen')).toHaveValue('Notizen gespeichert');
  expect(screen.queryByLabelText('Gespeicherte Journaltexte')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Was lief gut?'), {
    target: { value: 'Neu gespeichert' },
  });
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  const next = { ...saved, what_went_well: 'Neu gespeichert', edit_revision: 2 };
  vi.mocked(journalClient.history).mockResolvedValue(history([next]));
  click('Journalentwurf speichern');
  await waitFor(() => expect(screen.queryByRole('textbox')).not.toBeInTheDocument());
  expect(screen.getByText('Neu gespeichert')).toBeInTheDocument();
  click('Journal finalisieren');
  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByText('Neu gespeichert')).toBeInTheDocument();
  expect(screen.getAllByText('Neu gespeichert')).toHaveLength(1);
  expect(screen.getAllByText('Anders gespeichert')).toHaveLength(1);
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(dialog).toHaveTextContent('Bearbeitungsrevision 2');
  expect(dialog).toHaveTextContent('Gespeicherte Reviewquelle: r1');
  vi.mocked(journalClient.history).mockResolvedValue(
    history([final({ ...next, status: 'FINALIZED', edit_revision: 3 })]),
  );
  confirm();
  await screen.findByRole('heading', { name: 'Journal V1 · Finalisiert (unveränderlich)' });
  expect(vi.mocked(journalClient.command).mock.calls[1][1]).toEqual({
    operation: 'FINALIZE',
    version_id: 'j1',
    expected_edit_revision: 2,
    expected_exit_review_version_id: 'r1',
    confirmed: true,
  });
  expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
});

it('allows an explicitly confirmed empty final and keeps it immutable', async () => {
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Journal finalisieren' }));
  expect(screen.getByRole('dialog')).toHaveTextContent('Inhaltsleerer Abschluss');
  vi.mocked(journalClient.history).mockResolvedValue(history([final({ edit_revision: 2 })]));
  confirm();
  await screen.findByRole('heading', { name: 'Journal V1 · Finalisiert (unveränderlich)' });
  expect(screen.queryByRole('button', { name: 'Journal bearbeiten' })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

it('names the latest final as copy source while looking at an older version and consciously opens an existing draft', async () => {
  const old = final({ what_went_well: 'Älterer Ursprung' });
  const latest = final({ id: 'j2', version: 2, what_went_well: 'Letzter Finalstand' });
  vi.mocked(journalClient.history).mockResolvedValue(history([latest, old]));
  mount('/post-trade?trade_id=trade&journal_version_id=j1');
  fireEvent.click(await screen.findByRole('button', { name: 'Folgeversion vorbereiten' }));
  expect(screen.getByRole('dialog')).toHaveTextContent(
    'Kopierursprung: letzte finale Journal V2, ID j2',
  );
  vi.mocked(journalClient.command).mockResolvedValue({
    result_id: 'j3',
    result_type: 'TRADE_JOURNAL_VERSION',
    replayed: false,
  });
  const draft = version({
    id: 'j3',
    version: 3,
    what_went_well: 'Letzter Finalstand',
    supersedes_version_id: 'j2',
  });
  vi.mocked(journalClient.history).mockResolvedValue(history([draft, latest, old]));
  confirm();
  expect(await screen.findByLabelText('Was lief gut?')).toHaveValue('Letzter Finalstand');
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toMatchObject({
    expected_latest_version_id: 'j2',
  });
  fireEvent.change(screen.getByLabelText('Journalversion ansehen'), { target: { value: 'j1' } });
  await screen.findByText('Älterer Ursprung');
  expect(
    screen.queryByRole('button', { name: 'Folgeversion vorbereiten' }),
  ).not.toBeInTheDocument();
  click('Vorhandenen Journalentwurf öffnen');
  await screen.findByRole('heading', { name: 'Journal V3 · Entwurf' });
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});

it('saves a valid draft with STALE and unready review source without rebinding or finalizing', async () => {
  mount();
  fireEvent.change(await edit(), { target: { value: 'Lokale Reflexion' } });
  const stale = history();
  stale.handoff = { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'r1' };
  stale.versions[0].source_currentness = 'STALE';
  vi.mocked(journalClient.history).mockResolvedValue(stale);
  await refreshed();
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Lokale Reflexion');
  expect(screen.getByRole('button', { name: 'Journalentwurf speichern' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  vi.mocked(journalClient.history).mockResolvedValue({
    ...stale,
    versions: [
      {
        ...stale.versions[0],
        version: version({ what_went_well: 'Lokale Reflexion', edit_revision: 2 }),
      },
    ],
  });
  click('Journalentwurf speichern');
  await screen.findByText('Lokale Reflexion');
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toMatchObject({
    operation: 'SAVE_DRAFT',
    expected_edit_revision: 1,
  });
});

it('keeps rebind separate and confirms its exact new source while retaining saved texts', async () => {
  const saved = version({ what_went_well: 'Bewahren' });
  const h = history([saved]);
  h.handoff.exit_review_version_id = 'r2';
  vi.mocked(journalClient.history).mockResolvedValue(h);
  mount();
  await edit();
  fireEvent.change(screen.getByLabelText('Weitere Notizen'), { target: { value: 'lokal' } });
  expect(screen.getByRole('button', { name: 'Neue Review-Quelle übernehmen' })).toBeDisabled();
  click('Bearbeitung abbrechen');
  click('Verwerfen und Lesemodus öffnen');
  click('Neue Review-Quelle übernehmen');
  expect(screen.getByRole('dialog')).toHaveTextContent('Quelle: r2');
  vi.mocked(journalClient.history).mockResolvedValue({
    ...h,
    versions: [
      {
        ...h.versions[0],
        version: { ...saved, edit_revision: 2, source_exit_review_version_id: 'r2' },
      },
    ],
  });
  confirm();
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeEnabled(),
  );
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toEqual({
    operation: 'REBIND_SOURCE',
    version_id: 'j1',
    expected_edit_revision: 1,
    expected_exit_review_version_id: 'r2',
    confirmed: true,
  });
});

it('preserves the original editing base after an external revision/source change and requires an explicit load', async () => {
  mount();
  fireEvent.change(await edit(), { target: { value: 'Lokalen Text behalten' } });
  vi.mocked(journalClient.history).mockResolvedValue(
    history([
      version({
        edit_revision: 4,
        what_went_well: 'Extern geändert',
        source_exit_review_version_id: 'r2',
      }),
    ]),
  );
  await refreshed();
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Lokalen Text behalten');
  expect(screen.getByText(/Lokale Bearbeitungsbasis: Revision 1/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Journalentwurf speichern' })).toBeDisabled();
  click('Gespeicherten Journalstand laden (lokalen Text verwerfen)');
  click('Abbrechen');
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Lokalen Text behalten');
  click('Gespeicherten Journalstand laden (lokalen Text verwerfen)');
  click('Verwerfen und gespeicherten Stand laden');
  await screen.findByText('Extern geändert');
  await edit();
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Extern geändert');
  expect(screen.getByText(/Lokale Bearbeitungsbasis: Revision 4/)).toBeInTheDocument();
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('invalidates an open confirmation without silently replacing the confirmed saved content', async () => {
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ what_went_well: 'Vorher gespeichert' })]),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Journal finalisieren' }));
  vi.mocked(journalClient.history).mockResolvedValue(
    history([
      version({
        what_went_well: 'Extern neu',
        edit_revision: 2,
        source_exit_review_version_id: 'r2',
      }),
    ]),
  );
  await refreshed();
  expect(screen.getByRole('dialog')).toHaveTextContent('Vorher gespeichert');
  expect(screen.getByRole('dialog')).not.toHaveTextContent('Extern neu');
  expect(screen.getByRole('button', { name: 'Journalaktion bestätigen' })).toBeDisabled();
  expect(journalClient.command).not.toHaveBeenCalled();
  click('Abbrechen');
  expect(screen.getByText('Extern neu')).toBeInTheDocument();
});

it('freezes the uncertain command, key and actor for explicit retry even after local edits, then detects an older SAVE replay', async () => {
  vi.mocked(journalClient.command).mockRejectedValueOnce(new Error('transport failed'));
  mount();
  fireEvent.change(await edit(), { target: { value: 'Erster Versuch' } });
  click('Journalentwurf speichern');
  await screen.findByText(/Der Schreibausgang ist unklar/);
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('Was lief gut?'), {
    target: { value: 'Später lokal geändert' },
  });
  expect(screen.getByRole('button', { name: 'Journalentwurf speichern' })).toBeDisabled();
  vi.mocked(journalClient.command).mockResolvedValue({
    result_id: 'j1',
    result_type: 'TRADE_JOURNAL_VERSION',
    replayed: true,
  });
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ edit_revision: 5, what_went_well: 'Inzwischen gespeichert' })]),
  );
  click('Identischen Journalauftrag erneut senden');
  await screen.findByText(/Früherer Journalauftrag bestätigt/);
  const calls = vi.mocked(journalClient.command).mock.calls;
  expect(calls).toHaveLength(2);
  expect(calls[1]).toEqual(calls[0]);
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Später lokal geändert');
  expect(screen.getByText(/Lokale Bearbeitungsbasis: Revision 1/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
});

it('does not clear an uncertain command by merely reading or deliberately loading the saved version', async () => {
  vi.mocked(journalClient.command).mockRejectedValue(new Error('unknown'));
  mount();
  fireEvent.change(await edit(), { target: { value: 'Unklar' } });
  click('Journalentwurf speichern');
  await screen.findByText(/Der Schreibausgang ist unklar/);
  await refreshed();
  click('Gespeicherten Journalstand laden (lokalen Text verwerfen)');
  click('Verwerfen und gespeicherten Stand laden');
  await screen.findByText(/Ausgang des früheren Auftrags bleibt unklar/);
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  expect(
    screen.getByRole('button', { name: 'Identischen Journalauftrag erneut senden' }),
  ).toBeEnabled();
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});

it.each(['JOURNAL_CONFLICT', 'SOURCE_VERSION_MISMATCH', 'JOURNAL_SOURCE_NOT_READY'])(
  'distinguishes %s and gives changed input a new command key after readback',
  async (code) => {
    vi.mocked(journalClient.command).mockRejectedValue(
      new MarketApiError(409, { code, message: code, details: [], timestamp: at }),
    );
    mount();
    fireEvent.change(await edit(), { target: { value: 'Versuch A' } });
    click('Journalentwurf speichern');
    await screen.findByText(new RegExp(`\\(${code}\\)`));
    expect(
      screen.queryByRole('button', { name: 'Identischen Journalauftrag erneut senden' }),
    ).not.toBeInTheDocument();
    await refreshed();
    fireEvent.change(screen.getByLabelText('Was lief gut?'), { target: { value: 'Versuch B' } });
    click('Journalentwurf speichern');
    await waitFor(() => expect(journalClient.command).toHaveBeenCalledTimes(2));
    const calls = vi.mocked(journalClient.command).mock.calls;
    expect(calls[1][2]).not.toBe(calls[0][2]);
  },
);

it('keeps a confirmed write distinct from failed readback and retries only the read', async () => {
  mount();
  fireEvent.change(await edit(), { target: { value: 'Gesendeter Text' } });
  vi.mocked(journalClient.history).mockRejectedValue(new Error('read offline'));
  click('Journalentwurf speichern');
  await screen.findByText(/Schreibauftrag ist bestätigt/);
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Gesendeter Text');
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toBeDisabled();
  expect(
    screen.queryByRole('button', { name: 'Identischen Journalauftrag erneut senden' }),
  ).not.toBeInTheDocument();
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ what_went_well: 'Gesendeter Text', edit_revision: 2 })]),
  );
  click('Nur Lesestand erneut laden');
  await screen.findByText('Gesendeter Text');
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});

it('does not replace a missing command result with the newest version', async () => {
  mount();
  fireEvent.change(await edit(), { target: { value: 'Nicht verlieren' } });
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ id: 'j2', version: 2, what_went_well: 'Falscher Ersatz' })]),
  );
  click('Journalentwurf speichern');
  await screen.findByText(/Schreibauftrag ist bestätigt/);
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Nicht verlieren');
  expect(screen.queryByText('Falscher Ersatz')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Journalentwurf speichern' })).toBeDisabled();
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});

it('materializes an exact historical STALE final and treats the receipt as Evidence, not JournalVersion', async () => {
  const h = history([final({ id: 'j2', version: 2 }), final({ what_went_well: 'Historisch' })]);
  h.handoff = { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'r2' };
  h.versions[1].source_currentness = 'STALE';
  vi.mocked(journalClient.history).mockResolvedValue(h);
  const { router } = mount('/post-trade?trade_id=trade&journal_version_id=j1');
  fireEvent.click(
    await screen.findByRole('button', { name: 'Journalversion als Evidence übergeben' }),
  );
  vi.mocked(journalClient.command).mockResolvedValue({
    result_id: 'ev1',
    result_type: 'LEARNING_EVIDENCE',
    replayed: false,
  });
  vi.mocked(journalClient.history).mockResolvedValue({
    ...h,
    versions: [h.versions[0], { ...h.versions[1], learning_evidence_id: 'ev1' }],
  });
  confirm();
  await screen.findByText(/LearningEvidence: ev1/);
  expect(screen.getByLabelText('Journalversion ansehen')).toHaveValue('j1');
  expect(router.state.location.search).toContain('journal_version_id=j1');
  expect(vi.mocked(journalClient.command).mock.calls[0][1]).toEqual({
    operation: 'MATERIALIZE',
    version_id: 'j1',
    confirmed: true,
  });
  expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
});

it('blocks local selection, route/trade/query and native unload while dirty; stay preserves inputs and discard writes nothing', async () => {
  const h = history([version({ id: 'j2', version: 2 }), final()]);
  vi.mocked(journalClient.history).mockResolvedValue(h);
  const { router } = mount('/post-trade?trade_id=trade&journal_version_id=j2');
  fireEvent.change(await edit(), { target: { value: 'Hier behalten' } });
  const unload = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  fireEvent.change(screen.getByLabelText('Journalversion ansehen'), { target: { value: 'j1' } });
  expect(await screen.findByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
  expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
  click('Hier bleiben');
  expect(router.state.location.search).toContain('journal_version_id=j2');
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Hier behalten');
  await act(() => router.navigate('/post-trade?trade_id=B&journal_version_id=j2'));
  await screen.findByRole('alertdialog');
  click('Hier bleiben');
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Hier behalten');
  await act(() => router.navigate('/post-trade?trade_id=trade&journal_version_id=j1'));
  await screen.findByRole('alertdialog');
  click('Eingaben verwerfen und wechseln');
  await screen.findByRole('heading', { name: 'Journal V1 · Finalisiert (unveränderlich)' });
  expect(journalClient.command).not.toHaveBeenCalled();
});

it('takes the synchronous submit lock before React renders and never releases a running write for navigation', async () => {
  const result = deferred<JournalReceipt>();
  vi.mocked(journalClient.command).mockReturnValue(result.promise);
  const { router } = mount(undefined, { strict: true });
  fireEvent.change(await edit(), { target: { value: 'Ein Auftrag' } });
  const save = screen.getByRole('button', { name: 'Journalentwurf speichern' });
  act(() => {
    save.click();
    save.click();
  });
  expect(journalClient.command).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Bearbeitung abbrechen' })).toBeDisabled();
  await act(() => router.navigate('/else'));
  expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
  expect(
    screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
  ).not.toBeInTheDocument();
  click('Hier bleiben');
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ edit_revision: 2, what_went_well: 'Ein Auftrag' })]),
  );
  await act(async () => {
    result.resolve({ result_id: 'j1', result_type: 'TRADE_JOURNAL_VERSION', replayed: false });
    await result.promise;
  });
  await screen.findByText('Ein Auftrag');
});

it('ignores a late A receipt after forced query A to B to A, and ignores superseded reads', async () => {
  const result = deferred<JournalReceipt>();
  vi.mocked(journalClient.command).mockReturnValue(result.promise);
  vi.mocked(journalClient.history).mockResolvedValue(
    history([version({ id: 'j2', version: 2 }), version()]),
  );
  const { router } = mount('/post-trade?trade_id=trade&journal_version_id=j1', { guard: false });
  fireEvent.change(await edit(), { target: { value: 'Altes A' } });
  click('Journalentwurf speichern');
  await act(() => router.navigate('/post-trade?trade_id=trade&journal_version_id=j2'));
  await screen.findByRole('heading', { name: 'Journal V2 · Entwurf' });
  await act(() => router.navigate('/post-trade?trade_id=trade&journal_version_id=j1'));
  fireEvent.change(await edit(), { target: { value: 'Neues A' } });
  const readsBefore = vi.mocked(journalClient.history).mock.calls.length;
  await act(async () => {
    result.resolve({ result_id: 'j1', result_type: 'TRADE_JOURNAL_VERSION', replayed: false });
    await result.promise;
  });
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Neues A');
  expect(journalClient.history).toHaveBeenCalledTimes(readsBefore);
  const late = deferred<JournalHistory>();
  vi.mocked(journalClient.history)
    .mockReturnValueOnce(late.promise)
    .mockResolvedValue(history([version({ id: 'j2', version: 2 }), version()]));
  click('Quellenstand neu laden');
  await act(() => router.navigate('/post-trade?trade_id=trade&journal_version_id=j2'));
  await screen.findByRole('heading', { name: 'Journal V2 · Entwurf' });
  await act(async () => {
    late.resolve(history([version({ what_went_well: 'Verspätetes A' })]));
    await late.promise;
  });
  expect(screen.queryByText('Verspätetes A')).not.toBeInTheDocument();
});

it('ignores a receipt after unmount even when the same trade is mounted again', async () => {
  const result = deferred<JournalReceipt>();
  vi.mocked(journalClient.command).mockReturnValue(result.promise);
  const first = mount();
  fireEvent.change(await edit(), { target: { value: 'Alter Auftrag' } });
  click('Journalentwurf speichern');
  first.unmount();
  mount();
  fireEvent.change(await edit(), { target: { value: 'Neue Sitzung' } });
  const readsBefore = vi.mocked(journalClient.history).mock.calls.length;
  await act(async () => {
    result.resolve({ result_id: 'j1', result_type: 'TRADE_JOURNAL_VERSION', replayed: false });
    await result.promise;
  });
  expect(screen.getByLabelText('Was lief gut?')).toHaveValue('Neue Sitzung');
  expect(journalClient.history).toHaveBeenCalledTimes(readsBefore);
  expect(journalClient.command).toHaveBeenCalledTimes(1);
});

it('keeps a real embedded Lesson mounted through a failed/successful source refresh and blocks its route change', async () => {
  const h = history([final()]);
  h.versions[0].learning_evidence_id = 'evidence';
  vi.mocked(journalClient.history).mockResolvedValue(h);
  const { router } = mount();
  fireEvent.change(await screen.findByLabelText('Lesson-Titel'), {
    target: { value: 'Eigene Interpretation' },
  });
  vi.mocked(journalClient.history).mockRejectedValueOnce(new Error('read failure'));
  await refreshed();
  expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Eigene Interpretation');
  expect(screen.getByLabelText('Lesson-Titel')).toBeDisabled();
  await refreshed();
  expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Eigene Interpretation');
  await act(() => router.navigate('/else'));
  await screen.findByRole('alertdialog');
  click('Hier bleiben');
  expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Eigene Interpretation');
  expect(lessonDraftClient.createFromEvidence).not.toHaveBeenCalled();
});

it('does not silently rebind an open Lesson when the readback Evidence changes', async () => {
  const h = history([final()]);
  h.versions[0].learning_evidence_id = 'old-evidence';
  vi.mocked(journalClient.history).mockResolvedValue(h);
  mount();
  fireEvent.change(await screen.findByLabelText('Lesson-Titel'), {
    target: { value: 'Alte Quelle' },
  });
  vi.mocked(journalClient.history).mockResolvedValue({
    ...h,
    versions: [{ ...h.versions[0], learning_evidence_id: 'new-evidence' }],
  });
  await refreshed();
  expect(screen.getByLabelText('Lesson-Titel')).toHaveValue('Alte Quelle');
  expect(screen.getByText(/LearningEvidence: old-evidence/)).toBeInTheDocument();
  expect(screen.getByText(/bleiben an Evidence old-evidence/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Lesson anlegen' })).toBeDisabled();
  click('Eingaben verwerfen und neue Evidence öffnen');
  await waitFor(() => expect(screen.getByLabelText('Lesson-Titel')).toHaveValue(''));
  expect(screen.getByText(/LearningEvidence: new-evidence/)).toBeInTheDocument();
});

it('focuses cancel, traps keyboard focus and restores an action after Escape without writing', async () => {
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Journal finalisieren' }));
  const cancel = screen.getByRole('button', { name: 'Abbrechen' });
  expect(cancel).toHaveFocus();
  fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true });
  expect(screen.getByRole('button', { name: 'Journalaktion bestätigen' })).toHaveFocus();
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Journal finalisieren' })).toHaveFocus();
  expect(journalClient.command).not.toHaveBeenCalled();
});
