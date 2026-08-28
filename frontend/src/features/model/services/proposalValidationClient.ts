import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  CreateModelValidationInput,
  ModelValidationSummary,
} from '../types/proposalValidation';

const baseUrl = `${environment.apiBaseUrl}/api/v1/model-governance`;

export const proposalValidationClient = {
  listForProposal: (
    proposalId: string,
    signal?: AbortSignal,
  ): Promise<ModelValidationSummary[]> =>
    requestJson<ModelValidationSummary[]>(`${baseUrl}/proposals/${proposalId}/validations`, {
      signal,
    }),

  create: (
    proposalId: string,
    input: CreateModelValidationInput,
  ): Promise<ModelValidationSummary> =>
    requestJson<ModelValidationSummary>(`${baseUrl}/proposals/${proposalId}/validations`, {
      method: 'POST',
      body: input,
    }),
};
