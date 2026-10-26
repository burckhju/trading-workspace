import { chartClient } from '../../analysis/services/chartClient';
import { chartSetupClient } from '../../analysis/services/chartSetupClient';
import type {
  ChartCatalog,
  ChartIdentity,
  UnderlyingChartContext,
} from '../../analysis/types/charts';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import type { ReferenceDataContext, SetupAction } from './referenceDataContext';
import {
  mappingInputsChanged,
  resolveListingMapping,
  resolveReferenceMapping,
} from './referenceMapping';
import {
  topDownAdminClient,
  type MarketReference,
  type ProviderMapping,
  type Sector,
  type VenueReconciliation,
} from './topDownAdminClient';

export { validateSetupReceipt } from './referenceSetupReceipt';

export const setupActions: Array<{ value: SetupAction; label: string; group: string }> = [
  {
    value: 'stockMarket',
    label: 'Basiswert einer Marktbenchmark zuordnen',
    group: 'Basiswert / Listing',
  },
  { value: 'stockSector', label: 'Basiswert einem Sektor zuordnen', group: 'Basiswert / Listing' },
  {
    value: 'listingMapping',
    label: 'Aktie / ETF: EODHD-Mapping bearbeiten',
    group: 'Basiswert / Listing',
  },
  { value: 'listingValidate', label: 'Aktie / ETF: Mapping prüfen', group: 'Basiswert / Listing' },
  {
    value: 'listingImport',
    label: 'Aktie / ETF: Historie importieren',
    group: 'Basiswert / Listing',
  },
  { value: 'sectorReference', label: 'Sektor einer Referenz zuordnen', group: 'Sektor' },
  { value: 'proxy', label: 'Referenz einem bestehenden Listing zuordnen', group: 'Referenz' },
  { value: 'referenceMapping', label: 'Index: EODHD-Mapping bearbeiten', group: 'Referenz' },
  { value: 'referenceValidate', label: 'Index: Mapping prüfen', group: 'Referenz' },
  { value: 'basis', label: 'Index: Renditegrundlage bestätigen', group: 'Referenz' },
  { value: 'referenceImport', label: 'Index: Historie importieren', group: 'Referenz' },
  {
    value: 'bootstrap',
    label: 'Marktreferenzen DAX / S&P 500 / Nasdaq 100 anlegen',
    group: 'Stammdaten ergänzen',
  },
  { value: 'sector', label: 'Sektor anlegen', group: 'Stammdaten ergänzen' },
  { value: 'reference', label: 'Sektorreferenz anlegen', group: 'Stammdaten ergänzen' },
];

export type SetupSelection = Pick<
  ReferenceDataContext,
  'action' | 'underlyingId' | 'listingId' | 'referenceId' | 'sectorId' | 'mappingId'
>;
export interface SetupDraft {
  code: string;
  name: string;
  system: string;
  version: string;
  region: string;
  symbol: string;
  exchange: string;
  source: string;
  basis: string;
  start: string;
  end: string;
}
export interface SetupSnapshot {
  catalog: ChartCatalog;
  references: MarketReference[];
  sectors: Sector[];
  underlying: UnderlyingDetailResponse | null;
  listing: ListingResponse | null;
  reference: MarketReference | null;
  sector: Sector | null;
  identity: ChartIdentity | null;
  mapping: ProviderMapping | null;
  venue: VenueReconciliation | null;
  venueError: string;
  chartContext: UnderlyingChartContext | null;
}

/** A local prerequisite failure; no request was sent by executeSetup. */
export class SetupValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SetupValidationError';
  }
}

export const setupToday = () => new Date().toISOString().slice(0, 10);
export const isAssignment = (action: SetupAction) =>
  ['stockMarket', 'stockSector', 'sectorReference', 'proxy'].includes(action);
export const isDirectReference = (action: SetupAction) =>
  ['referenceMapping', 'referenceValidate', 'basis', 'referenceImport'].includes(action);
export const isListingAction = (action: SetupAction) =>
  ['listingMapping', 'listingValidate', 'listingImport'].includes(action);
