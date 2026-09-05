import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { OperationalWorkspaceResponse } from '../types';

const url = `${environment.apiBaseUrl}/api/v1/operational-workspace/actions`;

export const operationalWorkspaceApiClient = {
  getActions: (signal?: AbortSignal): Promise<OperationalWorkspaceResponse> =>
    requestJson<OperationalWorkspaceResponse>(url, { signal }),
};
