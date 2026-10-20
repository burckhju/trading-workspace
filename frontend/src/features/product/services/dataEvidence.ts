import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  QuoteHistoryReport,
  ValuationEvidenceView,
  ValuationFacts,
} from '../types/dataEvidence';

const base = `${environment.apiBaseUrl}/api/v1`;
export const dataEvidenceApi = {
  facts: (id: string, signal?: AbortSignal) =>
    requestJson<ValuationEvidenceView>(`${base}/warrants/${id}/valuation-evidence`, { signal }),
  recordFacts: (
    id: string,
    request: {
      terms_id: string;
      expected_version: number;
      expected_revision: number;
      facts: ValuationFacts;
      confirmation: 'CONFIRM_DOCUMENT_REVIEW';
    },
    signal?: AbortSignal,
  ) =>
    requestJson<ValuationEvidenceView>(`${base}/warrants/${id}/valuation-evidence`, {
      method: 'POST',
      body: request,
      signal,
    }),
  history: (id: string, days: number, signal?: AbortSignal) =>
    requestJson<QuoteHistoryReport>(
      `${base}/market-data/warrants/${id}/quote-history?days=${days}`,
      { signal },
    ),
};
