export interface LessonEvidenceReference {
  lesson_id: string;
  current_version_id: string;
  current_state: 'CURRENT' | 'REVIEW_RECOMMENDED' | 'RETIRED';
  title: string;
}

export interface LessonDetail {
  lesson_id: string;
  current_version_id: string;
  current_state: 'CURRENT' | 'REVIEW_RECOMMENDED' | 'RETIRED';
  version: number;
  title: string;
  main_category: string;
  content: string;
  evidence: Array<{
    id: string;
    learning_evidence_id: string;
    relation: 'SUPPORTS' | 'CONTRADICTS' | 'CONTEXTUAL';
  }>;
  created_at: string;
  created_by: string;
}
