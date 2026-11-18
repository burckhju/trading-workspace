export interface DeadlineExitListingOption {
  listing_id: string;
  listing_version: number;
  venue_version: number;
  venue_name: string;
  venue_mic: string;
  quotation_currency_code: string;
  symbol: string | null;
}

export interface DeadlineExitListingReport {
  warrant_id: string;
  status: 'AVAILABLE' | 'MISSING' | 'UNSUITABLE';
  reasons: string[];
  revision_number: number;
  selected_listing_id: string | null;
  selected_venue_mic: string | null;
  terms_id: string;
  recorded_at: string | null;
  available_listings: DeadlineExitListingOption[];
  definition_version: 'product-deadline-exit-choice-v1';
}
