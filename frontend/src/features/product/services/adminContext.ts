import { warrantApiClient } from './client';
import type { SelectionRepairContext } from './selectionRepairContext';
import type { WarrantListingResponse, WarrantResponse, WarrantTermsResponse } from '../types/api';

export interface WarrantDetailSnapshot {
  warrant: WarrantResponse;
  terms: WarrantTermsResponse[];
  listings: WarrantListingResponse[];
  currentTerms: WarrantTermsResponse | null;
  termsError: string | null;
}

/** The API has separate reads. Pin terms to an unchanged product version across that read window. */
export async function loadWarrantDetail(
  id: string,
  context?: SelectionRepairContext,
  signal?: AbortSignal,
): Promise<WarrantDetailSnapshot> {
  const before = await warrantApiClient.get(id, signal);
  const [terms, listings] = await Promise.all([
    warrantApiClient.terms(id, signal),
    warrantApiClient.listings(id, signal),
  ]);
  const warrant = await warrantApiClient.get(id, signal);
  if (signal?.aborted) throw new DOMException('Abgebrochener Produktabruf', 'AbortError');
  if (
    before.id !== id ||
    warrant.id !== id ||
    (context &&
      (warrant.underlying_id !== context.underlying.id ||
        before.underlying_id !== context.underlying.id ||
        (context.warrantId && id !== context.warrantId)))
  ) {
    throw new Error(
      'Das angeforderte Produkt ist im passenden Basiswertkontext nicht verfügbar. Keine automatische Ersatzauswahl.',
    );
  }
  if (
    !Number.isSafeInteger(warrant.version) ||
    warrant.version < 1 ||
    before.version !== warrant.version
  ) {
    throw new Error(
      'Das Produkt wurde während des Ladens geändert. Bitte Produkt neu laden und prüfen.',
    );
  }
  if (listings.some((item) => item.warrant_id !== id)) {
    throw new Error(
      'Die geladenen Notierungen gehören nicht eindeutig zu diesem Produkt. Bitte neu laden.',
    );
  }
  const open = terms.filter((item) => item.effective_to === null);
  const current = open.length === 1 ? open[0] : null;
  const valid =
    current &&
    terms.every((item) => item.warrant_id === id) &&
    new Set(terms.map((item) => item.id)).size === terms.length &&
    (current.option_direction === 'CALL' || current.option_direction === 'PUT') &&
    typeof current.strike === 'string' &&
    current.strike.trim() !== '' &&
    typeof current.ratio === 'string' &&
    current.ratio.trim() !== '' &&
    Boolean(current.maturity_date) &&
    Boolean(current.id);
  return {
    warrant,
    terms,
    listings,
    currentTerms: valid ? current : null,
    termsError: valid
      ? null
      : 'Aktuelle Produktbedingungen fehlen oder sind widersprüchlich. Änderungen sind gesperrt; bitte Produkt neu laden und den gespeicherten Stand prüfen.',
  };
}
