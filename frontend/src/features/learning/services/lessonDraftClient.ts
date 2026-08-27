import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { LessonDraftCreateRequest, LessonDraftCreateResponse } from '../types/lessonDraft';

const lessonsUrl = `${environment.apiBaseUrl}/api/v1/learning/lessons`;

export const lessonDraftClient = {
  createFromEvidence: (
    learningEvidenceId: string,
    input: Omit<LessonDraftCreateRequest, 'evidence_links'>,
  ): Promise<LessonDraftCreateResponse> =>
    requestJson<LessonDraftCreateResponse>(lessonsUrl, {
      method: 'POST',
      body: {
        ...input,
        evidence_links: [
          {
            learning_evidence_id: learningEvidenceId,
            relation: 'SUPPORTS',
          },
        ],
      },
    }),
};
