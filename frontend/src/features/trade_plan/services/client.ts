import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  AmendTradePlanRequest,
  CreateTradePlanRequest,
  LifecycleReasonRequest,
  TradePlanDetailResponse,
  TradePlanMutationOptions,
  TradePlanVersionResponse,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/trade-plans`;

function mutationOptions(method: 'POST', body: unknown, options?: TradePlanMutationOptions) {
  return {
    method,
    body,
    correlationId: options?.correlationId,
  } as const;
}

function normalizeDecimal(value: string | number | null | undefined) {
  return typeof value === 'string' ? value.replace(',', '.') : value;
}

function normalizeTradePlanContent<T extends CreateTradePlanRequest | AmendTradePlanRequest>(
  request: T,
): T {
  return {
    ...request,
    entry: {
      ...request.entry,
      price: normalizeDecimal(request.entry.price),
      price_from: normalizeDecimal(request.entry.price_from),
      price_to: normalizeDecimal(request.entry.price_to),
      reference_price: normalizeDecimal(request.entry.reference_price),
    },
    invalidation: {
      ...request.invalidation,
      stop_price: normalizeDecimal(request.invalidation.stop_price),
    },
    targets: request.targets.map((target) => ({
      ...target,
      price: normalizeDecimal(target.price) ?? target.price,
    })),
  } as T;
}

export const tradePlanApiClient = {
  create: (
    request: CreateTradePlanRequest,
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanDetailResponse> =>
    requestJson<TradePlanDetailResponse>(
      baseUrl,
      mutationOptions('POST', normalizeTradePlanContent(request), options),
    ),

  get: (tradePlanId: string, signal?: AbortSignal): Promise<TradePlanDetailResponse> =>
    requestJson<TradePlanDetailResponse>(`${baseUrl}/${tradePlanId}`, { signal }),

  versions: (tradePlanId: string, signal?: AbortSignal): Promise<TradePlanVersionResponse[]> =>
    requestJson<TradePlanVersionResponse[]>(`${baseUrl}/${tradePlanId}/versions`, { signal }),

  version: (
    tradePlanId: string,
    versionId: string,
    signal?: AbortSignal,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(`${baseUrl}/${tradePlanId}/versions/${versionId}`, {
      signal,
    }),

  amend: (
    tradePlanId: string,
    baseVersionId: string,
    request: AmendTradePlanRequest,
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(
      `${baseUrl}/${tradePlanId}/versions/${baseVersionId}/amendments`,
      mutationOptions('POST', normalizeTradePlanContent(request), options),
    ),

  submitForReview: (
    tradePlanId: string,
    versionId: string,
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(
      `${baseUrl}/${tradePlanId}/versions/${versionId}/submit-review`,
      mutationOptions('POST', undefined, options),
    ),

  returnToDraft: (
    tradePlanId: string,
    versionId: string,
    request: LifecycleReasonRequest = {},
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(
      `${baseUrl}/${tradePlanId}/versions/${versionId}/return-draft`,
      mutationOptions('POST', request, options),
    ),

  abandon: (
    tradePlanId: string,
    versionId: string,
    request: LifecycleReasonRequest = {},
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(
      `${baseUrl}/${tradePlanId}/versions/${versionId}/abandon`,
      mutationOptions('POST', request, options),
    ),

  approve: (
    tradePlanId: string,
    versionId: string,
    options?: TradePlanMutationOptions,
  ): Promise<TradePlanVersionResponse> =>
    requestJson<TradePlanVersionResponse>(
      `${baseUrl}/${tradePlanId}/versions/${versionId}/approve`,
      mutationOptions('POST', undefined, options),
    ),
};
