import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { IndicativeEntryReport } from '../indicativeEntry';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function count(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
function clock(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(
      value,
    ) &&
    !value.endsWith('-00:00') &&
    Number.isFinite(Date.parse(value)) &&
    new Date(value.slice(0, 10)).toISOString().slice(0, 10) === value.slice(0, 10)
  );
}
function decimal(value: unknown): boolean {
  return (
    typeof value === 'string' &&
    value.length <= 100 &&
    /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value)
  );
}
function optionalChoice(value: unknown, choices: string[]): boolean {
  return value == null || (typeof value === 'string' && choices.includes(value));
}
function assessment(value: unknown): boolean {
  return (
    object(value) &&
    text(value.id) &&
    text(value.owner_basis_id) &&
    clock(value.evaluated_at) &&
    clock(value.recorded_at) &&
    clock(value.session_count_at) &&
    (value.session_day_precision == null || text(value.session_day_precision)) &&
    (value.calendar_quality == null || text(value.calendar_quality)) &&
    (value.calendar_verification == null || text(value.calendar_verification)) &&
    ['BELOW_ENTRY', 'AT_OR_ABOVE_ENTRY', 'NOT_REACHED', 'UNAVAILABLE', 'CLOSED'].includes(
      String(value.outcome),
    ) &&
    Array.isArray(value.reasons) &&
    value.reasons.length > 0 &&
    value.reasons.every(text) &&
    optionalChoice(value.rule_version, [
      'indicative-entry-review-v1',
      'indicative-entry-review-v2',
    ]) &&
    optionalChoice(value.evaluation_mode, [
      'SOURCE_BID',
      'DELAYED_SOURCE_BID',
      'INDICATIVE_ISSUER',
    ]) &&
    (value.bid === null || decimal(value.bid)) &&
    decimal(value.gross_entry) &&
    (value.currency === null ||
      (typeof value.currency === 'string' && /^[A-Z]{3}$/.test(value.currency))) &&
    count(value.remaining_quantity) &&
    (value.original_bid_at === null || clock(value.original_bid_at)) &&
    (value.source_quote_at == null || clock(value.source_quote_at)) &&
    (value.received_at === null || clock(value.received_at)) &&
    (value.completed_sessions === null || count(value.completed_sessions)) &&
    (value.review_completed_sessions === null || count(value.review_completed_sessions)) &&
    (value.review_due === null || typeof value.review_due === 'boolean') &&
    optionalChoice(value.source_time_basis, [
      'ORIGINAL_BID_TIME',
      'SHARED_QUOTE_TIME',
      'ORIGINAL_TIME_UNKNOWN',
    ]) &&
    optionalChoice(value.source_freshness, [
      'WITHIN_900_SECONDS',
      'WITHIN_1800_SECONDS',
      'UNKNOWN',
    ]) &&
    optionalChoice(value.product_scale_quality, [
      'DOCUMENTED',
      'CURRENT_UNIT_HISTORY_ASSUMED',
      'UNAVAILABLE',
    ]) &&
    (value.history_continuity_assumed == null ||
      typeof value.history_continuity_assumed === 'boolean') &&
    object(value.source) &&
    Object.values(value.source).every((item) => item === null || typeof item === 'string')
  );
}
function episode(value: unknown): boolean {
  return (
    object(value) &&
    ['id', 'alert_id', 'opening_assessment_id'].every((key) => text(value[key])) &&
    ['ENTRY_LOSS', 'REVIEW_DUE', 'DATA_UNAVAILABLE'].includes(String(value.kind)) &&
    optionalChoice(value.rule_version, [
      'indicative-entry-review-v1',
      'indicative-entry-review-v2',
    ]) &&
    count(value.episode_number) &&
    value.episode_number > 0 &&
    clock(value.opened_at) &&
    (value.closed_at === null
      ? value.closing_assessment_id === null && value.close_reason === null
      : clock(value.closed_at) && text(value.closing_assessment_id) && text(value.close_reason))
  );
}

export function verifyIndicativeEntry(
  value: unknown,
  tradeId: string,
  positionId: string,
): IndicativeEntryReport {
  const invalid = () =>
    new Error(
      'Der gespeicherte indikative Prüfstand ist nicht eindeutig dieser Position und Regelversion zugeordnet.',
    );
  if (
    !object(value) ||
    value.trade_id !== tradeId ||
    value.position_id !== positionId ||
    !(
      (value.scope === 'INDICATIVE_ENTRY_V1' &&
        value.definition_version === 'indicative-entry-review-v1') ||
      (value.scope === 'INDICATIVE_ENTRY_V2' &&
        value.definition_version === 'indicative-entry-review-v2')
    ) ||
    value.qualified_b04 !== false ||
    value.full_baseline_activated !== false ||
    value.read_status !== 'READ_ONLY' ||
    !['NOT_ACTIVATED', 'SCOPE_ENABLED'].includes(String(value.activation_status)) ||
    typeof value.runner_enabled !== 'boolean' ||
    typeof value.notifications_enabled !== 'boolean' ||
    !(
      value.document_readiness == null ||
      (object(value.document_readiness) &&
        text(value.document_readiness.outcome) &&
        clock(value.document_readiness.attempted_at) &&
        clock(value.document_readiness.next_attempt_at) &&
        (value.document_readiness.problems == null ||
          (Array.isArray(value.document_readiness.problems) &&
            value.document_readiness.problems.every(text))))
    ) ||
    !clock(value.read_at) ||
    !count(value.assessment_count) ||
    !count(value.episode_count) ||
    !(value.latest_assessment === null || assessment(value.latest_assessment)) ||
    !Array.isArray(value.active_episodes) ||
    !value.active_episodes.every(episode) ||
    !Array.isArray(value.recent_episodes) ||
    value.recent_episodes.length > 50 ||
    !value.recent_episodes.every(episode)
  )
    throw invalid();
  const report = value as unknown as IndicativeEntryReport;
  if (
    (report.assessment_count === 0) !== (report.latest_assessment === null) ||
    report.episode_count < report.recent_episodes.length ||
    report.episode_count < report.active_episodes.length ||
    report.active_episodes.some((item) => item.closed_at !== null) ||
    new Set(report.active_episodes.map((item) => item.kind)).size !==
      report.active_episodes.length ||
    new Set(report.active_episodes.map((item) => item.id)).size !== report.active_episodes.length ||
    new Set(report.recent_episodes.map((item) => item.id)).size !== report.recent_episodes.length
  )
    throw invalid();
  return report;
}

export async function readIndicativeEntry(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<IndicativeEntryReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(
      `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/indicative-entry?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für den indikativen Prüfstand dieser Position.'
        : 'Der gespeicherte indikative Prüfstand konnte nicht gelesen werden. Offene Hinweise und Datenlage sind damit nicht geklärt.',
    );
  }
  return verifyIndicativeEntry(value, tradeId, positionId);
}
