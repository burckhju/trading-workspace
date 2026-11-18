import type { DeadlineExitListingReport } from '../types/deadlineExitListing';

export function deadlineExitReport(
  overrides: Partial<DeadlineExitListingReport> = {},
): DeadlineExitListingReport {
  return {
    warrant_id: 'synthetic-warrant',
    status: 'MISSING',
    reasons: ['PRODUCT_EXIT_LISTING_MISSING'],
    revision_number: 0,
    selected_listing_id: null,
    selected_venue_mic: null,
    terms_id: 'synthetic-terms',
    recorded_at: null,
    available_listings: [
      {
        listing_id: 'synthetic-listing',
        listing_version: 3,
        venue_version: 2,
        venue_name: 'Synthetischer Handelsplatz',
        venue_mic: 'XSYN',
        quotation_currency_code: 'EUR',
        symbol: 'SYNTHETIC',
      },
    ],
    definition_version: 'product-deadline-exit-choice-v1',
    ...overrides,
  };
}

export function savedDeadlineExitReport(
  overrides: Partial<DeadlineExitListingReport> = {},
): DeadlineExitListingReport {
  return deadlineExitReport({
    status: 'AVAILABLE',
    reasons: [],
    revision_number: 1,
    selected_listing_id: 'synthetic-listing',
    selected_venue_mic: 'XSYN',
    recorded_at: '2026-11-18T15:35:00Z',
    ...overrides,
  });
}
