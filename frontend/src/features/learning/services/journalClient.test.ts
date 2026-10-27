import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  configureRequestIdentityProvider,
  resetRequestIdentityProvider,
} from '../../../services/identity/requestIdentity';
import {
  journalClient,
  selectJournalEntry,
  snapshotJournalActor,
  type JournalEntry,
  type JournalHistory,
} from './journalClient';
vi.mock('../../../services/environment', () => ({
  environment: { apiBaseUrl: 'https://synthetic.invalid' },
}));
afterEach(() => {
  vi.unstubAllGlobals();
  resetRequestIdentityProvider();
});
it('pins revision, exact source and command key once, retaining a structured conflict', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        code: 'JOURNAL_CONFLICT',
        message: 'Saved draft changed',
        details: [],
        timestamp: '2026-10-14T12:00:00Z',
      }),
      { status: 409 },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  await expect(
    journalClient.command(
      'trade',
      {
        operation: 'FINALIZE',
        version_id: 'j1',
        expected_edit_revision: 4,
        expected_exit_review_version_id: 'r1',
        confirmed: true,
      },
      'key',
    ),
  ).rejects.toMatchObject({ status: 409, response: { code: 'JOURNAL_CONFLICT' } });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe('https://synthetic.invalid/api/v1/learning/trades/trade/journal/commands');
  expect(new Headers(init.headers).get('Idempotency-Key')).toBe('key');
  expect(JSON.parse(init.body as string)).toEqual({
    operation: 'FINALIZE',
    version_id: 'j1',
    expected_edit_revision: 4,
    expected_exit_review_version_id: 'r1',
    confirmed: true,
  });
});
it('reads history and a concrete historical version without writes', async () => {
  const fetchMock = vi
    .fn<(url: string, options: RequestInit) => Promise<Response>>()
    .mockImplementation(() => Promise.resolve(new Response('{}')));
  vi.stubGlobal('fetch', fetchMock);
  const signal = new AbortController().signal;
  await journalClient.history('trade', signal);
  await journalClient.version('old-version', signal);
  expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
    'https://synthetic.invalid/api/v1/learning/trades/trade/journal',
    'https://synthetic.invalid/api/v1/learning/journal-versions/old-version',
  ]);
  for (const [, init] of fetchMock.mock.calls) {
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
    expect(init.signal).toBe(signal);
  }
});

it('does not repeat an uncertain write and retains command, key and actor on an explicit retry', async () => {
  const originalIdentity = { actorId: 'synthetic-actor-1', actorName: 'Synthetic first actor' };
  configureRequestIdentityProvider(() => originalIdentity);
  const actor = snapshotJournalActor();
  const command = {
    operation: 'SAVE_DRAFT' as const,
    version_id: 'draft-1',
    expected_edit_revision: 4,
    what_went_well: 'Unveränderter Versuch',
    would_do_differently: null,
    additional_notes: '',
  };
  const receipt = { result_id: 'draft-1', result_type: 'TRADE_JOURNAL_VERSION', replayed: true };
  const fetchMock = vi
    .fn<(url: string, options: RequestInit) => Promise<Response>>()
    .mockRejectedValueOnce(new TypeError('connection lost'))
    .mockResolvedValueOnce(new Response(JSON.stringify(receipt)));
  vi.stubGlobal('fetch', fetchMock);

  await expect(journalClient.command('trade-1', command, 'fixed-key', actor)).rejects.toThrow();
  expect(fetchMock).toHaveBeenCalledTimes(1);

  originalIdentity.actorId = 'synthetic-actor-2';
  originalIdentity.actorName = 'Synthetic second actor';
  const result = await journalClient.command('trade-1', command, 'fixed-key', actor);
  expect(result).toEqual(receipt);
  expect(result).not.toHaveProperty('edit_revision');
  expect(result).not.toHaveProperty('what_went_well');
  expect(Object.isFrozen(actor)).toBe(true);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  for (const [url, init] of fetchMock.mock.calls) {
    expect(url).toBe('https://synthetic.invalid/api/v1/learning/trades/trade-1/journal/commands');
    expect(JSON.parse(init.body as string)).toEqual(command);
    expect(new Headers(init.headers).get('Idempotency-Key')).toBe('fixed-key');
    expect(new Headers(init.headers).get('X-Actor-ID')).toBe('synthetic-actor-1');
    expect(new Headers(init.headers).get('X-Actor-Name')).toBe('Synthetic first actor');
  }
});

