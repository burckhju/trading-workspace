import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  AlertResponse,
  PositionMonitoringHealthResponse,
  PositionValuationResponse,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/alerts`;
const monitoringBaseUrl = `${environment.apiBaseUrl}/api/v1/position-monitoring`;

export const alertApiClient = {
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

  valuation: (tradeId: string, signal?: AbortSignal): Promise<PositionValuationResponse> =>
    requestJson<PositionValuationResponse>(
      `${monitoringBaseUrl}/trades/${encodeURIComponent(tradeId)}/valuation`,
      { signal },
    ),
};
