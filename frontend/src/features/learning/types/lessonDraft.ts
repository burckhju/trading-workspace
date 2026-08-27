export interface LessonDraftCreateRequest {
  title: string;
  main_category: string;
  content: string;
  evidence_links: Array<{
    learning_evidence_id: string;
    relation: 'SUPPORTS';
  }>;
  tags: string[];
}

export interface LessonDraftCreateResponse {
  lesson_id: string;
  current_version_id: string;
  version: number;
  current_state: string;
  title: string;
  main_category: string;
  content: string;
  evidence: Array<{
    id: string;
    learning_evidence_id: string;
    relation: string;
  }>;
}
