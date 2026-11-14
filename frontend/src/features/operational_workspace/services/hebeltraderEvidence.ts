import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderCoverageItem, HebeltraderEvidenceReport } from '../hebeltraderEvidence';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function nullableString(value: unknown): boolean {
  return value === null || typeof value === 'string';
}

function nullableQuantity(value: unknown): boolean {
  return value === null || (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0);
}

function marks(value: unknown, basis: 'UNDERLYING' | 'WARRANT', instrument: unknown): boolean {
  return (
    object(value) &&
    object(value.binding) &&
    value.binding.basis === basis &&
    value.binding.instrument_id === instrument &&
    typeof value.binding.currency === 'string' &&
    /^[A-Z]{3}$/.test(value.binding.currency) &&
    value.scale === 'SOURCE_ORIGINAL' &&
    ['reference_price', 'target_1', 'target_2', 'stop_1', 'stop_2'].every(
      (key) => typeof value[key] === 'string',
    )
  );
}

function source(value: unknown, productId: unknown, underlyingId: unknown): boolean {
  return (
    value === null ||
    (object(value) &&
      value.product_id === productId &&
      value.underlying_id === underlyingId &&
      value.source_name === 'HEBELTRADER' &&
      value.time_precision === 'DATE_ONLY' &&
      ['CURRENT_SOURCE', 'SOURCE_SUPERSEDED'].includes(String(value.currentness)) &&
      typeof value.version === 'number' &&
      Number.isSafeInteger(value.version) &&
      value.version > 0 &&
      nullableString(value.external_reference) &&
      nullableString(value.supersedes_version_id) &&
      [
        'source_version_id',
        'observation_id',
        'issue_date',
        'observed_at',
        'recorded_at',
        'imported_at',
        'accepted_at',
        'accepted_by',
        'filename',
        'content_hash',
        'import_row_id',
        'batch_id',
        'file_id',
      ].every((key) => typeof value[key] === 'string') &&
      marks(value.underlying, 'UNDERLYING', underlyingId) &&
      marks(value.product, 'WARRANT', productId))
  );
}

function item(value: unknown): value is HebeltraderCoverageItem {
  return (
    object(value) &&
    typeof value.key === 'string' &&
    typeof value.label === 'string' &&
    typeof value.detail === 'string' &&
    ['PRESENT', 'MISSING', 'CONFLICT', 'UNSUITABLE'].includes(String(value.status)) &&
    (value.clarification === null || typeof value.clarification === 'string') &&
    strings(value.affected_rules) &&
    strings(value.references)
  );
}

export async function readHebeltraderEvidence(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<HebeltraderEvidenceReport> {
  let report: unknown;
  try {
    report = await requestJson<unknown>(
      `${environment.apiBaseUrl}/api/v1/trade-position/trades/${encodeURIComponent(tradeId)}/hebeltrader-evidence?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für diese Belegabdeckung.'
        : 'Die Belegabdeckung konnte nicht gelesen werden. Fehlende Belege sind damit nicht festgestellt.',
    );
  }
  if (
    !object(report) ||
    report.definition_version !== 'hebeltrader-evidence-v1' ||
    report.trade_id !== tradeId ||
    report.position_id !== positionId ||
    typeof report.product_id !== 'string' ||
    typeof report.underlying_id !== 'string' ||
    typeof report.basis_id !== 'string' ||
    typeof report.read_started_at !== 'string' ||
    typeof report.read_completed_at !== 'string' ||
    !nullableString(report.evidence_revision_id) ||
    !nullableString(report.evidence_recorded_at) ||
    !nullableQuantity(report.original_z1_quantity) ||
    !nullableQuantity(report.assigned_z1_sold_quantity) ||
    !nullableString(report.personal_underlying_entry) ||
    !nullableString(report.underlying_currency) ||
    !['COMPLETE', 'INCOMPLETE', 'CONFLICTED'].includes(String(report.coverage_status)) ||
    report.implementation_status !== 'F207_4_EVIDENCE_ONLY' ||
    report.operation_status !== 'NOT_ASSESSED' ||
    report.baseline_id !== 'HEBELTRADER_CONFIRMED_BASELINE' ||
    report.baseline_version !== '1.0.0' ||
    !Array.isArray(report.items) ||
    !report.items.every(item) ||
    !source(report.source, report.product_id, report.underlying_id)
  ) {
    throw new Error(
      'Die Antwort lässt sich dieser Position und dem Evidenzvertrag nicht sicher zuordnen.',
    );
  }
  return report as unknown as HebeltraderEvidenceReport;
}