it('keeps an explicitly absent actor snapshot and does not replace it from a later provider', async () => {
  configureRequestIdentityProvider(() => undefined);
  const actor = snapshotJournalActor();
  configureRequestIdentityProvider(() => ({ actorId: 'later-actor' }));
  const receipt = { result_id: 'evidence-1', result_type: 'LEARNING_EVIDENCE', replayed: false };
  const fetchMock = vi
    .fn<(url: string, options: RequestInit) => Promise<Response>>()
    .mockResolvedValue(new Response(JSON.stringify(receipt)));
  vi.stubGlobal('fetch', fetchMock);

  const result = await journalClient.command(
    'trade-1',
    { operation: 'MATERIALIZE', version_id: 'historic-final-1', confirmed: true },
    'materialize-key',
    actor,
  );
  expect(result).toEqual(receipt);
  expect(new Headers(fetchMock.mock.calls[0][1].headers).has('X-Actor-ID')).toBe(false);
  expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
    operation: 'MATERIALIZE',
    version_id: 'historic-final-1',
    confirmed: true,
  });
});

it('allows cancelling a read without issuing another read or write', async () => {
  const controller = new AbortController();
  const aborted = new DOMException('Aborted', 'AbortError');
  const fetchMock = vi
    .fn<(url: string, options: RequestInit) => Promise<Response>>()
    .mockImplementation(
      (_, options) =>
        new Promise((_, reject) => {
          options.signal?.addEventListener('abort', () => reject(aborted), { once: true });
        }),
    );
  vi.stubGlobal('fetch', fetchMock);
  const reading = journalClient.history('trade-1', controller.signal);
  controller.abort();
  await expect(reading).rejects.toBe(aborted);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

function entry(id: string, latest = false): JournalEntry {
  return {
    version: {
      id,
      trade_journal_id: 'journal-1',
      version: latest ? 2 : 1,
      edit_revision: 3,
      status: 'FINALIZED',
      what_went_well: 'Gespeichert',
      would_do_differently: null,
      additional_notes: null,
      source_exit_review_version_id: 'review-1',
      supersedes_version_id: null,
      created_at: '2026-10-14T12:00:00Z',
      created_by: 'actor',
      updated_at: '2026-10-14T12:00:00Z',
      updated_by: 'actor',
      finalized_at: '2026-10-14T12:00:00Z',
      finalized_by: 'actor',
    },
    is_latest: latest,
    source_currentness: 'STALE',
    source_checked_at: '2026-10-26T12:00:00Z',
    learning_evidence_id: null,
  };
}

function history(
  versions: JournalEntry[] = [entry('newest', true), entry('historical')],
): JournalHistory {
  return {
    trade_id: 'trade-1',
    journal_id: 'journal-1',
    handoff: { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'review-2' },
    versions,
  };
}

describe('selectJournalEntry', () => {
  it('selects only the explicit historic identity even when a newer version exists', () => {
    const read = history();
    expect(selectJournalEntry(read, 'trade-1', 'historical')).toBe(read.versions[1]);
    // The existing version endpoint can return just an older entry, marked is_latest=false.
    expect(selectJournalEntry(history([read.versions[1]]), 'trade-1', 'historical')).toBe(
      read.versions[1],
    );
  });

  it('allows latest selection only when there is no explicit identity', () => {
    const read = history([entry('historical'), entry('newest', true)]);
    expect(selectJournalEntry(read, 'trade-1', null)).toBe(read.versions[1]);
    expect(selectJournalEntry(history([]), 'trade-1', null)).toBeNull();
  });

  it.each(['', ' ', 'missing', 'other-trade-version'])(
    'rejects explicit %j instead of falling back to latest',
    (versionId) => {
      expect(() => selectJournalEntry(history(), 'trade-1', versionId)).toThrow();
      expect(() => selectJournalEntry(history([]), 'trade-1', versionId)).toThrow();
    },
  );

  it('rejects a history for another trade even if the version ID matches', () => {
    expect(() => selectJournalEntry(history(), 'trade-2', 'historical')).toThrow(
      /nicht zum angefragten Trade/,
    );
    expect(() => selectJournalEntry(history(), '', null)).toThrow();
  });

  it('rejects entries that do not belong to the returned journal', () => {
    const read = history();
    read.versions[1].version.trade_journal_id = 'foreign-journal';
    expect(() => selectJournalEntry(read, 'trade-1', 'historical')).toThrow(
      /nicht zum gelesenen Journal/,
    );
    expect(() => selectJournalEntry(read, 'trade-1', 'newest')).toThrow();
    expect(() => selectJournalEntry({ ...history(), journal_id: null }, 'trade-1', null)).toThrow();
  });

  it('rejects duplicate identities and an ambiguous latest selection', () => {
    expect(() =>
      selectJournalEntry(history([entry('same', true), entry('same')]), 'trade-1', 'same'),
    ).toThrow(/widersprüchliche Versionsidentitäten/);
    expect(() =>
      selectJournalEntry(history([entry('a', true), entry('b', true)]), 'trade-1', null),
    ).toThrow(/nicht eindeutig/);
    expect(() => selectJournalEntry(history([entry('historical')]), 'trade-1', null)).toThrow(
      /nicht eindeutig/,
    );
  });
});
