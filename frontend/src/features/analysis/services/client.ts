import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  AnalysisDetail,
  AnalysisOverviewPage,
  AnalysisRun,
  AnalysisRunDetail,
  AnalysisSummary,
  AnalysisEvent,
  AnalysisVerification,
  SnapshotPage,
  RunAnalysisRequest,
} from '../types/api';

const baseUrl = `${environment.apiBaseUrl}/api/v1/market-analyses`;

export type OverviewFilters = {
  underlyingId?: string;
  status?: string;
  qualityStatus?: string;
  analysisTimeFrom?: string;
  analysisTimeTo?: string;
  sortBy?: string;
  sortDirection?: string;
};

function overviewParams(
  filters: OverviewFilters,
  offset?: number,
  limit?: number,
): URLSearchParams {
  const params = new URLSearchParams();
  if (offset !== undefined) params.set('offset', String(offset));
  if (limit !== undefined) params.set('limit', String(limit));
  if (filters.underlyingId) params.set('underlying_id', filters.underlyingId);
  if (filters.status) params.set('status', filters.status);
  if (filters.qualityStatus) params.set('quality_status', filters.qualityStatus);
  if (filters.analysisTimeFrom) params.set('analysis_time_from', filters.analysisTimeFrom);
  if (filters.analysisTimeTo) params.set('analysis_time_to', filters.analysisTimeTo);
  if (filters.sortBy) params.set('sort_by', filters.sortBy);
  if (filters.sortDirection) params.set('sort_direction', filters.sortDirection);
  return params;
}

export const analysisApiClient = {
  list: (signal?: AbortSignal): Promise<AnalysisSummary[]> =>
    requestJson<AnalysisSummary[]>(baseUrl, { signal }),

  listPage: (
    offset: number,
    limit: number,
    filters: OverviewFilters = {},
    signal?: AbortSignal,
  ): Promise<AnalysisOverviewPage> => {
    const params = overviewParams(filters, offset, limit);
    return requestJson<AnalysisOverviewPage>(`${baseUrl}/page?${params.toString()}`, { signal });
  },

  exportUrl: (filters: OverviewFilters = {}): string =>
    `${baseUrl}/export.csv?${overviewParams(filters).toString()}`,

  get: (id: string, signal?: AbortSignal): Promise<AnalysisDetail> =>
    requestJson<AnalysisDetail>(`${baseUrl}/${id}`, { signal }),

  create: (underlyingId: string, listingId: string): Promise<AnalysisSummary> =>
    requestJson<AnalysisSummary>(baseUrl, {
      method: 'POST',
      body: { underlying_id: underlyingId, listing_id: listingId },
    }),

  run: (id: string, request: RunAnalysisRequest): Promise<AnalysisRun> =>
    requestJson<AnalysisRun>(`${baseUrl}/${id}/runs`, { method: 'POST', body: request }),

  getRun: (id: string, version: number, signal?: AbortSignal): Promise<AnalysisRunDetail> =>
    requestJson<AnalysisRunDetail>(`${baseUrl}/${id}/runs/${version}?include_snapshot=false`, {
      signal,
    }),

  getSnapshot: (
    id: string,
    version: number,
    offset: number,
    limit: number,
    signal?: AbortSignal,
  ): Promise<SnapshotPage> =>
    requestJson<SnapshotPage>(
      `${baseUrl}/${id}/runs/${version}/snapshot?offset=${offset}&limit=${limit}`,
      { signal },
    ),

  events: (id: string, signal?: AbortSignal): Promise<AnalysisEvent[]> =>
    requestJson<AnalysisEvent[]>(`${baseUrl}/${id}/events`, { signal }),

  verify: (id: string, version: number): Promise<AnalysisVerification> =>
    requestJson<AnalysisVerification>(`${baseUrl}/${id}/runs/${version}/verify`, {
      method: 'POST',
    }),

  retry: (id: string, version: number, reason?: string): Promise<AnalysisRun> =>
    requestJson<AnalysisRun>(`${baseUrl}/${id}/runs/${version}/retry`, {
      method: 'POST',
      body: { reason: reason || null },
    }),

  supersede: (
    id: string,
    version: number,
    replacementVersion: number,
    reason?: string,
  ): Promise<AnalysisEvent> =>
    requestJson<AnalysisEvent>(`${baseUrl}/${id}/runs/${version}/supersede`, {
      method: 'POST',
      body: { replacement_version: replacementVersion, reason: reason || null },
    }),
};

export const listAnalyses = analysisApiClient.list;
export const getAnalysis = analysisApiClient.get;
export const createAnalysis = analysisApiClient.create;
