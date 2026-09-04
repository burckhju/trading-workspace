import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { AlertResponse } from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/alerts`;

export const alertApiClient = {
  forTrade: (tradeId: string, signal?: AbortSignal): Promise<AlertResponse[]> =>
    requestJson<AlertResponse[]>(`${baseUrl}/trades/${encodeURIComponent(tradeId)}`, { signal }),
};
