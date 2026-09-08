import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { OperationalPositionsResponse, OperationalWorkspaceResponse } from '../types';

const baseUrl = `${environment.apiBaseUrl}/api/v1/operational-workspace`;

export const operationalWorkspaceApiClient = {
  getActions: (signal?: AbortSignal): Promise<OperationalWorkspaceResponse> =>
    requestJson<OperationalWorkspaceResponse>(`${baseUrl}/actions`, { signal }),
  getPositions: (signal?: AbortSignal): Promise<OperationalPositionsResponse> =>
    requestJson<OperationalPositionsResponse>(`${baseUrl}/positions`, { signal }),
};
