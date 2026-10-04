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
  proposals: () => requestJson<SectorProposal[]>(`${base}/sector-proposals`),
  write: (path: string, body?: unknown, method: 'POST' | 'PUT' = 'POST') =>
    requestJson<Record<string, unknown>>(`${base}/${path}`, { method, body }),
};
