import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  ProductEvaluationResponse,
  ProductSelectionRunDetailResponse,
  ProductSelectionRunSummaryResponse,
  SelectProductRequest,
  StartProductSelectionRunRequest,
  Uuid,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/product-selection-runs`;

export const productSelectionApiClient = {
  start: (request: StartProductSelectionRunRequest): Promise<ProductSelectionRunDetailResponse> =>
    requestJson<ProductSelectionRunDetailResponse>(baseUrl, { method: 'POST', body: request }),

  listForTradePlanVersion: (
    tradePlanVersionId: Uuid,
    signal?: AbortSignal,
  ): Promise<ProductSelectionRunSummaryResponse[]> =>
    requestJson<ProductSelectionRunSummaryResponse[]>(
      `${baseUrl}?trade_plan_version_id=${encodeURIComponent(tradePlanVersionId)}`,
      { signal },
    ),

  get: (runId: Uuid, signal?: AbortSignal): Promise<ProductSelectionRunDetailResponse> =>
    requestJson<ProductSelectionRunDetailResponse>(`${baseUrl}/${runId}`, { signal }),

  getEvaluation: (
    runId: Uuid,
    evaluationId: Uuid,
    signal?: AbortSignal,
  ): Promise<ProductEvaluationResponse> =>
    requestJson<ProductEvaluationResponse>(`${baseUrl}/${runId}/evaluations/${evaluationId}`, {
      signal,
    }),

  select: (
    runId: Uuid,
    request: SelectProductRequest,
  ): Promise<ProductSelectionRunDetailResponse> =>
    requestJson<ProductSelectionRunDetailResponse>(`${baseUrl}/${runId}/selection`, {
      method: 'POST',
      body: request,
    }),
};
