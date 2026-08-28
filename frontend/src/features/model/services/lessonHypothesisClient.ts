import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { CreateLessonHypothesisInput, LessonHypothesis } from '../types/lessonHypothesis';

const baseUrl = `${environment.apiBaseUrl}/api/v1/model-governance/lesson-versions`;

export const lessonHypothesisClient = {
  listForLessonVersion: (lessonVersionId: string, signal?: AbortSignal): Promise<LessonHypothesis[]> =>
    requestJson<LessonHypothesis[]>(`${baseUrl}/${lessonVersionId}/hypotheses`, { signal }),

  createFromLessonVersion: (
    lessonVersionId: string,
    input: CreateLessonHypothesisInput,
  ): Promise<LessonHypothesis> =>
    requestJson<LessonHypothesis>(`${baseUrl}/${lessonVersionId}/hypotheses`, {
      method: 'POST',
      body: input,
    }),
};
