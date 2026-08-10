import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { Candidate, CandidateEvaluation, CandidateLiveWorkflow } from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/candidates`;

export const candidateApiClient = {
  list: (signal?: AbortSignal): Promise<Candidate[]> =>
    requestJson<Candidate[]>(baseUrl, { signal }),

  evaluations: (candidateId: string, signal?: AbortSignal): Promise<CandidateEvaluation[]> =>
    requestJson<CandidateEvaluation[]>(`${baseUrl}/${candidateId}/evaluations`, { signal }),

  liveWorkflow: (candidateId: string, signal?: AbortSignal): Promise<CandidateLiveWorkflow> =>
    requestJson<CandidateLiveWorkflow>(`${baseUrl}/${candidateId}/live-workflow`, { signal }),

  evaluateAuto: (candidateId: string): Promise<CandidateEvaluation> =>
    requestJson<CandidateEvaluation>(`${baseUrl}/${candidateId}/evaluations/auto`, {
      method: 'POST',
      body: {},
    }),
};
