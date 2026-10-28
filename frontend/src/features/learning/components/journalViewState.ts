import type {
  JournalCommand,
  JournalEntry,
  JournalHistory,
  JournalTexts,
  JournalVersion,
} from '../services/journalClient';

export const journalFields = [
  ['what_went_well', 'Was lief gut?'],
  ['would_do_differently', 'Was würde ich anders machen?'],
  ['additional_notes', 'Weitere Notizen'],
] as const;

export function journalTexts(value: JournalTexts): JournalTexts {
  return {
    what_went_well: value.what_went_well ?? '',
    would_do_differently: value.would_do_differently ?? '',
    additional_notes: value.additional_notes ?? '',
  };
}

export function sameJournalTexts(left: JournalTexts, right: JournalTexts): boolean {
  return journalFields.every(([field]) => (left[field] ?? '') === (right[field] ?? ''));
}

export function sameJournalVersion(left: JournalVersion, right: JournalVersion): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function journalQuery(search: string, tradeId: string) {
  const params = new URLSearchParams(search);
  const trades = params.getAll('trade_id');
  const versions = params.getAll('journal_version_id');
  const key = JSON.stringify([trades, versions]);
  if (trades.length !== 1 || trades[0] !== tradeId || !tradeId.trim() || versions.length > 1) {
    return {
      key,
      versionId: null,
      error:
        'Der Journalaufruf ist nicht eindeutig. Bitte genau einen Trade und höchstens eine Journalversions-ID angeben.',
    };
  }
  if (versions.length === 1 && !versions[0].trim()) {
    return {
      key,
      versionId: null,
      error: 'Die angefragte Journalversions-ID ist leer. Bitte den Quellenlink prüfen.',
    };
  }
  return { key, versionId: versions[0] ?? null, error: null };
}

export type JournalConfirmation = {
  command: JournalCommand;
  saved: JournalVersion | null;
  copySource: JournalVersion | null;
  sourceCurrentness: JournalEntry['source_currentness'] | null;
  handoff: JournalHistory['handoff'];
};

/** Inspection timestamps may change. The IDs, saved content and gate may not. */
export function confirmationIsCurrent(
  confirmation: JournalConfirmation,
  history: JournalHistory,
  entry: JournalEntry | null,
): boolean {
  const { command, saved } = confirmation;
  if (command.operation === 'CREATE_DRAFT') {
    const latest = history.versions.find((item) => item.is_latest)?.version;
    if ((latest?.id ?? null) !== command.expected_latest_version_id) return false;
    if (latest?.status === 'DRAFT') return false;
    if (
      latest &&
      (!confirmation.copySource || !sameJournalVersion(latest, confirmation.copySource))
    )
      return false;
  } else if (
    !entry ||
    !saved ||
    command.version_id !== saved.id ||
    ('expected_edit_revision' in command &&
      command.expected_edit_revision !== saved.edit_revision) ||
    !sameJournalVersion(saved, entry.version) ||
    confirmation.sourceCurrentness !== entry.source_currentness
  ) {
    return false;
  }
  if ('expected_exit_review_version_id' in command) {
    if (
      !history.handoff.ready ||
      history.handoff.exit_review_version_id !== command.expected_exit_review_version_id
    ) {
      return false;
    }
  }
  return (
    command.operation !== 'FINALIZE' ||
    (entry?.source_currentness === 'CURRENT' &&
      entry.version.source_exit_review_version_id === command.expected_exit_review_version_id)
  );
}
