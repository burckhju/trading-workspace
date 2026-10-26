import type { ChartIdentity } from '../../analysis/types/charts';
import type { ProviderMapping } from './topDownAdminClient';

/** Backend normalization, used only to suppress a destructive, unchanged PUT. */
export function normalizeMappingInput(value: string): string {
  return value.trim().toUpperCase();
}

export function mappingInputsChanged(
  mapping: ProviderMapping | null,
  symbol: string,
  exchange: string,
): boolean {
  return (
    normalizeMappingInput(symbol) !== normalizeMappingInput(mapping?.provider_symbol ?? '') ||
    normalizeMappingInput(exchange) !== normalizeMappingInput(mapping?.provider_exchange_code ?? '')
  );
}

function requireMappingDetails(mapping: ProviderMapping): ProviderMapping {
  if (
    !mapping.id ||
    mapping.provider !== 'EODHD' ||
    !Number.isSafeInteger(mapping.version) ||
    mapping.version < 1 ||
    !mapping.provider_symbol?.trim() ||
    !mapping.provider_exchange_code?.trim() ||
    !['ACTIVE', 'DISABLED', 'INVALID'].includes(mapping.status)
  ) {
    throw new Error('Der gelesene Mappingdatensatz ist unvollständig. Bitte erneut laden.');
  }
  return mapping;
}

/** Listing administration may never select an instrument-only or other-provider mapping. */
export function resolveListingMapping(
  mappings: ProviderMapping[],
  listingId: string,
  mappingId?: string | null,
): ProviderMapping | null {
  if (!listingId) throw new Error('Für das Provider-Mapping fehlt die bestätigte Notierung.');
  const matches = mappings.filter(
    (mapping) => mapping.listing_id === listingId && mapping.provider === 'EODHD',
  );
  if (matches.length > 1)
    throw new Error('Mehrdeutige EODHD-Mappings für diese Notierung. Schreiben ist gesperrt.');
  const mapping = matches[0] ?? null;
  if (mapping && mappings.filter((item) => item.id === mapping.id).length !== 1)
    throw new Error('Die Mapping-ID ist im gelesenen Bestand nicht eindeutig.');
  if (mappingId) {
    const specified = mappings.filter((item) => item.id === mappingId);
    if (specified.length !== 1 || mapping?.id !== mappingId)
      throw new Error('Die Mapping-ID gehört nicht eindeutig zu dieser Notierung und EODHD.');
  }
  return mapping ? requireMappingDetails(mapping) : null;
}

/** Match the catalogue chain against the full DTO; never split provider_identity text. */
export function resolveReferenceMapping(
  mappings: ProviderMapping[],
  identity: ChartIdentity,
  mappingId?: string | null,
): ProviderMapping | null {
  if (!identity.reference_id || identity.listing_id !== null || identity.underlying_id !== null)
    throw new Error('Der Indexkontext besitzt keine eindeutige listingfreie Referenzidentität.');
  if (mappingId && mappingId !== identity.mapping_id)
    throw new Error('Die Mapping-ID widerspricht dem aktuellen Referenzkatalog.');
  if (!identity.instrument_id) {
    if (identity.mapping_id || identity.mapping_version !== null)
      throw new Error('Dem Referenz-Mapping fehlt die belegte Instrumentidentität.');
    return null;
  }
  const matches = mappings.filter(
    (mapping) =>
      mapping.market_data_instrument_id === identity.instrument_id && mapping.provider === 'EODHD',
  );
  if (matches.length > 1) throw new Error('Mehrdeutige EODHD-Mappings für das Referenzinstrument.');
  const mapping = matches[0] ?? null;
  if (!mapping) {
    if (identity.mapping_id || identity.mapping_version !== null)
      throw new Error(
        'Das Mapping aus dem Referenzkatalog fehlt im maßgeblichen Mappingdatensatz.',
      );
    return null;
  }
  if (
    mapping.listing_id !== null ||
    mapping.id !== identity.mapping_id ||
    mapping.version !== identity.mapping_version ||
    mappings.filter((item) => item.id === mapping.id).length !== 1
  ) {
    throw new Error('Referenz, Instrument, Mapping und Revision stimmen nicht überein. Neu laden.');
  }
  return requireMappingDetails(mapping);
}

/** A read-before-write check is deliberately not described as atomic concurrency control. */
export function sameMappingRevision(
  shown: ProviderMapping | null,
  fresh: ProviderMapping | null,
): boolean {
  if (shown === null || fresh === null) return shown === fresh;
  return (
    shown.id === fresh.id &&
    shown.workspace_id === fresh.workspace_id &&
    shown.listing_id === fresh.listing_id &&
    shown.market_data_instrument_id === fresh.market_data_instrument_id &&
    shown.provider === fresh.provider &&
    shown.version === fresh.version &&
    shown.provider_symbol === fresh.provider_symbol &&
    shown.provider_exchange_code === fresh.provider_exchange_code &&
    shown.status === fresh.status &&
    shown.validated_at === fresh.validated_at &&
    shown.validation_message === fresh.validation_message &&
    shown.updated_at === fresh.updated_at
  );
}

export class MappingRevisionConflict extends Error {
  readonly current: ProviderMapping | null;

  constructor(current: ProviderMapping | null) {
    super(
      'Das Mapping wurde inzwischen verändert. Den neuen Stand vor einer Aktion erneut prüfen.',
    );
    this.name = 'MappingRevisionConflict';
    this.current = current;
  }
}

export function requireCurrentMapping(
  shown: ProviderMapping | null,
  fresh: ProviderMapping | null,
): void {
  if (!sameMappingRevision(shown, fresh)) throw new MappingRevisionConflict(fresh);
}

export function referenceBasisForMapping(
  identity: ChartIdentity | null,
  mapping: ProviderMapping | null,
): { returnBasis: string; source: string | null } {
  if (
    !identity?.reference_id ||
    identity.listing_id !== null ||
    !identity.instrument_id ||
    !mapping ||
    mapping.listing_id !== null ||
    mapping.provider !== 'EODHD' ||
    identity.instrument_id !== mapping.market_data_instrument_id ||
    identity.mapping_id !== mapping.id ||
    identity.mapping_version !== mapping.version
  ) {
    return { returnBasis: 'UNKNOWN', source: null };
  }
  return { returnBasis: identity.return_basis, source: identity.basis_source };
}
