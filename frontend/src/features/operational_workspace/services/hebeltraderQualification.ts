import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { TargetQualificationPreview, TargetRequestStatus } from '../hebeltraderQualification';
import {
  isHebeltraderTargetAssessment,
  verifyHebeltraderTargetsReport,
} from './hebeltraderTargets';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function nullableText(value: unknown): boolean {
  return value === null || text(value);
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}
function count(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
function oneOf(value: unknown, values: readonly string[]): boolean {
  return typeof value === 'string' && values.includes(value);
}
function stamp(value: unknown): boolean {
  return (
    text(value) && /T.+(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value))
  );
}
function day(value: unknown): boolean {
  return text(value) && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value));
}
function issues(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.every((item) => object(item) && text(item.code) && text(item.detail))
  );
}
function binding(value: unknown): value is Record<string, string> {
  return (
    object(value) &&
    [
      'history_fingerprint',
      'listing_fingerprint',
      'source_version_id',
      'source_scale_reference',
    ].every((key) => text(value[key]))
  );
}
function qualification(value: unknown): boolean {
  return value === null || (binding(value) && text(value.evidence_reference));
}
function marks(value: unknown, basis: string, instrumentId: unknown): boolean {
  return (
    object(value) &&
    object(value.binding) &&
    value.binding.basis === basis &&
    value.binding.instrument_id === instrumentId &&
    text(value.binding.currency) &&
    value.scale === 'SOURCE_ORIGINAL' &&
    ['reference_price', 'target_1', 'target_2', 'stop_1', 'stop_2'].every((key) => text(value[key]))
  );
}
function source(value: unknown, productId: unknown, underlyingId: unknown): boolean {
  if (value === null) return true;
  return (
    object(value) &&
    value.product_id === productId &&
    value.underlying_id === underlyingId &&
    value.source_name === 'HEBELTRADER' &&
    value.time_precision === 'DATE_ONLY' &&
    count(value.version) &&
    value.version > 0 &&
    day(value.issue_date) &&
    oneOf(value.currentness, ['CURRENT_SOURCE', 'SOURCE_SUPERSEDED']) &&
    nullableText(value.supersedes_version_id) &&
    nullableText(value.external_reference) &&
    [
      'source_version_id',
      'observation_id',
      'filename',
      'content_hash',
      'accepted_by',
      'import_row_id',
      'batch_id',
      'file_id',
    ].every((key) => text(value[key])) &&
    ['observed_at', 'recorded_at', 'imported_at', 'accepted_at'].every((key) =>
      stamp(value[key]),
    ) &&
    marks(value.underlying, 'UNDERLYING', underlyingId) &&
    marks(value.product, 'WARRANT', productId)
  );
}
function listing(value: unknown, workspaceId: unknown, underlyingId: unknown): boolean {
  return (
    value === null ||
    (object(value) &&
      value.workspace_id === workspaceId &&
      value.underlying_id === underlyingId &&
      value.provenance === 'CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED' &&
      ['listing_id', 'trading_venue_id', 'venue_reference_version', 'fingerprint'].every((key) =>
        text(value[key]),
      ) &&
      ['venue_mic', 'timezone', 'currency'].every((key) => typeof value[key] === 'string') &&
      ['listing_recorded_at', 'listing_updated_at', 'venue_recorded_at', 'venue_updated_at'].every(
        (key) => stamp(value[key]),
      ) &&
      count(value.listing_version) &&
      count(value.venue_version))
  );
}
function history(value: unknown, underlyingId: unknown): boolean {
  if (
    !object(value) ||
    !text(value.workspace_id) ||
    value.underlying_id !== underlyingId ||
    !listing(value.binding, value.workspace_id, underlyingId) ||
    !Array.isArray(value.rows) ||
    !count(value.row_limit) ||
    value.row_limit > 5000 ||
    value.rows.length > value.row_limit ||
    !count(value.rows_observed) ||
    !text(value.fingerprint) ||
    !oneOf(value.status, ['AVAILABLE', 'MISSING', 'BLOCKED', 'LIMIT_EXCEEDED']) ||
    !strings(value.reasons) ||
    !day(value.start_date) ||
    !day(value.end_date) ||
    !stamp(value.known_at) ||
    !stamp(value.read_at) ||
    typeof value.stored_range_complete !== 'boolean' ||
    typeof value.intervals_complete !== 'boolean' ||
    value.calendar_coverage !== 'NOT_ASSESSED' ||
    value.qualification_required !== 'HISTORICAL_BINDING_AND_COMPARISON_SCALE'
  )
    return false;
  const listingId = object(value.binding) ? value.binding.listing_id : null;
  return (
    new Set(value.rows.map((row) => (object(row) ? row.source_row_id : null))).size ===
      value.rows.length &&
    value.rows.every(
      (row) =>
        object(row) &&
        row.workspace_id === value.workspace_id &&
        row.listing_id === listingId &&
        ['source_row_id', 'fingerprint', 'open', 'high', 'low', 'close'].every((key) =>
          text(row[key]),
        ) &&
        ['currency', 'provider', 'provider_symbol', 'price_type', 'quality_status'].every(
          (key) => typeof row[key] === 'string',
        ) &&
        ['market_data_instrument_id', 'adjusted_close', 'volume'].every((key) =>
          nullableText(row[key]),
        ) &&
        ['retrieved_at', 'recorded_at', 'last_updated_at'].every((key) => stamp(row[key])) &&
        ['interval_start', 'interval_end', 'source_updated_at'].every(
          (key) => row[key] === null || stamp(row[key]),
        ) &&
        day(row.trading_date) &&
        strings(row.warnings) &&
        strings(row.issues) &&
        oneOf(row.scale_status, [
          'REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION',
          'ADJUSTMENT_INDICATION_PRESENT',
        ]) &&
        row.price_basis === 'UNDERLYING' &&
        row.time_precision === 'DATE_ONLY' &&
        row.interval_basis === 'LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION',
    )
  );
}

