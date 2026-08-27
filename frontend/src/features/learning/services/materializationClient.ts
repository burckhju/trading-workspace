import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  Ft011MaterializationStatus,
  MaterializeFt011LearningEvidenceResponse,
} from '../types/materialization';

const baseUrl = `${environment.apiBaseUrl}/api/v1/learning/trades`;

function tradeUrl(tradeId: string, path: string): string {
  return `${baseUrl}/${tradeId}${path}`;
}

export const ft011MaterializationClient = {
  status: (tradeId: string, signal?: AbortSignal): Promise<Ft011MaterializationStatus> =>
    requestJson<Ft011MaterializationStatus>(
      tradeUrl(tradeId, '/ft011-evidence/materialization-status'),
      { signal },
    ),

  materialize: (
    tradeId: string,
    idempotencyKey: string,
  ): Promise<MaterializeFt011LearningEvidenceResponse> =>
    requestJson<MaterializeFt011LearningEvidenceResponse>(
      tradeUrl(tradeId, '/ft011-evidence/materialize'),
      {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
      },
    ),
};
