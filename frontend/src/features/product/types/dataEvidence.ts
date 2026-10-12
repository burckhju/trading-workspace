export interface ValuationFacts {
  product_type: 'VANILLA_WARRANT' | 'OTHER_STRUCTURED' | null;
  exercise_style: 'EUROPEAN' | 'AMERICAN' | 'OTHER' | null;
  quanto: boolean | null;
  ratio_convention: 'UNDERLYING_UNITS_PER_WARRANT' | null;
  expiry_at: string | null;
  document_reference: string;
  source_url: string | null;
  reviewed_at: string;
  note: string;
}
export interface ValuationEvidence {
  id: string;
  terms_id: string;
  revision: number;
  recorded_at: string;
  actor_id: string;
  identity?: { isin: string | null; wkn: string | null; issuer_id: string; underlying_id: string };
  origin: 'MANUAL_DOCUMENT_REVIEW';
  facts: ValuationFacts;
}
export interface ValuationEvidenceView {
  revision: number;
  current: ValuationEvidence | null;
  history: ValuationEvidence[];
  status: 'CURRENT' | 'MISSING' | 'IDENTITY_OR_TERMS_CHANGED';
}
export interface QuoteHistoryReport {
  warrant_id: string;
  window_start: string;
  window_end: string;
  collection_started_at: string | null;
  item_limit: number;
  segments: Array<{
    provider: string;
    identity_key: string;
    isin: string;
    sampled_slots: number;
    distinct_quote_evidence: number;
    observed_utc_days: number;
    first_capture_at: string;
    last_capture_at: string;
    statuses: Record<string, number>;
  }>;
  items: Array<{
    id: string;
    provider: string;
    identity_key: string;
    isin: string;
    captured_at: string;
    slot_at: string;
    status: string;
    reason: string | null;
    retrieved_at: string | null;
    cache_status: string | null;
    quote: {
      bid: string | null;
      ask: string | null;
      reference_price: string | null;
      reference_price_type: string | null;
      observed_at: string | null;
      currency: string;
      source_mode: string | null;
    } | null;
  }>;
}
