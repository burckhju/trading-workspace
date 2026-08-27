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
