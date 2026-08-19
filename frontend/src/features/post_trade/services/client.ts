import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  ExitReviewDraftRequest,
  ExitReviewResponse,
  HandoffResponse,
  ObservationEvidenceResponse,
  ObservationResponse,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/post-trade/trades`;

function tradeUrl(tradeId: string, path: string): string {
  return `${baseUrl}/${tradeId}${path}`;
}

export const postTradeApiClient = {
  startObservation: (tradeId: string): Promise<ObservationResponse> =>
    requestJson<ObservationResponse>(tradeUrl(tradeId, '/observation'), {
      method: 'POST',
    }),

  observation: (tradeId: string, signal?: AbortSignal): Promise<ObservationResponse> =>
    requestJson<ObservationResponse>(tradeUrl(tradeId, '/observation'), {
      signal,
    }),

  evidence: (tradeId: string, signal?: AbortSignal): Promise<ObservationEvidenceResponse> =>
    requestJson<ObservationEvidenceResponse>(tradeUrl(tradeId, '/observation/evidence'), {
      signal,
    }),

  createReviewDraft: (tradeId: string): Promise<ExitReviewResponse> =>
    requestJson<ExitReviewResponse>(tradeUrl(tradeId, '/exit-review'), {
      method: 'POST',
    }),

  review: (tradeId: string, signal?: AbortSignal): Promise<ExitReviewResponse> =>
    requestJson<ExitReviewResponse>(tradeUrl(tradeId, '/exit-review'), {
      signal,
    }),

  updateReviewDraft: (
    tradeId: string,
    request: ExitReviewDraftRequest,
  ): Promise<ExitReviewResponse> =>
    requestJson<ExitReviewResponse>(tradeUrl(tradeId, '/exit-review/draft'), {
      method: 'PUT',
      body: request,
    }),

  finalizeReview: (tradeId: string): Promise<ExitReviewResponse> =>
    requestJson<ExitReviewResponse>(tradeUrl(tradeId, '/exit-review/finalize'), {
      method: 'POST',
    }),

  revalidateReview: (tradeId: string): Promise<ExitReviewResponse> =>
    requestJson<ExitReviewResponse>(tradeUrl(tradeId, '/exit-review/revalidate'), {
      method: 'POST',
    }),

  reviewHistory: (tradeId: string, signal?: AbortSignal): Promise<ExitReviewResponse[]> =>
    requestJson<ExitReviewResponse[]>(tradeUrl(tradeId, '/exit-review/history'), {
      signal,
    }),

  handoff: (tradeId: string, signal?: AbortSignal): Promise<HandoffResponse> =>
    requestJson<HandoffResponse>(tradeUrl(tradeId, '/handoff'), {
      signal,
    }),
};
