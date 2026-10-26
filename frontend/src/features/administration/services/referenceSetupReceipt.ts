import { MarketTransportError } from '../../market/services/http';
import { normalizeMappingInput } from './referenceMapping';
import type { SetupDraft, SetupSelection, SetupSnapshot } from './referenceSetup';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown): value is string {
  return typeof value === 'string' && Boolean(value.trim());
}

function timestamp(value: unknown): value is string {
  return text(value) && Number.isFinite(Date.parse(value));
}

function count(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

function requireReceipt(condition: boolean): asserts condition {
  if (!condition) {
    throw new MarketTransportError(
      'Die Serverantwort belegt diesen Schreibauftrag nicht eindeutig. Abschluss unbekannt; nur den aktuellen Zustand erneut lesen.',
    );
  }
}

function validateMappingReceipt(
  selection: SetupSelection,
  snapshot: SetupSnapshot,
  draft: SetupDraft,
  result: Record<string, unknown>,
) {
  const shown = snapshot.mapping;
  const direct = selection.action.startsWith('reference');
  const saving = selection.action.endsWith('Mapping');
  requireReceipt(
    text(result.id) &&
      text(result.workspace_id) &&
      result.provider === 'EODHD' &&
      text(result.provider_symbol) &&
      text(result.provider_exchange_code) &&
      count(result.version) &&
      result.version > (shown?.version ?? 0) &&
      (result.validation_message === null || typeof result.validation_message === 'string'),
  );
  if (shown) {
    requireReceipt(result.id === shown.id && result.workspace_id === shown.workspace_id);
    if (shown.market_data_instrument_id) {
      requireReceipt(result.market_data_instrument_id === shown.market_data_instrument_id);
    }
  }
  if (selection.mappingId) requireReceipt(result.id === selection.mappingId);
  if (direct) {
    requireReceipt(result.listing_id === null && text(result.market_data_instrument_id));
    if (snapshot.identity?.instrument_id) {
      requireReceipt(result.market_data_instrument_id === snapshot.identity.instrument_id);
    }
  } else {
    requireReceipt(
      Boolean(snapshot.listing) &&
        result.listing_id === snapshot.listing?.id &&
        (result.market_data_instrument_id === null || text(result.market_data_instrument_id)),
    );
  }
  if (saving) {
    requireReceipt(
      result.provider_symbol === normalizeMappingInput(draft.symbol) &&
        result.provider_exchange_code === normalizeMappingInput(draft.exchange) &&
        result.status === 'DISABLED' &&
        result.validated_at === null,
    );
  } else {
    requireReceipt(
      Boolean(shown) &&
        result.provider_symbol === shown?.provider_symbol &&
        result.provider_exchange_code === shown?.provider_exchange_code &&
        ['ACTIVE', 'INVALID'].includes(String(result.status)) &&
        timestamp(result.validated_at),
    );
  }
}

/** Check only fields the actual write DTO returns; a later matching GET is not a receipt. */
export function validateSetupReceipt(
  selection: SetupSelection,
  snapshot: SetupSnapshot,
  draft: SetupDraft,
  candidate: boolean,
  result: unknown,
): void {
  const action = selection.action;
  if (action === 'bootstrap') {
    requireReceipt(Array.isArray(result));
    for (const code of ['DAX', 'SP500', 'NASDAQ100']) {
      const matches = result.filter((item: unknown) => object(item) && item.code === code);
      requireReceipt(matches.length === 1);
      const value: unknown = matches[0];
      requireReceipt(object(value) && text(value.id) && text(value.name));
    }
    return;
  }
  requireReceipt(object(result));
  if (action.endsWith('Mapping') || action.endsWith('Validate')) {
    validateMappingReceipt(selection, snapshot, draft, result);
    return;
  }
  if (action.endsWith('Import')) {
    requireReceipt(
      result.mapping_id === snapshot.mapping?.id &&
        result.start_date === draft.start &&
        result.end_date === draft.end &&
        count(result.inserted) &&
        count(result.updated) &&
        count(result.unchanged),
    );
    if (action === 'referenceImport') {
      requireReceipt(
        result.market_reference_id === selection.referenceId &&
          result.market_data_instrument_id === snapshot.mapping?.market_data_instrument_id &&
          text(result.currency),
      );
    } else {
      requireReceipt(
        result.listing_id === snapshot.listing?.id &&
          result.workspace_id === snapshot.mapping?.workspace_id &&
          result.provider === 'EODHD' &&
          count(result.processed) &&
          result.processed === result.inserted + result.updated + result.unchanged,
      );
    }
    return;
  }
  requireReceipt(text(result.id));
  if (action === 'basis') {
    requireReceipt(result.return_basis === draft.basis);
    return;
  }
  if (action === 'sector' || action === 'reference') {
    requireReceipt(
      result.code === draft.code.trim().toUpperCase() &&
        result.name === draft.name.trim() &&
        result.active === true &&
        timestamp(result.created_at),
    );
    if (action === 'sector') {
      requireReceipt(
        result.classification_system === draft.system.trim() &&
          result.classification_version === draft.version.trim(),
      );
    } else {
      requireReceipt(
        result.region === draft.region.trim().toUpperCase() &&
          result.reference_version === draft.version.trim() &&
          result.reference_type === 'SECTOR_INDEX' &&
          result.role === 'SECTOR_REFERENCE',
      );
    }
    return;
  }
  requireReceipt(
    result.valid_from === draft.start &&
      result.valid_to === null &&
      result.source === (candidate ? 'MANUAL_ADMIN' : 'CHART_SETUP') &&
      result.quality_status === 'GOOD' &&
      timestamp(result.created_at),
  );
}
