import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

export type LessonState = 'CURRENT' | 'REVIEW_RECOMMENDED' | 'RETIRED';
export type EvidenceRelation = 'SUPPORTS' | 'CONTRADICTS' | 'CONTEXTUAL';
export type EvidenceChoice = { learning_evidence_id: string; relation: EvidenceRelation };
export interface LessonVersionSnapshot {
  version: {
    id: string;
    lesson_id: string;
    version: number;
    main_category: string;
    content: string;
    created_at: string;
    created_by: string;
    supersedes_version_id: string | null;
  };
  evidence_links: Array<EvidenceChoice & { id: string; lesson_version_id: string }>;
}
export interface ReviewContext {
  lesson: { id: string; title: string; current_version_id: string; current_state: LessonState };
  history: LessonVersionSnapshot[];
  signals: Array<{
    signal: {
      id: string;
      lesson_version_id: string;
      status: 'OPEN' | 'RESOLVED';
      resolution: string | null;
      raised_at: string;
      resolved_at: string | null;
      resulting_lesson_version_id: string | null;
    };
    trigger_link_ids: string[];
  }>;
  transitions: Array<{
    id: string;
    from_state: LessonState | null;
    to_state: LessonState;
    reason: string;
    related_lesson_version_id: string | null;
    occurred_at: string;
    occurred_by: string;
  }>;
  read_at: string;
}
export interface EvidenceSummary {
  evidence_id: string;
  source_type: string;
  source: {
    type: string;
    trade_id?: string;
    trade_journal_version_id?: string;
    exit_review_version_id?: string;
    external_observation_version_id?: string;
    external_observation_journal_version_id?: string;
  };
  created_at: string;
}
export interface SourceInspection {
  evidence_id: string;
  source_type: string;
  source_version_id: string;
  source_currentness: string;
  review_currentness: string | null;
  superseded_by_version_id: string | null;
  checked_at: string;
}
export type ReviewOperation =
  | 'OPEN_SOURCE_REVIEW'
  | 'OPEN_CONTRADICTION_REVIEW'
  | 'CONFIRM_UNCHANGED'
  | 'NEW_VERSION'
  | 'RETIRE';
type ReviewBase = {
  expected_current_version_id: string;
  expected_current_state: LessonState;
  expected_open_signal_id: string | null;
  reason: string;
  confirmed: true;
};
export type ReviewCommand = ReviewBase &
  (
    | { operation: 'OPEN_SOURCE_REVIEW'; reviewed_evidence_ids: string[] }
    | { operation: 'OPEN_CONTRADICTION_REVIEW'; contradiction_link_ids: string[] }
    | { operation: 'CONFIRM_UNCHANGED' | 'RETIRE' }
    | {
        operation: 'NEW_VERSION';
        main_category: string;
        content: string;
        evidence: EvidenceChoice[];
      }
  );
export interface ReviewReceipt {
  lesson_id: string;
  result_id: string;
  result_type: string;
  replayed: boolean;
}
const base = `${environment.apiBaseUrl}/api/v1/learning`;
export const lessonReviewClient = {
  context: (id: string, signal?: AbortSignal) =>
    requestJson<ReviewContext>(`${base}/lessons/${id}/review-context`, { signal }),
  evidence: (signal?: AbortSignal) =>
    requestJson<EvidenceSummary[]>(`${base}/learning-evidence`, { signal }),
  source: (id: string, signal?: AbortSignal) =>
    requestJson<SourceInspection>(`${base}/learning-evidence/${id}/currentness`, { signal }),
  execute: (id: string, command: ReviewCommand, key: string) =>
    requestJson<ReviewReceipt>(`${base}/lessons/${id}/review-commands`, {
      method: 'POST',
      body: command,
      headers: { 'Idempotency-Key': key },
    }),
};
export function evidenceLabel(item: EvidenceSummary): string {
  const source = item.source;
  const id =
    source.trade_journal_version_id ??
    source.exit_review_version_id ??
    source.external_observation_version_id ??
    source.external_observation_journal_version_id;
  return `${source.type} · ${id ?? 'Quelle unbekannt'} · erfasst ${item.created_at}`;
}
