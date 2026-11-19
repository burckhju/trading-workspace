import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { DeadlineExitListingReport } from '../types/deadlineExitListing';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function version(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
function choice(value: unknown): boolean {
  return (
    object(value) &&
    text(value.listing_id) &&
    version(value.listing_version) &&
    version(value.venue_version) &&
    text(value.venue_name) &&
    text(value.venue_mic) &&
    typeof value.quotation_currency_code === 'string' &&
    /^[A-Z]{3}$/.test(value.quotation_currency_code) &&
    (value.symbol === null || text(value.symbol))
  );
}

export function verifyDeadlineExitListing(
  value: unknown,
  warrantId: string,
): DeadlineExitListingReport {
  if (
    !object(value) ||
    value.warrant_id !== warrantId ||
    value.definition_version !== 'product-deadline-exit-choice-v1' ||
    !['AVAILABLE', 'MISSING', 'UNSUITABLE'].includes(String(value.status)) ||
    !Array.isArray(value.reasons) ||
    !value.reasons.every(text) ||
    !version(value.revision_number) ||
    !text(value.terms_id) ||
    !(value.selected_listing_id === null || text(value.selected_listing_id)) ||
    !(value.selected_venue_mic === null || text(value.selected_venue_mic)) ||
    !(
      value.recorded_at === null ||
      (typeof value.recorded_at === 'string' && Number.isFinite(Date.parse(value.recorded_at)))
    ) ||
    !Array.isArray(value.available_listings) ||
    !value.available_listings.every(choice)
  )
    throw new Error(
      'Der gespeicherte Ausstiegshandelsplatz ist diesem Produkt nicht eindeutig zugeordnet.',
    );
  const report = value as unknown as DeadlineExitListingReport;
  const selected = report.available_listings.find(
    (item) => item.listing_id === report.selected_listing_id,
  );
  if (
    new Set(report.available_listings.map((item) => item.listing_id)).size !==
      report.available_listings.length ||
    (report.status === 'AVAILABLE' &&
      (!selected || selected.venue_mic !== report.selected_venue_mic))
  )
    throw new Error(
      'Der gespeicherte Ausstiegshandelsplatz passt nicht zu den verfügbaren Notierungen.',
    );
  return report;
}

const url = (warrantId: string) =>
  `${environment.apiBaseUrl}/api/v1/warrants/${encodeURIComponent(warrantId)}/deadline-exit-listing`;

export async function readDeadlineExitListing(
  warrantId: string,
  signal?: AbortSignal,
): Promise<DeadlineExitListingReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(url(warrantId), { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für den Ausstiegshandelsplatz dieses Produkts.'
        : error instanceof MarketApiError && error.response.code === 'PRODUCT_EXIT_TERMS_MISSING'
          ? 'Aktuelle Produktbedingungen fehlen. Die Produktstammdaten müssen zuerst geklärt werden.'
          : 'Der gespeicherte Ausstiegshandelsplatz konnte nicht gelesen werden. Die Auswahl ist damit nicht geklärt.',
    );
  }
  return verifyDeadlineExitListing(value, warrantId);
}

export async function saveDeadlineExitListing(
  warrantId: string,
  report: DeadlineExitListingReport,
  listingId: string | null,
): Promise<DeadlineExitListingReport> {
  if (report.warrant_id !== warrantId)
    throw new Error('Die Auswahl gehört zu einem anderen Produkt.');
  const option = report.available_listings.find((item) => item.listing_id === listingId);
  if (listingId !== null && !option)
    throw new Error('Bitte eine der vorhandenen Notierungen auswählen.');
  const result = await requestJson<unknown>(url(warrantId), {
    method: 'PUT',
    body: {
      listing_id: listingId,
      expected_revision_number: report.revision_number,
      expected_terms_id: report.terms_id,
      expected_listing_version: option?.listing_version ?? null,
      expected_venue_version: option?.venue_version ?? null,
    },
  });
  return verifyDeadlineExitListing(result, warrantId);
}
