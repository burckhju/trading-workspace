export type Uuid = string;
export type IsoDateTime = string;

export type UnderlyingType = 'STOCK';
export type LifecycleStatus = 'ACTIVE' | 'INACTIVE';
export type QualityStatus = 'DRAFT' | 'COMPLETE' | 'VERIFIED';

export interface ApiErrorDetail {
  field: string | null;
  message: string;
  context: Record<string, unknown> | null;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details: ApiErrorDetail[];
  timestamp: IsoDateTime;
}

export interface CreateListingRequest {
  trading_venue_id: Uuid;
  ticker: string;
  currency_code: string;
  is_primary?: boolean;
}

export interface CreateUnderlyingRequest {
  name: string;
  type?: UnderlyingType;
  isin?: string | null;
  wkn?: string | null;
  primary_listing: CreateListingRequest;
}

export interface UpdateUnderlyingRequest {
  version: number;
  name?: string | null;
  isin?: string | null;
  wkn?: string | null;
}

export interface VersionRequest {
  version: number;
}

export interface AddListingRequest {
  trading_venue_id: Uuid;
  ticker: string;
  currency_code: string;
  is_primary?: boolean;
}

export interface UpdateListingRequest {
  version: number;
  trading_venue_id?: Uuid;
  ticker?: string;
  currency_code?: string;
  lifecycle_status?: LifecycleStatus;
}

export interface PrimaryListingSummaryResponse {
  id: Uuid;
  ticker: string;
  trading_venue_id: Uuid;
  trading_venue_mic: string;
  trading_venue_name: string;
  currency_code: string;
}

export interface ListingResponse {
  id: Uuid;
  underlying_id: Uuid;
  trading_venue_id: Uuid;
  trading_venue_mic: string | null;
  trading_venue_name: string | null;
  ticker: string;
  currency_code: string;
  lifecycle_status: LifecycleStatus;
  is_primary: boolean;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface UnderlyingSummaryResponse {
  id: Uuid;
  type: UnderlyingType;
  name: string;
  isin: string | null;
  wkn: string | null;
  lifecycle_status: LifecycleStatus;
  quality_status: QualityStatus;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  primary_listing: PrimaryListingSummaryResponse | null;
}

export interface UnderlyingDetailResponse extends UnderlyingSummaryResponse {
  listings: ListingResponse[];
}

export interface UnderlyingSearchResponse {
  items: UnderlyingSummaryResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface TradingVenueResponse {
  id: Uuid;
  mic: string;
  name: string;
  country_code: string;
  timezone: string;
  reference_version: string;
}

export interface TradingVenueAdminResponse extends TradingVenueResponse {
  is_active: boolean;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface CreateTradingVenueRequest {
  mic: string;
  name: string;
  country_code: string;
  timezone: string;
}

export interface UpdateTradingVenueRequest {
  expected_version: number;
  name?: string;
  country_code?: string;
  timezone?: string;
}

export interface IssuerResponse {
  id: Uuid;
  legal_name: string;
  display_name: string;
  country_code: string | null;
  lei: string | null;
}

export interface IssuerAdminResponse extends IssuerResponse {
  is_active: boolean;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface CreateIssuerRequest {
  legal_name: string;
  display_name: string;
  country_code?: string | null;
  lei?: string | null;
}

export interface UpdateIssuerRequest {
  expected_version: number;
  legal_name?: string;
  display_name?: string;
  country_code?: string | null;
  lei?: string | null;
}

export interface IssuerVersionRequest {
  expected_version: number;
}

export interface IssuerListResponse {
  items: IssuerResponse[];
}

export interface IssuerAdminListResponse {
  items: IssuerAdminResponse[];
}

export interface CurrencyResponse {
  code: string;
  name: string;
  minor_unit: number;
  reference_version: string;
}

export interface TradingVenueListResponse {
  items: TradingVenueResponse[];
}

export interface TradingVenueAdminListResponse {
  items: TradingVenueAdminResponse[];
}

export interface CurrencyListResponse {
  items: CurrencyResponse[];
}

export interface SearchUnderlyingsParameters {
  query?: string;
  lifecycleStatus?: LifecycleStatus;
  tradingVenueId?: Uuid;
  currencyCode?: string;
  offset?: number;
  limit?: number;
}

export interface AuditActorHeaders {
  actorId?: string;
  actorName?: string;
}

export interface AuditEventResponse {
  id: Uuid;
  aggregate_type: string;
  aggregate_id: Uuid;
  occurred_at: IsoDateTime;
  actor_display_name: string;
  change_type: string;
  version_before: number | null;
  version_after: number | null;
  field_changes: Record<string, { old: unknown; new: unknown }>;
}

export interface AuditEventListResponse {
  items: AuditEventResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface UnderlyingUsageResponse {
  usage_type: string;
  count: number;
  object_ids: Uuid[];
}

export interface UnderlyingUsageListResponse {
  items: UnderlyingUsageResponse[];
}

export interface PageParameters {
  offset?: number;
  limit?: number;
}
