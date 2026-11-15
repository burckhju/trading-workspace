import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderSessionsReport } from '../hebeltraderSessions';

const maxDays = 3660;
const assurance = 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION';

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
  return Array.isArray(value) && value.every(text);
}

function date(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value
  );
}

function clock(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
    date(value.slice(0, 10)) &&
    Number.isFinite(Date.parse(value))
  );
}

function nullableDate(value: unknown): boolean {
  return value === null || date(value);
}

function nullableClock(value: unknown): boolean {
  return value === null || clock(value);
}

function dates(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.length <= maxDays &&
    value.every(date) &&
    value.every((item, index) => index === 0 || item > value[index - 1])
  );
}

function timezone(value: unknown): boolean {
  if (!text(value)) return false;
  try {
    new Intl.DateTimeFormat('en', { timeZone: value });
    return true;
  } catch {
    return false;
  }
}

function entry(value: unknown): boolean {
  if (value === null) return true;
  // An unsuitable entry remains inspectable with the owner's concrete reasons.
  return (
    object(value) &&
    text(value.execution_id) &&
    nullableText(value.execution_timezone) &&
    ['EXACT', 'DATE_ONLY'].includes(String(value.time_precision)) &&
    nullableClock(value.executed_at) &&
    nullableDate(value.executed_on)
  );
}

function binding(value: unknown, instrument: unknown): boolean {
  return (
    object(value) &&
    value.instrument_kind === 'UNDERLYING' &&
    value.instrument_id === instrument &&
    ['listing_id', 'trading_venue_id', 'market_segment'].every((key) => text(value[key])) &&
    typeof value.venue_mic === 'string' &&
    /^[A-Z0-9]{4}$/.test(value.venue_mic) &&
    timezone(value.timezone) &&
    date(value.valid_from) &&
    date(value.valid_through) &&
    value.valid_from <= value.valid_through
  );
}

function provenance(value: unknown): boolean {
  return (
    object(value) &&
    ['manifest_sha256', 'document_sha256'].every(
      (key) => typeof value[key] === 'string' && /^[a-f0-9]{64}$/.test(value[key]),
    ) &&
    [
      'document_filename',
      'document_media_type',
      'publisher',
      'reference',
      'review_reference',
      'recorded_by',
    ].every((key) => text(value[key])) &&
    nullableClock(value.published_at) &&
    nullableDate(value.published_on) &&
    !(value.published_at !== null && value.published_on !== null) &&
    nullableClock(value.retrieved_at) &&
    clock(value.reviewed_at)
  );
}

function calendar(value: unknown, instrument: unknown): boolean {
  if (
    !object(value) ||
    !text(value.workspace_id) ||
    value.instrument_kind !== 'UNDERLYING' ||
    value.instrument_id !== instrument ||
    !clock(value.known_at) ||
    !clock(value.read_at) ||
    !nullableClock(value.recorded_at) ||
    !['revision_id', 'supersedes_revision_id', 'calendar_id', 'calendar_version'].every((key) =>
      nullableText(value[key]),
    ) ||
    !(
      value.revision_number === null ||
      (typeof value.revision_number === 'number' &&
        Number.isSafeInteger(value.revision_number) &&
        value.revision_number > 0)
    ) ||
    !nullableDate(value.coverage_start) ||
    !nullableDate(value.coverage_end) ||
    !(
      value.evidence_status === null ||
      value.evidence_status === 'ACTIVE' ||
      value.evidence_status === 'WITHDRAWN'
    ) ||
    !(value.binding === null || binding(value.binding, instrument)) ||
    !(value.source === null || provenance(value.source)) ||
    !['AVAILABLE', 'MISSING', 'UNSUITABLE'].includes(String(value.status)) ||
    !strings(value.reasons) ||
    value.verification !== assurance ||
    value.operation_status !== 'READ_ONLY'
  )
    return false;
  return (
    value.status !== 'AVAILABLE' ||
    (text(value.revision_id) &&
      value.revision_number !== null &&
      text(value.calendar_id) &&
      text(value.calendar_version) &&
      value.binding !== null &&
      value.source !== null &&
      date(value.coverage_start) &&
      date(value.coverage_end) &&
      value.coverage_start <= value.coverage_end &&
      value.evidence_status === 'ACTIVE' &&
      value.recorded_at !== null)
  );
}

function day(value: unknown): boolean {
  if (
    !object(value) ||
    !date(value.session_date) ||
    !text(value.source_reference) ||
    !['SESSION', 'CLOSED', 'UNKNOWN'].includes(String(value.status)) ||
    !Array.isArray(value.intervals)
  )
    return false;
  if (value.status !== 'SESSION') return value.intervals.length === 0;
  return (
    value.intervals.length > 0 &&
    value.intervals.length <= 8 &&
    value.intervals.every(
      (interval: unknown) =>
        object(interval) &&
        clock(interval.opens_at) &&
        clock(interval.closes_at) &&
        Date.parse(interval.opens_at) < Date.parse(interval.closes_at),
    )
  );
}

