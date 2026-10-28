import { describe, expect, it } from 'vitest';

import type {
  JournalCommand,
  JournalEntry,
  JournalHistory,
  JournalVersion,
} from '../services/journalClient';
import {
  confirmationIsCurrent,
  journalQuery,
  journalTexts,
  sameJournalTexts,
  sameJournalVersion,
  type JournalConfirmation,
} from './journalViewState';

function entry(overrides: Partial<JournalVersion> = {}): JournalEntry {
  return {
    version: {
      id: 'journal-version-1',
      trade_journal_id: 'journal-1',
      version: 1,
      edit_revision: 3,
      status: 'DRAFT',
      source_exit_review_version_id: 'review-1',
      supersedes_version_id: null,
      what_went_well: '  Vollständiger gespeicherter Text\nmit zweiter Zeile  ',
      would_do_differently: null,
      additional_notes: 'Eigene Notiz',
      created_at: '2026-10-14T12:00:00Z',
      created_by: 'actor',
      updated_at: '2026-10-14T12:10:00Z',
      updated_by: 'actor',
      finalized_at: null,
      finalized_by: null,
      ...overrides,
    },
    is_latest: true,
    source_currentness: 'CURRENT',
    source_checked_at: '2026-10-26T12:00:00Z',
    learning_evidence_id: null,
  };
}

function history(selected: JournalEntry): JournalHistory {
  return {
    trade_id: 'trade-1',
    journal_id: 'journal-1',
    handoff: { ready: true, reason: 'READY', exit_review_version_id: 'review-1' },
    versions: [selected],
  };
}

function confirmation(command: JournalCommand, selected: JournalEntry): JournalConfirmation {
  return {
    command,
    saved: selected.version,
    copySource: selected.version,
    sourceCurrentness: selected.source_currentness,
    handoff: history(selected).handoff,
  };
}

function finalize(selected: JournalEntry): JournalConfirmation {
  return confirmation(
    {
      operation: 'FINALIZE',
      version_id: selected.version.id,
      expected_edit_revision: selected.version.edit_revision,
      expected_exit_review_version_id: 'review-1',
      confirmed: true,
    },
    selected,
  );
}

describe('journalQuery', () => {
  it('uses the exact current query and distinguishes an explicit version from an implicit entry', () => {
    expect(journalQuery('?trade_id=trade-1&journal_version_id=v1', 'trade-1')).toMatchObject({
      versionId: 'v1',
      error: null,
    });
    expect(journalQuery('?trade_id=trade-1&other_context=keep', 'trade-1')).toMatchObject({
      versionId: null,
      error: null,
    });
    expect(journalQuery('?trade_id=trade-1&journal_version_id=v2', 'trade-1').key).not.toBe(
      journalQuery('?trade_id=trade-1&journal_version_id=v1', 'trade-1').key,
    );
  });

  it.each([
    '?trade_id=trade-1&journal_version_id=',
    '?trade_id=trade-1&journal_version_id=%20%20',
    '?trade_id=trade-1&journal_version_id=v1&journal_version_id=v2',
    '?trade_id=trade-1&journal_version_id=v1&journal_version_id=v1',
    '?trade_id=trade-1&trade_id=trade-2&journal_version_id=v1',
    '?trade_id=trade-2&journal_version_id=v1',
    '?journal_version_id=v1',
  ])('rejects an empty or ambiguous context %s before any command', (search) => {
    expect(journalQuery(search, 'trade-1').error).toBeTruthy();
  });

  it('rejects a missing trade even without a version and does not trim an explicit identity', () => {
    expect(journalQuery('?trade_id=', '').error).toBeTruthy();
    expect(journalQuery('?trade_id=trade-1&journal_version_id=%20v1%20', 'trade-1')).toMatchObject({
      versionId: ' v1 ',
      error: null,
    });
  });
});

describe('saved and local journal text', () => {
  it('prefills all optional fields without trimming or manufacturing content', () => {
    const saved = entry().version;
    const local = journalTexts(saved);
    expect(local).toEqual({
      what_went_well: '  Vollständiger gespeicherter Text\nmit zweiter Zeile  ',
      would_do_differently: '',
      additional_notes: 'Eigene Notiz',
    });
    expect(sameJournalTexts(saved, local)).toBe(true);
    expect(sameJournalTexts(saved, { ...local, additional_notes: '' })).toBe(false);
    expect(
      sameJournalTexts(saved, { ...local, what_went_well: saved.what_went_well?.trim() ?? '' }),
    ).toBe(false);
  });

  it('keeps saved identity, revision and source separate from equal local text', () => {
    const saved = entry().version;
    expect(sameJournalVersion(saved, { ...saved })).toBe(true);
    expect(sameJournalVersion(saved, { ...saved, edit_revision: 4 })).toBe(false);
    expect(sameJournalVersion(saved, { ...saved, source_exit_review_version_id: 'review-2' })).toBe(
      false,
    );
    const advanced = { ...saved, edit_revision: 4 };
    expect(sameJournalTexts(saved, advanced)).toBe(true);
  });
});