export function verifyQualificationPreview(
  value: unknown,
  tradeId: string,
  positionId: string,
): TargetQualificationPreview {
  const invalid = () =>
    new Error(
      'Die Vergleichsbelege lassen sich dem angefragten Positions- und Quellenstand nicht sicher zuordnen.',
    );
  if (
    !object(value) ||
    value.definition_version !== 'hebeltrader-qualification-preview-v1' ||
    value.operation_status !== 'READ_ONLY'
  )
    throw invalid();
  const report = verifyHebeltraderTargetsReport(value.report, tradeId, positionId);
  if (
    !object(value.entry) ||
    !text(value.entry.product_id) ||
    !text(value.entry.underlying_id) ||
    !(
      value.entry.option_direction === null || oneOf(value.entry.option_direction, ['CALL', 'PUT'])
    ) ||
    !(value.entry.opened_at === null || stamp(value.entry.opened_at)) ||
    !(value.entry.opened_on === null || day(value.entry.opened_on)) ||
    !nullableText(value.entry.opening_timezone) ||
    !nullableText(value.entry.evidence_revision_id) ||
    !source(value.source, value.entry.product_id, value.entry.underlying_id) ||
    !nullableText(value.attempted_source_version_id) ||
    !issues(value.source_issues) ||
    !object(value.source_scale) ||
    !oneOf(value.source_scale.review_status, [
      'UNVERIFIED',
      'UNCHANGED_VERIFIED',
      'ADJUSTMENT_REQUIRED',
    ]) ||
    !nullableText(value.source_scale.source_scale_reference) ||
    !nullableText(value.source_scale.review_reference) ||
    value.source_scale.scope !== 'SOURCE_AND_PURCHASE_EVIDENCE_ONLY' ||
    value.source_scale.market_observations_verified !== false ||
    !history(value.history, value.entry.underlying_id) ||
    !object(value.readiness) ||
    !oneOf(value.readiness.status, ['REVIEWABLE', 'BLOCKED', 'NOT_APPLICABLE']) ||
    !issues(value.readiness.issues) ||
    !count(value.readiness.usable_row_count) ||
    !Array.isArray(value.readiness.rows) ||
    !value.readiness.rows.every(
      (row) => object(row) && text(row.source_row_id) && text(row.fingerprint),
    ) ||
    !object(value.qualification) ||
    !oneOf(value.qualification.status, ['MISSING', 'REUSABLE', 'STALE']) ||
    !qualification(value.qualification.value) ||
    !nullableText(value.qualification.contained_in_assessment_id) ||
    !(
      value.qualification.contained_in_recorded_at === null ||
      stamp(value.qualification.contained_in_recorded_at)
    ) ||
    value.qualification.origin !== 'USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION' ||
    !(value.qualification_binding === null || binding(value.qualification_binding)) ||
    !strings(value.notices)
  )
    throw invalid();
  const result = value as unknown as TargetQualificationPreview;
  const rows = result.history.rows;
  const rowRefs = new Set(rows.map((row) => `${row.source_row_id}:${row.fingerprint}`));
  const reviewRefs = result.readiness.rows.map((row) => `${row.source_row_id}:${row.fingerprint}`);
  if (
    report.inputs.price_history_fingerprint !== result.history.fingerprint ||
    report.inputs.available_price_rows !== rows.length ||
    report.inputs.listing_binding_fingerprint !== (result.history.binding?.fingerprint ?? null) ||
    (result.source !== null &&
      (result.source.source_version_id !== result.attempted_source_version_id ||
        result.source.source_version_id !== report.inputs.source_version_id)) ||
    ((result.readiness.status === 'REVIEWABLE' || result.readiness.rows.length > 0) &&
      result.readiness.rows.length !== rows.length) ||
    new Set(reviewRefs).size !== result.readiness.rows.length ||
    !result.readiness.rows.every(
      (row) =>
        rowRefs.has(`${row.source_row_id}:${row.fingerprint}`) &&
        oneOf(row.status, ['SUITABLE_AFTER_CONFIRMATION', 'UNSUITABLE']) &&
        issues(row.issues),
    ) ||
    result.readiness.usable_row_count !==
      result.readiness.rows.filter((row) => row.status === 'SUITABLE_AFTER_CONFIRMATION').length ||
    (result.qualification.status === 'MISSING') !== (result.qualification.value === null) ||
    (result.qualification.status === 'REUSABLE') !== report.inputs.qualification_reusable ||
    (result.qualification.status !== 'MISSING' &&
      (!result.qualification.contained_in_assessment_id ||
        !result.qualification.contained_in_recorded_at))
  )
    throw invalid();
  const bound = result.qualification_binding;
  if (
    bound &&
    (bound.history_fingerprint !== result.history.fingerprint ||
      bound.listing_fingerprint !== result.history.binding?.fingerprint ||
      bound.source_version_id !== result.source?.source_version_id ||
      bound.source_scale_reference !== result.source_scale.source_scale_reference ||
      bound.source_scale_reference !== report.inputs.source_scale_reference)
  )
    throw invalid();
  if (
    result.qualification.status === 'REUSABLE' &&
    (!result.qualification.value ||
      result.qualification.value.history_fingerprint !== result.history.fingerprint ||
      result.qualification.value.listing_fingerprint !== result.history.binding?.fingerprint ||
      result.qualification.value.source_version_id !== result.source?.source_version_id ||
      result.qualification.value.source_scale_reference !==
        result.source_scale.source_scale_reference)
  )
    throw invalid();
  if (
    result.readiness.status === 'REVIEWABLE' &&
    (!bound ||
      !result.source ||
      result.readiness.usable_row_count === 0 ||
      report.position_state !== 'OPEN')
  )
    throw invalid();
  return result;
}

