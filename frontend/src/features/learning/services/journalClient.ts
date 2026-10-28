import { environment } from '../../../services/environment';
import {
  getRequestIdentity,
  type RequestIdentity,
} from '../../../services/identity/requestIdentity';
import { requestJson } from '../../market/services/http';

export type JournalTexts = {
  what_went_well: string | null;
  would_do_differently: string | null;
  additional_notes: string | null;
};
export type JournalVersion = JournalTexts & {
  id: string;
  trade_journal_id: string;
  version: number;
  edit_revision: number;
  status: 'DRAFT' | 'FINALIZED';
  source_exit_review_version_id: string | null;
  supersedes_version_id: string | null;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  finalized_at: string | null;
  finalized_by: string | null;
};
export type JournalEntry = {
  version: JournalVersion;
  is_latest: boolean;
  source_currentness: 'CURRENT' | 'STALE' | 'UNKNOWN';
  source_checked_at: string;
  learning_evidence_id: string | null;
};
export type JournalHistory = {
  trade_id: string;
  journal_id: string | null;
  handoff: { ready: boolean; reason: string; exit_review_version_id: string | null };
  versions: JournalEntry[];
};
export type JournalCommand =
  | {
      operation: 'CREATE_DRAFT';
      expected_latest_version_id: string | null;
      expected_exit_review_version_id: string;
      confirmed: true;
    }
  | ({ operation: 'SAVE_DRAFT'; version_id: string; expected_edit_revision: number } & JournalTexts)
  | {
      operation: 'FINALIZE' | 'REBIND_SOURCE';
      version_id: string;
      expected_edit_revision: number;
      expected_exit_review_version_id: string;
      confirmed: true;
    }
  | { operation: 'MATERIALIZE'; version_id: string; confirmed: true };

/** A receipt confirms the command, never the draft's current content or revision. */
export type JournalReceipt = {
  result_id: string;
  result_type: string;
  replayed: boolean;
};

export type JournalActor = Readonly<Partial<RequestIdentity>>;

/** Keep the actor with the command and key for an explicitly requested retry. */
export function snapshotJournalActor(): JournalActor {
  return Object.freeze({ ...getRequestIdentity() });
}

/** Validate the complete read context before selecting an exact journal source. */
export function selectJournalEntry(
  history: JournalHistory,
  tradeId: string,
  versionId: string | null,
): JournalEntry | null {
  if (!tradeId || history.trade_id !== tradeId) {
    throw new Error('Der gelesene Journalstand gehört nicht zum angefragten Trade.');
  }
  const seen = new Set<string>();
  for (const entry of history.versions) {
    if (!history.journal_id || entry.version.trade_journal_id !== history.journal_id) {
      throw new Error('Die Journalversion gehört nicht zum gelesenen Journal.');
    }
    if (seen.has(entry.version.id)) {
      throw new Error('Der gelesene Journalstand enthält widersprüchliche Versionsidentitäten.');
    }
    seen.add(entry.version.id);
  }
  if (versionId !== null) {
    if (!versionId.trim()) {
      throw new Error('Die angefragte Journalversions-ID ist leer. Bitte den Quellenlink prüfen.');
    }
    const selected = history.versions.find((entry) => entry.version.id === versionId);
    if (!selected) {
      throw new Error(
        'Die angefragte Journalversion ist für diesen Trade und dieses Journal nicht vorhanden.',
      );
    }
    return selected;
  }
  if (history.versions.length === 0) return null;
  const latest = history.versions.filter((entry) => entry.is_latest);
  if (latest.length !== 1) {
    throw new Error('Der neueste gespeicherte Journalstand ist nicht eindeutig bestimmt.');
  }
  return latest[0];
}

const base = `${environment.apiBaseUrl}/api/v1/learning`;
export const journalClient = {
  history: (tradeId: string, signal?: AbortSignal) =>
    requestJson<JournalHistory>(`${base}/trades/${tradeId}/journal`, { signal }),
  version: (versionId: string, signal?: AbortSignal) =>
    requestJson<JournalHistory>(`${base}/journal-versions/${versionId}`, { signal }),
  command: (tradeId: string, command: JournalCommand, key: string, actor?: JournalActor) =>
    requestJson<JournalReceipt>(`${base}/trades/${tradeId}/journal/commands`, {
      method: 'POST',
      body: command,
      headers: { 'Idempotency-Key': key },
      actor,
    }),
};