export const needsUnderlying = (action: SetupAction) =>
  isListingAction(action) || ['stockMarket', 'stockSector', 'proxy'].includes(action);
export const needsReference = (action: SetupAction) =>
  isDirectReference(action) || ['stockMarket', 'sectorReference', 'proxy'].includes(action);
export const needsSector = (action: SetupAction) =>
  ['stockSector', 'sectorReference'].includes(action);
export const needsListing = (action: SetupAction) => isListingAction(action) || action === 'proxy';
export const editsMapping = (action: SetupAction) => action.endsWith('Mapping');
export const importsHistory = (action: SetupAction) => action.endsWith('Import');

export function initialSetupDraft(action: SetupAction, candidate: boolean): SetupDraft {
  const historyStart = new Date();
  historyStart.setUTCDate(historyStart.getUTCDate() - 400);
  return {
    code: '',
    name: '',
    system: '',
    version: '',
    region: 'US',
    symbol: '',
    exchange: '',
    source: '',
    basis: 'PRICE_INDEX',
    start: candidate
      ? isAssignment(action)
        ? setupToday()
        : historyStart.toISOString().slice(0, 10)
      : `${new Date().getUTCFullYear() - 1}-01-01`,
    end: setupToday(),
  };
}

export function selectionForAction(current: SetupSelection, action: SetupAction): SetupSelection {
  return {
    action,
    underlyingId: needsUnderlying(action) ? current.underlyingId : '',
    listingId: needsListing(action) ? current.listingId : '',
    referenceId: needsReference(action) ? current.referenceId : '',
    sectorId: needsSector(action) ? current.sectorId : '',
    mappingId:
      (isListingAction(action) && isListingAction(current.action)) ||
      (isDirectReference(action) && isDirectReference(current.action))
        ? current.mappingId
        : '',
  };
}

function exact<T extends { id: string }>(values: T[], id: string, name: string): T | null {
  if (!id) return null;
  const matches = values.filter((value) => value.id === id);
  if (matches.length !== 1)
    throw new Error(`${name} ist nicht eindeutig vorhanden. Schreiben ist gesperrt.`);
  return matches[0];
}

/** All inputs are stored-data reads. Search/provider discovery never participates. */
export async function readSetupSnapshot(
  selection: SetupSelection,
  signal?: AbortSignal,
): Promise<SetupSnapshot> {
  const asOf = setupToday();
  const [catalog, references, sectors, mappings, underlying] = await Promise.all([
    chartClient.catalog(asOf, signal),
    topDownAdminClient.references(signal),
    topDownAdminClient.sectors(signal),
    isDirectReference(selection.action) || isListingAction(selection.action)
      ? topDownAdminClient.mappings(signal)
      : Promise.resolve([]),
    selection.underlyingId
      ? marketApiClient.getUnderlying(selection.underlyingId, signal)
      : Promise.resolve(null),
  ]);
  if (underlying && underlying.id !== selection.underlyingId)
    throw new Error('Der gelesene Basiswert gehört nicht zum gewählten Kontext.');
  const reference = exact(references, selection.referenceId, 'Die Referenz');
  const sector = exact(sectors, selection.sectorId, 'Der Sektor');
  const primaryListings = underlying?.listings.filter((value) => value.is_primary) ?? [];
  if (!selection.listingId && needsListing(selection.action) && primaryListings.length > 1)
    throw new Error(
      'Mehrere Primary Listings sind belegt. Bitte eine Notierung ausdrücklich auswählen.',
    );
  const listing = selection.listingId
    ? exact(underlying?.listings ?? [], selection.listingId, 'Die Notierung')
    : needsListing(selection.action)
      ? (primaryListings[0] ?? null)
      : null;
  if (listing && listing.underlying_id !== underlying?.id)
    throw new Error('Notierung und Basiswert gehören nicht zusammen.');
  const identities = catalog.references.filter(
    (value) => value.identity.reference_id === selection.referenceId,
  );
  const identity = identities.length === 1 ? identities[0].identity : null;
  if (isDirectReference(selection.action) && selection.referenceId && !identity)
    throw new Error('Die direkte Referenz ist im aktuellen Chartkatalog nicht eindeutig belegt.');
  const mapping =
    isDirectReference(selection.action) && identity
      ? resolveReferenceMapping(mappings, identity, selection.mappingId)
      : isListingAction(selection.action) && listing
        ? resolveListingMapping(mappings, listing.id, selection.mappingId)
        : null;
  const chartContext = underlying
    ? await chartClient.underlying(underlying.id, asOf, signal)
    : null;
  if (chartContext && chartContext.underlying_id !== underlying?.id)
    throw new Error('Der Chart-Lesestand gehört zu einem anderen Basiswert.');
  let venue: VenueReconciliation | null = null;
  let venueError = '';
  if (mapping?.listing_id) {
    try {
      const value = await topDownAdminClient.venueReconciliation(mapping.id, signal);
      if (
        !value ||
        !['MATCHED', 'CONFLICT', 'AMBIGUOUS', 'UNRESOLVED'].includes(value.status) ||
        !Array.isArray(value.evidence_venue_ids) ||
        value.evidence_venue_ids.some((id) => typeof id !== 'string' || !id) ||
        typeof value.explanation !== 'string' ||
        (value.listing_venue_id !== null && value.listing_venue_id !== listing?.trading_venue_id) ||
        (value.status === 'MATCHED' && value.listing_venue_id === null)
      ) {
        throw new Error(
          'Der Handelsplatz-Lesestand passt nicht zur bestätigten Notierung. Bitte erneut lesen.',
        );
      }
      venue = value;
    } catch (reason: unknown) {
      if (signal?.aborted) throw reason;
      venueError = reason instanceof Error ? reason.message : 'Handelsplatzabgleich nicht lesbar.';
    }
  }
  if (signal?.aborted) throw new DOMException('Kontext wurde verlassen.', 'AbortError');
  return {
    catalog,
    references,
    sectors,
    underlying,
    listing,
    reference,
    sector,
    identity,
    mapping,
    venue,
    venueError,
    chartContext,
  };
}

