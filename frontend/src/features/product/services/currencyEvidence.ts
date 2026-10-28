import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  CurrencyEvidence,
  CurrencyEvidenceHistory,
  CurrencyEvidenceRequest,
} from '../types/currencyEvidence';

const url = (id: string) => `${environment.apiBaseUrl}/api/v1/warrants/${id}/currency-evidence`;

export const currencyEvidenceApi = {
  history: (id: string, signal?: AbortSignal) =>
    requestJson<CurrencyEvidenceHistory>(url(id), { signal }),
  record: (id: string, request: CurrencyEvidenceRequest, signal?: AbortSignal) =>
    requestJson<CurrencyEvidence>(url(id), { method: 'POST', body: request, signal }),
};
