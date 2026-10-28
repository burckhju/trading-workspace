export interface HistoricalCurrencyListing {
  trading_venue_id: string;
  currency_code: string | null;
}

export interface CurrencyEvidenceFacts {
  kind: 'EXECUTION_DOCUMENT' | 'HISTORICAL_LISTINGS';
  source_reference: string;
  supersedes_evidence_id: string | null;
  revoked: boolean;
  trade_id: string | null;
  execution_id: string | null;
  currency_code: string | null;
  trading_venue_id: string | null;
  valid_from: string | null;
  valid_to: string | null;
  listings: HistoricalCurrencyListing[];
  complete_listing_set: boolean;
}

export interface CurrencyEvidenceRequest extends CurrencyEvidenceFacts {
  request_id: string;
  confirmation: 'CONFIRM_SOURCE_REVIEW';
}

export interface CurrencyEvidence extends CurrencyEvidenceFacts {
  id: string;
  product_id: string;
  workspace_id: string;
  recorded_at: string;
  recorded_by: string;
  request_id: string;
  request_fingerprint: string;
  verification: 'USER_VERIFIED_SOURCE';
}

export interface CurrencyEvidenceHistory {
  history: CurrencyEvidence[];
}
