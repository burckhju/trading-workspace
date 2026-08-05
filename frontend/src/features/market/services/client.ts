import { environment } from '../../../services/environment';
import { requestJson } from './http';
import type {
  AddListingRequest,
  AuditEventListResponse,
  AuditActorHeaders,
  CreateUnderlyingRequest,
  CurrencyListResponse,
  ListingResponse,
  PageParameters,
  SearchUnderlyingsParameters,
  TradingVenueListResponse,
  UnderlyingDetailResponse,
  UnderlyingSearchResponse,
  UnderlyingSummaryResponse,
  UnderlyingUsageListResponse,
  UpdateListingRequest,
  UpdateUnderlyingRequest,
  Uuid,
  VersionRequest,
} from '../types/api';

const API_V1 = '/api/v1';

function apiUrl(path: string): string {
  return `${environment.apiBaseUrl}${API_V1}${path}`;
}

function underlyingsUrl(path = ''): string {
  return apiUrl(`/underlyings${path}`);
}

function appendSearchParameters(url: URL, parameters: SearchUnderlyingsParameters): void {
  if (parameters.query !== undefined) {
    url.searchParams.set('q', parameters.query);
  }
  if (parameters.lifecycleStatus !== undefined) {
    url.searchParams.set('lifecycle_status', parameters.lifecycleStatus);
  }
  if (parameters.tradingVenueId !== undefined) {
    url.searchParams.set('trading_venue_id', parameters.tradingVenueId);
  }
  if (parameters.currencyCode !== undefined) {
    url.searchParams.set('currency_code', parameters.currencyCode);
  }
  if (parameters.offset !== undefined) {
    url.searchParams.set('offset', String(parameters.offset));
  }
  if (parameters.limit !== undefined) {
    url.searchParams.set('limit', String(parameters.limit));
  }
}

export interface MarketApiClient {
  searchUnderlyings: (
    parameters?: SearchUnderlyingsParameters,
    signal?: AbortSignal,
  ) => Promise<UnderlyingSearchResponse>;
  getUnderlying: (id: Uuid, signal?: AbortSignal) => Promise<UnderlyingDetailResponse>;
  getUnderlyingAuditEvents: (
    id: Uuid,
    parameters?: PageParameters,
    signal?: AbortSignal,
  ) => Promise<AuditEventListResponse>;
  getUnderlyingUsages: (id: Uuid, signal?: AbortSignal) => Promise<UnderlyingUsageListResponse>;
  createUnderlying: (
    request: CreateUnderlyingRequest,
    actor?: AuditActorHeaders,
  ) => Promise<UnderlyingSummaryResponse>;
  updateUnderlying: (
    id: Uuid,
    request: UpdateUnderlyingRequest,
    actor?: AuditActorHeaders,
  ) => Promise<UnderlyingSummaryResponse>;
  verifyUnderlying: (
    id: Uuid,
    request: VersionRequest,
    actor?: AuditActorHeaders,
  ) => Promise<UnderlyingSummaryResponse>;
  deactivateUnderlying: (
    id: Uuid,
    request: VersionRequest,
    actor?: AuditActorHeaders,
  ) => Promise<UnderlyingSummaryResponse>;
  reactivateUnderlying: (
    id: Uuid,
    request: VersionRequest,
    actor?: AuditActorHeaders,
  ) => Promise<UnderlyingSummaryResponse>;
  deleteUnderlying: (id: Uuid, version: number, actor?: AuditActorHeaders) => Promise<void>;
  addListing: (
    underlyingId: Uuid,
    request: AddListingRequest,
    actor?: AuditActorHeaders,
  ) => Promise<ListingResponse>;
  updateListing: (
    underlyingId: Uuid,
    listingId: Uuid,
    request: UpdateListingRequest,
    actor?: AuditActorHeaders,
  ) => Promise<ListingResponse>;
  setPrimaryListing: (
    underlyingId: Uuid,
    listingId: Uuid,
    request: VersionRequest,
    actor?: AuditActorHeaders,
  ) => Promise<ListingResponse>;
  listTradingVenues: (signal?: AbortSignal) => Promise<TradingVenueListResponse>;
  listCurrencies: (signal?: AbortSignal) => Promise<CurrencyListResponse>;
}

export const marketApiClient: MarketApiClient = {
  searchUnderlyings: async (parameters = {}, signal) => {
    const url = new URL(underlyingsUrl());
    appendSearchParameters(url, parameters);
    return requestJson<UnderlyingSearchResponse>(url.toString(), { signal });
  },

  getUnderlying: (id, signal) =>
    requestJson<UnderlyingDetailResponse>(underlyingsUrl(`/${id}`), { signal }),

  getUnderlyingAuditEvents: (id, parameters = {}, signal) => {
    const url = new URL(underlyingsUrl(`/${id}/audit-events`));
    if (parameters.offset !== undefined) url.searchParams.set('offset', String(parameters.offset));
    if (parameters.limit !== undefined) url.searchParams.set('limit', String(parameters.limit));
    return requestJson<AuditEventListResponse>(url.toString(), { signal });
  },

  getUnderlyingUsages: (id, signal) =>
    requestJson<UnderlyingUsageListResponse>(underlyingsUrl(`/${id}/usages`), { signal }),

  createUnderlying: (request, actor) =>
    requestJson<UnderlyingSummaryResponse>(underlyingsUrl(), {
      method: 'POST',
      body: request,
      actor,
    }),

  updateUnderlying: (id, request, actor) =>
    requestJson<UnderlyingSummaryResponse>(underlyingsUrl(`/${id}`), {
      method: 'PATCH',
      body: request,
      actor,
    }),

  verifyUnderlying: (id, request, actor) =>
    requestJson<UnderlyingSummaryResponse>(underlyingsUrl(`/${id}/verify`), {
      method: 'POST',
      body: request,
      actor,
    }),

  deactivateUnderlying: (id, request, actor) =>
    requestJson<UnderlyingSummaryResponse>(underlyingsUrl(`/${id}/deactivate`), {
      method: 'POST',
      body: request,
      actor,
    }),

  reactivateUnderlying: (id, request, actor) =>
    requestJson<UnderlyingSummaryResponse>(underlyingsUrl(`/${id}/reactivate`), {
      method: 'POST',
      body: request,
      actor,
    }),

  deleteUnderlying: async (id, version, actor) => {
    const url = new URL(underlyingsUrl(`/${id}`));
    url.searchParams.set('version', String(version));
    await requestJson<void>(url.toString(), { method: 'DELETE', actor });
  },

  addListing: (underlyingId, request, actor) =>
    requestJson<ListingResponse>(underlyingsUrl(`/${underlyingId}/listings`), {
      method: 'POST',
      body: request,
      actor,
    }),

  updateListing: (underlyingId, listingId, request, actor) =>
    requestJson<ListingResponse>(underlyingsUrl(`/${underlyingId}/listings/${listingId}`), {
      method: 'PATCH',
      body: request,
      actor,
    }),

  setPrimaryListing: (underlyingId, listingId, request, actor) =>
    requestJson<ListingResponse>(underlyingsUrl(`/${underlyingId}/primary-listing/${listingId}`), {
      method: 'PUT',
      body: request,
      actor,
    }),

  listTradingVenues: (signal) =>
    requestJson<TradingVenueListResponse>(apiUrl('/market-reference-data/trading-venues'), {
      signal,
    }),

  listCurrencies: (signal) =>
    requestJson<CurrencyListResponse>(apiUrl('/market-reference-data/currencies'), { signal }),
};
