import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  CreateModelChangeProposalInput,
  GovernedModelSummary,
  GovernedModelVersion,
  ModelChangeProposalSummary,
} from '../types/hypothesisProposal';

const baseUrl = `${environment.apiBaseUrl}/api/v1/model-governance`;

export const hypothesisProposalClient = {
  listForHypothesis: (
    hypothesisId: string,
    signal?: AbortSignal,
  ): Promise<ModelChangeProposalSummary[]> =>
    requestJson<ModelChangeProposalSummary[]>(`${baseUrl}/hypotheses/${hypothesisId}/proposals`, {
      signal,
    }),

  listModels: (signal?: AbortSignal): Promise<GovernedModelSummary[]> =>
    requestJson<GovernedModelSummary[]>(`${baseUrl}/models`, { signal }),

  listVersions: (modelId: string, signal?: AbortSignal): Promise<GovernedModelVersion[]> =>
    requestJson<GovernedModelVersion[]>(`${baseUrl}/models/${modelId}/versions`, { signal }),

  create: (input: CreateModelChangeProposalInput): Promise<ModelChangeProposalSummary> =>
    requestJson<ModelChangeProposalSummary>(`${baseUrl}/proposals`, {
      method: 'POST',
      body: input,
    }),
};
