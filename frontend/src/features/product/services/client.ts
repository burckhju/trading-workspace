import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  AddWarrantListingRequest,
  AddWarrantTermsRequest,
  CreateWarrantRequest,
  WarrantListingResponse,
  WarrantResponse,
  WarrantTermsResponse,
} from '../types/api';

function warrantUrl(path = ''): string {
  return `${environment.apiBaseUrl}/api/v1/warrants${path}`;
}

function normalizeDecimalInput(value: string): string {
  return value.trim().replace(',', '.');
}

export const warrantApiClient = {
  list: (signal?: AbortSignal) => requestJson<WarrantResponse[]>(warrantUrl(), { signal }),
  get: (id: string, signal?: AbortSignal) =>
    requestJson<WarrantResponse>(warrantUrl(`/${id}`), { signal }),
  create: (request: CreateWarrantRequest) =>
    requestJson<WarrantResponse>(warrantUrl(), {
      method: 'POST',
      body: {
        ...request,
        strike: normalizeDecimalInput(request.strike),
        ratio: normalizeDecimalInput(request.ratio),
      },
    }),
  deactivate: (id: string, version: number) =>
    requestJson<WarrantResponse>(warrantUrl(`/${id}/deactivate`), {
      method: 'POST',
      body: { version },
    }),
  reactivate: (id: string, version: number) =>
    requestJson<WarrantResponse>(warrantUrl(`/${id}/reactivate`), {
      method: 'POST',
      body: { version },
    }),
  terms: (id: string, signal?: AbortSignal) =>
    requestJson<WarrantTermsResponse[]>(warrantUrl(`/${id}/terms`), { signal }),
  addTerms: (id: string, request: AddWarrantTermsRequest) =>
    requestJson<WarrantTermsResponse>(warrantUrl(`/${id}/terms`), {
      method: 'POST',
      body: {
        ...request,
        strike: normalizeDecimalInput(request.strike),
        ratio: normalizeDecimalInput(request.ratio),
      },
    }),
  listings: (id: string, signal?: AbortSignal) =>
    requestJson<WarrantListingResponse[]>(warrantUrl(`/${id}/listings`), { signal }),
  addListing: (id: string, request: AddWarrantListingRequest) =>
    requestJson<WarrantListingResponse>(warrantUrl(`/${id}/listings`), {
      method: 'POST',
      body: request,
    }),
};