describe('frozen journal confirmation', () => {
  it('allows a fresh source inspection timestamp without silently changing the saved confirmation', () => {
    const original = entry();
    const selected = { ...original, source_checked_at: '2026-10-26T12:30:00Z' };
    expect(confirmationIsCurrent(finalize(original), history(selected), selected)).toBe(true);
  });

  it.each<Partial<JournalVersion>>([
    { id: 'another-version' },
    { edit_revision: 4 },
    { source_exit_review_version_id: 'review-2' },
    { status: 'FINALIZED' },
    { what_went_well: 'Extern geänderter Text' },
  ])('invalidates a confirmation when its saved version changes: %j', (changed) => {
    const original = entry();
    const selected = entry(changed);
    expect(confirmationIsCurrent(finalize(original), history(selected), selected)).toBe(false);
  });

  it('requires the command to name the displayed saved version and revision exactly', () => {
    const selected = entry();
    const correct = finalize(selected);
    expect(confirmationIsCurrent({ ...correct, saved: null }, history(selected), selected)).toBe(
      false,
    );
    expect(confirmationIsCurrent(correct, history(selected), null)).toBe(false);
    expect(
      confirmationIsCurrent(
        {
          ...correct,
          command: {
            operation: 'FINALIZE',
            version_id: 'another-version',
            expected_edit_revision: 3,
            expected_exit_review_version_id: 'review-1',
            confirmed: true,
          },
        },
        history(selected),
        selected,
      ),
    ).toBe(false);
    expect(
      confirmationIsCurrent(
        {
          ...correct,
          command: {
            operation: 'FINALIZE',
            version_id: selected.version.id,
            expected_edit_revision: 2,
            expected_exit_review_version_id: 'review-1',
            confirmed: true,
          },
        },
        history(selected),
        selected,
      ),
    ).toBe(false);
  });

  it('requires the same ready review binding for finalization and rebind', () => {
    const selected = entry();
    const current = history(selected);
    expect(
      confirmationIsCurrent(
        finalize(selected),
        {
          ...current,
          handoff: { ...current.handoff, ready: false },
        },
        selected,
      ),
    ).toBe(false);
    expect(
      confirmationIsCurrent(
        finalize(selected),
        {
          ...current,
          handoff: { ...current.handoff, exit_review_version_id: 'review-2' },
        },
        selected,
      ),
    ).toBe(false);
    const stale = { ...selected, source_currentness: 'STALE' as const };
    expect(confirmationIsCurrent(finalize(selected), history(stale), stale)).toBe(false);
    expect(confirmationIsCurrent(finalize(stale), history(stale), stale)).toBe(false);

    const rebind = confirmation(
      {
        operation: 'REBIND_SOURCE',
        version_id: stale.version.id,
        expected_edit_revision: stale.version.edit_revision,
        expected_exit_review_version_id: 'review-2',
        confirmed: true,
      },
      stale,
    );
    expect(
      confirmationIsCurrent(
        rebind,
        {
          ...history(stale),
          handoff: { ready: true, reason: 'READY', exit_review_version_id: 'review-2' },
        },
        stale,
      ),
    ).toBe(true);
    expect(confirmationIsCurrent(rebind, history(stale), stale)).toBe(false);
  });

  it('allows explicit historical STALE materialization independently of the current review gate', () => {
    const selected = {
      ...entry({ status: 'FINALIZED' }),
      is_latest: false,
      source_currentness: 'STALE' as const,
    };
    const current = {
      ...history(selected),
      handoff: { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'new-review' },
    };
    const confirm = confirmation(
      {
        operation: 'MATERIALIZE',
        version_id: selected.version.id,
        confirmed: true,
      },
      selected,
    );
    expect(confirmationIsCurrent(confirm, current, selected)).toBe(true);
    expect(
      confirmationIsCurrent(confirm, current, {
        ...selected,
        source_currentness: 'UNKNOWN',
      }),
    ).toBe(false);
  });

  it('pins the latest final copy origin while an older version is being viewed', () => {
    const historical = entry({ id: 'old-final', status: 'FINALIZED' });
    historical.is_latest = false;
    const latest = entry({ id: 'latest-final', version: 2, status: 'FINALIZED' });
    const current = { ...history(latest), versions: [latest, historical] };
    const confirm = {
      ...confirmation(
        {
          operation: 'CREATE_DRAFT',
          expected_latest_version_id: latest.version.id,
          expected_exit_review_version_id: 'review-1',
          confirmed: true,
        },
        historical,
      ),
      copySource: latest.version,
    };
    expect(confirmationIsCurrent(confirm, current, historical)).toBe(true);
    expect(
      confirmationIsCurrent(
        confirm,
        {
          ...current,
          versions: [entry({ id: 'newer-final', status: 'FINALIZED' }), historical],
        },
        historical,
      ),
    ).toBe(false);
    expect(
      confirmationIsCurrent(
        confirm,
        {
          ...current,
          versions: [{ ...latest, version: { ...latest.version, edit_revision: 4 } }, historical],
        },
        historical,
      ),
    ).toBe(false);
    expect(
      confirmationIsCurrent(
        confirm,
        {
          ...current,
          versions: [{ ...latest, version: { ...latest.version, status: 'DRAFT' } }, historical],
        },
        historical,
      ),
    ).toBe(false);
  });

  it('allows a first draft confirmation only while the journal is still empty', () => {
    const current: JournalHistory = {
      ...history(entry()),
      journal_id: null,
      versions: [],
    };
    const confirm: JournalConfirmation = {
      command: {
        operation: 'CREATE_DRAFT',
        expected_latest_version_id: null,
        expected_exit_review_version_id: 'review-1',
        confirmed: true,
      },
      saved: null,
      copySource: null,
      sourceCurrentness: null,
      handoff: current.handoff,
    };
    expect(confirmationIsCurrent(confirm, current, null)).toBe(true);
    expect(confirmationIsCurrent(confirm, history(entry()), null)).toBe(false);
  });
});
