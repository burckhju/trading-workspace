import { environment } from '../../../services/environment';
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
const base = `${environment.apiBaseUrl}/api/v1/learning`;
export const journalClient = {
  history: (tradeId: string, signal?: AbortSignal) =>
    requestJson<JournalHistory>(`${base}/trades/${tradeId}/journal`, { signal }),
  version: (versionId: string, signal?: AbortSignal) =>
    requestJson<JournalHistory>(`${base}/journal-versions/${versionId}`, { signal }),
  command: (tradeId: string, command: JournalCommand, key: string) =>
    requestJson<{ result_id: string; result_type: string; replayed: boolean }>(
      `${base}/trades/${tradeId}/journal/commands`,
      { method: 'POST', body: command, headers: { 'Idempotency-Key': key } },
    ),
};
