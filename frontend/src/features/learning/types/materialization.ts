export interface Ft011MaterializationStatus {
  ready: boolean;
  reason: string;
  materialized: boolean;
  learning_evidence_id: string | null;
  exit_review_version_id: string | null;
}

export interface MaterializeFt011LearningEvidenceResponse {
  learning_evidence_id: string;
  exit_review_version_id: string;
  created: boolean;
  replayed: boolean;
}

export interface Ft011EvidenceHistoryItem {
  learning_evidence_id: string;
  evidence_type: 'FT011';
  materialized_at: string;
  trade_id: string;
  post_trade_observation_id: string;
  exit_review_id: string;
  exit_review_version_id: string;
  review_version: number | null;
  review_status: string | null;
  stored_review_currentness: string | null;
  source_currentness: 'CURRENT' | 'STALE' | 'UNKNOWN';
  superseded_by_version_id: string | null;
  checked_at: string;
  lesson_links: {
    link_id: string;
    lesson_id: string;
    lesson_title: string;
    lesson_version_id: string;
    lesson_version: number;
    relation: 'SUPPORTS' | 'CONTRADICTS' | 'CONTEXTUAL';
    is_current_version: boolean;
  }[];
}
