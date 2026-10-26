import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

const base = `${environment.apiBaseUrl}/api/v1/top-down-reference-data`;
export interface SectorProposal {
  code: string;
  sector: string;
  benchmark: string;
  ticker: string;
  isin: string;
  source_url: string;
  mic: string;
  currency: string;
  classification_system: string;
  classification_version: string;
  reviewed_on: string;
  taxonomy_source: string;
  venue_source: string;
  provider_coverage: string;
}
export const chartSetupClient = {
  proposals: (signal?: AbortSignal) =>
    requestJson<SectorProposal[]>(`${base}/sector-proposals`, { method: 'GET', signal }),
  write: (path: string, body?: unknown, method: 'POST' | 'PUT' = 'POST') =>
    requestJson<unknown>(`${base}/${path}`, { method, body }),
};
