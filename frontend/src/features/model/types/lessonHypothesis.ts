export type HypothesisStatus = 'OPEN' | 'PROPOSED' | 'CLOSED';

export interface LessonHypothesis {
  id: string;
  title: string;
  statement: string;
  status: HypothesisStatus;
  source_lesson_version_id: string | null;
  created_at: string;
  created_by: string;
}

export interface CreateLessonHypothesisInput {
  title: string;
  statement: string;
}