/** Validate selected existing targets, leaving overlap/history rules with the backend owner. */
export function setupProblem(
  selection: SetupSelection,
  snapshot: SetupSnapshot,
  draft: SetupDraft,
): string {
  const action = selection.action;
  if (
    ['sector', 'reference'].includes(action) &&
    (!draft.code.trim() || !draft.name.trim() || !draft.version.trim())
  )
    return 'Code, Name und Version müssen vollständig angegeben werden.';
  if (action === 'sector' && !draft.system.trim())
    return 'Bitte das Klassifikationssystem angeben.';
  if (action === 'reference' && !draft.region.trim()) return 'Bitte die Region angeben.';
  if (needsUnderlying(action) && !snapshot.underlying)
    return 'Bitte einen vorhandenen Basiswert auswählen.';
  if (needsListing(action) && !snapshot.listing)
    return 'Bitte eine bestehende Notierung auswählen.';
  if (needsReference(action) && !snapshot.reference)
    return 'Bitte eine passende Referenz auswählen.';
  if (needsSector(action) && !snapshot.sector) return 'Bitte einen vorhandenen Sektor auswählen.';
  if (
    snapshot.underlying?.lifecycle_status === 'INACTIVE' ||
    snapshot.listing?.lifecycle_status === 'INACTIVE' ||
    snapshot.reference?.active === false ||
    snapshot.sector?.active === false
  )
    return 'Ein gewähltes Objekt ist inaktiv. Die bestehende Stammdatenverwaltung bleibt zuständig.';
  if (action === 'sectorReference' && snapshot.reference?.reference_type !== 'SECTOR_INDEX')
    return 'Dieser Vorgang benötigt eine geeignete Sektorreferenz.';
  if (
    (action.endsWith('Validate') || importsHistory(action) || action === 'basis') &&
    !snapshot.mapping
  )
    return 'Für diesen Kontext fehlt ein eindeutiges EODHD-Mapping.';
  if ((importsHistory(action) || action === 'basis') && snapshot.mapping?.status !== 'ACTIVE')
    return 'Das Mapping muss zuerst ausdrücklich geprüft und aktiviert werden.';
  if (action === 'basis' && snapshot.mapping?.provider_exchange_code !== 'INDX')
    return 'Die Renditegrundlage benötigt ein direktes Indexmapping mit Exchange-Code INDX.';
  if (action === 'basis' && !['PRICE_INDEX', 'TOTAL_RETURN_INDEX'].includes(draft.basis))
    return 'Bitte eine unterstützte Index-Renditegrundlage auswählen.';
  if (action === 'basis' && !isEvidenceUrl(draft.source))
    return 'Bitte eine öffentliche HTTPS-Quellenadresse ohne Zugangsdaten angeben.';
  if (action === 'listingImport' && snapshot.venue?.status !== 'MATCHED')
    return 'Vor dem Import muss der Handelsplatz eindeutig abgeglichen sein.';
  if (isAssignment(action) && !isCalendarDate(draft.start))
    return 'Bitte einen gültigen Gültigkeitsbeginn auswählen.';
  if (
    importsHistory(action) &&
    (!isCalendarDate(draft.start) || !isCalendarDate(draft.end) || draft.end < draft.start)
  )
    return 'Bitte einen gültigen Importzeitraum bestätigen.';
  if (editsMapping(action) && (!draft.symbol.trim() || !draft.exchange.trim()))
    return 'Symbol und Exchange-Code müssen ausdrücklich angegeben werden.';
  return '';
}

function isEvidenceUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && Boolean(url.hostname) && !url.username && !url.password;
  } catch {
    return false;
  }
}

function isCalendarDate(value: string): boolean {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return (
    Number.isFinite(date.getTime()) &&
    date.getUTCFullYear() >= 1 &&
    date.toISOString().slice(0, 10) === value
  );
}

function requireSnapshotContext(selection: SetupSelection, snapshot: SetupSnapshot): void {
  const matches = [
    !needsUnderlying(selection.action) || selection.underlyingId === snapshot.underlying?.id,
    !needsListing(selection.action) ||
      !selection.listingId ||
      selection.listingId === snapshot.listing?.id,
    !needsReference(selection.action) || selection.referenceId === snapshot.reference?.id,
    !needsSector(selection.action) || selection.sectorId === snapshot.sector?.id,
    !(isListingAction(selection.action) || isDirectReference(selection.action)) ||
      !selection.mappingId ||
      selection.mappingId === snapshot.mapping?.id,
  ];
  if (matches.includes(false))
    throw new Error(
      'Der gelesene Stand gehört nicht zum bestätigten Eingabekontext. Bitte erneut laden.',
    );
  if (needsListing(selection.action) && snapshot.listing?.underlying_id !== snapshot.underlying?.id)
    throw new Error('Notierung und Basiswert gehören nicht zusammen.');
  if (isDirectReference(selection.action)) {
    if (!snapshot.identity || snapshot.identity.reference_id !== selection.referenceId)
      throw new Error('Die direkte Referenz ist im aktuellen Chartkatalog nicht eindeutig belegt.');
    resolveReferenceMapping(
      snapshot.mapping ? [snapshot.mapping] : [],
      snapshot.identity,
      selection.mappingId,
    );
  } else if (isListingAction(selection.action) && snapshot.listing) {
    resolveListingMapping(
      snapshot.mapping ? [snapshot.mapping] : [],
      snapshot.listing.id,
      selection.mappingId,
    );
  }
}

export function snapshotReviewKey(snapshot: SetupSnapshot): string {
  return JSON.stringify({
    underlying: snapshot.underlying && [
      snapshot.underlying.id,
      snapshot.underlying.version,
      snapshot.underlying.lifecycle_status,
    ],
    listing: snapshot.listing && [
      snapshot.listing.id,
      snapshot.listing.underlying_id,
      snapshot.listing.version,
      snapshot.listing.lifecycle_status,
    ],
    reference: snapshot.reference,
    sector: snapshot.sector,
    mapping: snapshot.mapping,
    basis: snapshot.identity && [
      snapshot.identity.return_basis,
      snapshot.identity.basis_source,
      snapshot.identity.mapping_id,
      snapshot.identity.mapping_version,
    ],
    venue: snapshot.venue,
  });
}

