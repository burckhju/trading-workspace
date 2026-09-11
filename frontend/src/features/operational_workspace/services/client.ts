import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  OperationalPositionsResponse,
  OperationalWorkspaceResponse,
  PositionAlertProjection,
} from '../types';

const baseUrl = `${environment.apiBaseUrl}/api/v1/operational-workspace`;
const monitoringBaseUrl = `${environment.apiBaseUrl}/api/v1/position-monitoring`;

export const operationalWorkspaceApiClient = {
  getActions: (signal?: AbortSignal): Promise<OperationalWorkspaceResponse> =>
    requestJson<OperationalWorkspaceResponse>(`${baseUrl}/actions`, { signal }),
  getPositions: (signal?: AbortSignal): Promise<OperationalPositionsResponse> =>
    requestJson<OperationalPositionsResponse>(`${baseUrl}/positions`, { signal }),
  getPositionAlertProjection: (
    tradeId: string,
    signal?: AbortSignal,
  ): Promise<PositionAlertProjection> =>
    requestJson<PositionAlertProjection>(
      `${monitoringBaseUrl}/trades/${tradeId}/alert-projection`,
      { signal },
    ),
};
