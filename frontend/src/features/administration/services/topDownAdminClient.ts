import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

const referenceUrl = `${environment.apiBaseUrl}/api/v1/top-down-reference-data`;
const marketDataUrl = `${environment.apiBaseUrl}/api/v1/market-data`;
const analysisUrl = `${environment.apiBaseUrl}/api/v1/market-analyses`;

export type MarketReference = {
  id: string;
  code: string;
  name: string;
  reference_type: string;
  active: boolean;
};
export type Sector = { id: string; code: string; name: string; active: boolean };
export type ProviderMapping = {
  id: string;
  listing_id: string;
  status: string;
  provider_symbol: string;
  provider_exchange_code: string;
};
export type VenueReconciliation = {
  status: 'MATCHED' | 'CONFLICT' | 'AMBIGUOUS' | 'UNRESOLVED';
  listing_venue_id: string | null;
  evidence_venue_ids: string[];
  explanation: string;
};
export type AnalysisSummary = { id: string; underlying_id: string; listing_id: string };

const assignmentDefaults = () => ({
  valid_from: new Date().toISOString().slice(0, 10),
  valid_to: null,
  source: 'MANUAL_ADMIN',
  source_reference: 'Candidate live workflow',
  quality_status: 'GOOD',
});

export const topDownAdminClient = {
  references: (): Promise<MarketReference[]> =>
    requestJson<MarketReference[]>(`${referenceUrl}/market-references`),
  sectors: (): Promise<Sector[]> => requestJson<Sector[]>(`${referenceUrl}/sectors`),
  mappings: (): Promise<ProviderMapping[]> =>
    requestJson<ProviderMapping[]>(`${marketDataUrl}/provider-mappings`),

  assignBenchmark: (underlyingId: string, referenceId: string) =>
    requestJson<unknown>(`${referenceUrl}/underlyings/${underlyingId}/benchmark-assignments`, {
      method: 'POST',
      body: { ...assignmentDefaults(), market_reference_id: referenceId, role: 'BROAD_MARKET' },
    }),
  assignSector: (underlyingId: string, sectorId: string) =>
    requestJson<unknown>(`${referenceUrl}/underlyings/${underlyingId}/sector-assignments`, {
      method: 'POST',
      body: { ...assignmentDefaults(), sector_id: sectorId },
    }),
  assignSectorReference: (sectorId: string, referenceId: string) =>
    requestJson<unknown>(`${referenceUrl}/sectors/${sectorId}/reference-assignments`, {
      method: 'POST',
      body: { ...assignmentDefaults(), market_reference_id: referenceId },
    }),
  assignReferenceListing: (referenceId: string, listingId: string) =>
    requestJson<unknown>(`${referenceUrl}/market-references/${referenceId}/listing-assignments`, {
      method: 'POST',
      body: { ...assignmentDefaults(), listing_id: listingId },
    }),
  createMapping: (listingId: string, symbol: string, exchangeCode: string) =>
    requestJson<ProviderMapping>(`${marketDataUrl}/provider-mappings`, {
      method: 'PUT',
      body: {
        listing_id: listingId,
        provider: 'EODHD',
        provider_symbol: symbol,
        provider_exchange_code: exchangeCode,
        actor_name: 'Trading Workspace User',
      },
    }),
  validateMapping: (mappingId: string) =>
    requestJson<ProviderMapping>(`${marketDataUrl}/provider-mappings/${mappingId}/validate`, {
      method: 'POST',
      body: { enabled: true, actor_name: 'Trading Workspace User' },
    }),
  venueReconciliation: (mappingId: string) =>
    requestJson<VenueReconciliation>(
      `${marketDataUrl}/provider-mappings/${mappingId}/venue-reconciliation`,
    ),
  activateReference: (referenceId: string) =>
    requestJson<MarketReference>(`${referenceUrl}/market-references/${referenceId}/active`, {
      method: 'PATCH',
      body: { active: true },
    }),
  activateSector: (sectorId: string) =>
    requestJson<Sector>(`${referenceUrl}/sectors/${sectorId}/active`, {
      method: 'PATCH',
      body: { active: true },
    }),
  importHistory: (listingId: string, mappingId: string, startDate: string, endDate: string) =>
    requestJson<unknown>(`${marketDataUrl}/daily-prices/import`, {
      method: 'POST',
      body: {
        listing_id: listingId,
        mapping_id: mappingId,
        start_date: startDate,
        end_date: endDate,
      },
    }),
  createAnalysis: (underlyingId: string, listingId: string): Promise<AnalysisSummary> =>
    requestJson<AnalysisSummary>(analysisUrl, {
      method: 'POST',
      body: { underlying_id: underlyingId, listing_id: listingId },
    }),
  runAnalysis: (analysisId: string, startDate: string, endDate: string) =>
    requestJson<unknown>(`${analysisUrl}/${analysisId}/runs`, {
      method: 'POST',
      body: { start_date: startDate, end_date: endDate, parameters: {} },
    }),
};
