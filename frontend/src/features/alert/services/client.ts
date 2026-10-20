import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  AlertResponse,
  MonitoringRuntimeStatusResponse,
  PositionMonitoringHealthResponse,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/alerts`;
const monitoringBaseUrl = `${environment.apiBaseUrl}/api/v1/position-monitoring`;

export const alertApiClient = {
  monitoringRuntime: (signal?: AbortSignal): Promise<MonitoringRuntimeStatusResponse> =>
    requestJson<MonitoringRuntimeStatusResponse>(`${monitoringBaseUrl}/runtime/status`, { signal }),

  forTrade: (tradeId: string, signal?: AbortSignal): Promise<AlertResponse[]> =>
    requestJson<AlertResponse[]>(`${baseUrl}/trades/${encodeURIComponent(tradeId)}`, { signal }),

  monitoringHealth: (
    tradeId: string,
    signal?: AbortSignal,
  ): Promise<PositionMonitoringHealthResponse> =>
    requestJson<PositionMonitoringHealthResponse>(
      `${monitoringBaseUrl}/trades/${encodeURIComponent(tradeId)}/health`,
      { signal },
    ),
};
