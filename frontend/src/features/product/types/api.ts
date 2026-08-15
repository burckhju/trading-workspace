export type Uuid = string;
export type IsoDateTime = string;
export type WarrantLifecycle = 'ACTIVE' | 'INACTIVE';
export type ProductFamily = 'WARRANT';
export type OptionDirection = 'CALL' | 'PUT';

export interface WarrantResponse {
  id: Uuid;
  workspace_id: Uuid;
  issuer_id: Uuid;
  underlying_id: Uuid;
  product_family: ProductFamily;
  display_name: string;
  isin: string | null;
  wkn: string | null;
  lifecycle_status: WarrantLifecycle;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface WarrantTermsResponse {
  id: Uuid;
  warrant_id: Uuid;
  version_no: number;
  effective_from: IsoDateTime;
  effective_to: IsoDateTime | null;
  option_direction: OptionDirection;
  strike: string;
  maturity_date: string;
  ratio: string;
  created_at: IsoDateTime;
}

export interface WarrantListingResponse {
  id: Uuid;
  workspace_id: Uuid;
  warrant_id: Uuid;
  trading_venue_id: Uuid;
  symbol: string;
  quotation_currency_code: string;
  lifecycle_status: WarrantLifecycle;
  version: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface CreateWarrantRequest {
  issuer_id: Uuid;
  underlying_id: Uuid;
  display_name: string;
  isin?: string | null;
  wkn?: string | null;
  option_direction: OptionDirection;
  strike: string;
  maturity_date: string;
  ratio: string;
}

export interface AddWarrantTermsRequest {
  expected_version: number;
  option_direction: OptionDirection;
  strike: string;
  maturity_date: string;
  ratio: string;
}

export interface AddWarrantListingRequest {
  trading_venue_id: Uuid;
  symbol: string;
  quotation_currency_code: string;
}