function period(value: unknown): boolean {
  if (
    !object(value) ||
    ![
      'COMPLETE',
      'INCOMPLETE',
      'MISSING',
      'UNSUITABLE',
      'LIMIT_EXCEEDED',
      'NOT_REQUESTED',
    ].includes(String(value.status)) ||
    !nullableDate(value.start_date) ||
    !nullableDate(value.end_date) ||
    !nullableText(value.fingerprint) ||
    !dates(value.missing_dates) ||
    !Array.isArray(value.days) ||
    value.days.length > maxDays ||
    !value.days.every(day)
  )
    return false;
  const rows = value.days as Array<{ session_date: string; status: string }>;
  if (!dates(rows.map((row) => row.session_date))) return false;
  if (value.status === 'NOT_REQUESTED')
    return rows.length === 0 && value.missing_dates.length === 0;
  if (!date(value.start_date) || !date(value.end_date) || value.start_date > value.end_date)
    return false;
  return (
    value.status !== 'COMPLETE' ||
    (value.missing_dates.length === 0 && rows.every((row) => row.status !== 'UNKNOWN'))
  );
}

function count(value: unknown, periodValue: unknown, evaluatedAt: unknown): boolean {
  if (
    !object(value) ||
    !object(periodValue) ||
    !['AVAILABLE', 'NOT_ASSESSABLE', 'NOT_APPLICABLE'].includes(String(value.status)) ||
    !nullableDate(value.anchor_date) ||
    value.evaluated_at !== evaluatedAt ||
    !clock(value.evaluated_at) ||
    value.threshold_sessions !== 20 ||
    !dates(value.completed_session_dates) ||
    !strings(value.reasons) ||
    !nullableDate(value.twentieth_session_date) ||
    !nullableClock(value.twentieth_closes_at)
  )
    return false;
  if (value.status !== 'AVAILABLE')
    return (
      value.completed_sessions === null &&
      value.completed_session_dates.length === 0 &&
      value.threshold_reached === null &&
      value.twentieth_session_date === null &&
      value.twentieth_closes_at === null
    );
  if (
    !date(value.anchor_date) ||
    typeof value.completed_sessions !== 'number' ||
    !Number.isSafeInteger(value.completed_sessions) ||
    value.completed_sessions < 0 ||
    value.completed_sessions !== value.completed_session_dates.length ||
    typeof value.threshold_reached !== 'boolean'
  )
    return false;
  // No calendar arithmetic here: the owner supplies the counted dates and threshold.
  if (
    periodValue.status !== 'COMPLETE' &&
    !(periodValue.status === 'NOT_REQUESTED' && value.completed_sessions === 0)
  )
    return false;
  return value.threshold_reached
    ? date(value.twentieth_session_date) && clock(value.twentieth_closes_at)
    : value.twentieth_session_date === null && value.twentieth_closes_at === null;
}

export function verifyHebeltraderSessions(
  value: unknown,
  tradeId: string,
  positionId: string,
): HebeltraderSessionsReport {
  if (
    !object(value) ||
    value.trade_id !== tradeId ||
    value.position_id !== positionId ||
    !['product_id', 'underlying_id', 'basis_id'].every((key) => text(value[key])) ||
    !['OPEN', 'CLOSED', 'CANCELLED'].includes(String(value.position_state)) ||
    !clock(value.read_started_at) ||
    !clock(value.read_completed_at) ||
    !clock(value.evaluated_at) ||
    !entry(value.entry) ||
    !calendar(value.calendar, value.underlying_id) ||
    !period(value.period) ||
    !count(value.count, value.period, value.evaluated_at) ||
    !Array.isArray(value.issues) ||
    !value.issues.every(
      (issue: unknown) => object(issue) && text(issue.code) && text(issue.detail),
    ) ||
    !strings(value.notices) ||
    value.definition_version !== 'hebeltrader-sessions-v1' ||
    value.baseline_id !== 'HEBELTRADER_CONFIRMED_BASELINE' ||
    value.baseline_version !== '1.0.0' ||
    value.implementation_status !== 'F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY' ||
    value.rule_evaluation_status !== 'B04_B05_B06_B58_NOT_EVALUATED' ||
    value.operation_status !== 'NOT_ACTIVATED' ||
    value.read_status !== 'READ_ONLY'
  ) {
    throw new Error(
      'Die Antwort lässt sich dieser Position und dem Vertrag für Basiswertsitzungen nicht sicher zuordnen.',
    );
  }
  return value as unknown as HebeltraderSessionsReport;
}

export async function readHebeltraderSessions(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<HebeltraderSessionsReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(
      `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/hebeltrader-sessions?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für die Basiswertsitzungen dieser Position.'
        : 'Die Basiswertsitzungen konnten nicht gelesen werden. Fehlende Kalenderbelege sind damit nicht festgestellt.',
    );
  }
  return verifyHebeltraderSessions(value, tradeId, positionId);
}