export async function executeSetup(
  selection: SetupSelection,
  snapshot: SetupSnapshot,
  draft: SetupDraft,
  candidate: boolean,
): Promise<unknown> {
  try {
    const problem = setupProblem(selection, snapshot, draft);
    if (problem) throw new Error(problem);
    requireSnapshotContext(selection, snapshot);
    if (candidate && isAssignment(selection.action) && draft.start !== setupToday())
      throw new Error(
        'Der Tagesbezug des Kandidaten ist inzwischen veraltet. Gültigkeitsbeginn erneut prüfen.',
      );
    if (
      !candidate &&
      isAssignment(selection.action) &&
      selection.action !== 'sectorReference' &&
      !draft.source.trim()
    )
      throw new Error('Bitte den Quellenbeleg der neuen Zuordnung angeben.');
    if (
      editsMapping(selection.action) &&
      !mappingInputsChanged(snapshot.mapping, draft.symbol, draft.exchange)
    )
      throw new Error(
        'Die Mappingwerte sind unverändert. Es wird keine neue Revision gespeichert.',
      );
  } catch (reason: unknown) {
    throw new SetupValidationError(
      reason instanceof Error ? reason.message : 'Eingabekontext ist nicht vollständig geprüft.',
    );
  }
  const evidence = {
    valid_from: draft.start,
    valid_to: null,
    source: candidate ? 'MANUAL_ADMIN' : 'CHART_SETUP',
    ...(selection.action === 'sectorReference'
      ? {}
      : { source_reference: candidate ? 'Candidate live workflow' : draft.source }),
    quality_status: 'GOOD',
  };
  const listingId = snapshot.listing?.id ?? '';
  const mappingId = snapshot.mapping?.id ?? '';
  switch (selection.action) {
    case 'bootstrap':
      return chartSetupClient.write('bootstrap-v1');
    case 'sector':
      return chartSetupClient.write('sectors', {
        code: draft.code,
        name: draft.name,
        classification_system: draft.system,
        classification_version: draft.version,
      });
    case 'reference':
      return chartSetupClient.write('sector-references', {
        code: draft.code,
        name: draft.name,
        region: draft.region,
        reference_version: draft.version,
      });
    case 'stockMarket':
      return chartSetupClient.write(`underlyings/${selection.underlyingId}/benchmark-assignments`, {
        ...evidence,
        market_reference_id: selection.referenceId,
        role: 'BROAD_MARKET',
      });
    case 'stockSector':
      return chartSetupClient.write(`underlyings/${selection.underlyingId}/sector-assignments`, {
        ...evidence,
        sector_id: selection.sectorId,
      });
    case 'sectorReference':
      return chartSetupClient.write(`sectors/${selection.sectorId}/reference-assignments`, {
        ...evidence,
        market_reference_id: selection.referenceId,
      });
    case 'proxy':
      return chartSetupClient.write(
        `market-references/${selection.referenceId}/listing-assignments`,
        { ...evidence, listing_id: listingId },
      );
    case 'listingMapping':
      return topDownAdminClient.createMapping(listingId, draft.symbol, draft.exchange);
    case 'listingValidate':
      return topDownAdminClient.validateMapping(mappingId);
    case 'listingImport':
      return topDownAdminClient.importHistory(listingId, mappingId, draft.start, draft.end);
    case 'referenceMapping':
      return chartSetupClient.write(
        `market-references/${selection.referenceId}/provider-mapping/eodhd`,
        { provider_symbol: draft.symbol, provider_exchange_code: draft.exchange },
        'PUT',
      );
    case 'referenceValidate':
      return chartSetupClient.write(
        `market-references/${selection.referenceId}/provider-mapping/eodhd/validate`,
      );
    case 'referenceImport':
      return chartSetupClient.write(
        `market-references/${selection.referenceId}/daily-prices/import`,
        { start_date: draft.start, end_date: draft.end },
      );
    case 'basis':
      return chartSetupClient.write(`market-references/${selection.referenceId}/series-basis`, {
        mapping_id: mappingId,
        mapping_version: snapshot.mapping?.version,
        return_basis: draft.basis,
        source_url: draft.source,
        confirmed: true,
      });
  }
}
