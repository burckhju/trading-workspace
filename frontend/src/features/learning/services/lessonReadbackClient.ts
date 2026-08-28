import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { LessonDetail, LessonEvidenceReference } from '../types/lessonReadback';

const baseUrl = `${environment.apiBaseUrl}/api/v1/learning`;

export const lessonReadbackClient = {
  listForEvidence: (
    learningEvidenceId: string,
    signal?: AbortSignal,
  ): Promise<LessonEvidenceReference[]> =>
    requestJson<LessonEvidenceReference[]>(
      `${baseUrl}/learning-evidence/${learningEvidenceId}/lessons`,
      { signal },
    ),

  getLesson: (lessonId: string, signal?: AbortSignal): Promise<LessonDetail> =>
    requestJson<LessonDetail>(`${baseUrl}/lessons/${lessonId}`, { signal }),
};
