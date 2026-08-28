import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { RuntimeActivation } from '../types/runtimeActivation';

const baseUrl = `${environment.apiBaseUrl}/api/v1/model-governance`;

export const runtimeActivationClient = {
  getCurrent: (modelId: string, signal?: AbortSignal): Promise<RuntimeActivation | null> =>
    requestJson<RuntimeActivation | null>(`${baseUrl}/models/${modelId}/runtime-activation`, {
      signal,
    }),

  activate: (
    modelId: string,
    versionId: string,
    correlationId?: string,
  ): Promise<RuntimeActivation> =>
    requestJson<RuntimeActivation>(`${baseUrl}/models/${modelId}/versions/${versionId}/activate`, {
      method: 'POST',
      correlationId,
    }),
};