function base(tradeId: string): string {
  return `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/hebeltrader-targets`;
}

async function read(url: string, signal: AbortSignal | undefined, label: string): Promise<unknown> {
  try {
    return await requestJson<unknown>(url, { signal });
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? `Keine Berechtigung für ${label}.`
        : `${label} konnten nicht gelesen werden. Der bisherige Entwurf und ein unbestätigter Schreibausgang bleiben erhalten.`,
    );
  }
}

export async function readQualificationPreview(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<TargetQualificationPreview> {
  return verifyQualificationPreview(
    await read(
      `${base(tradeId)}/qualification-preview?position_id=${encodeURIComponent(positionId)}`,
      signal,
      'die Vergleichsbelege',
    ),
    tradeId,
    positionId,
  );
}

export async function readTargetRequest(
  tradeId: string,
  positionId: string,
  requestId: string,
  signal?: AbortSignal,
): Promise<TargetRequestStatus> {
  const value = await read(
    `${base(tradeId)}/requests/${encodeURIComponent(requestId)}?position_id=${encodeURIComponent(positionId)}`,
    signal,
    'die Vorgangsbelege',
  );
  if (
    !object(value) ||
    value.definition_version !== 'hebeltrader-request-status-v1' ||
    value.operation_status !== 'READ_ONLY' ||
    value.trade_id !== tradeId ||
    value.position_id !== positionId ||
    value.request_id !== requestId ||
    !oneOf(value.status, ['RECORDED', 'UNKNOWN']) ||
    !stamp(value.read_started_at) ||
    !stamp(value.read_completed_at) ||
    !qualification(value.qualification) ||
    !isHebeltraderTargetAssessment(value.assessment) ||
    (value.status === 'RECORDED'
      ? !stamp(value.recorded_at) || value.assessment === null
      : value.recorded_at !== null || value.assessment !== null || value.qualification !== null)
  ) {
    throw new Error(
      'Der Vorgangsbeleg lässt sich dieser Position und dieser Anfrage nicht sicher zuordnen. Der Schreibausgang bleibt unbestätigt.',
    );
  }
  return value as unknown as TargetRequestStatus;
}
