import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type {
  HebeltraderTarget,
  HebeltraderTargetAssessmentRequest,
  HebeltraderTargetsReport,
} from '../hebeltraderTargets';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function nullableText(value: unknown): boolean {
  return value === null || text(value);
}

function strings(value: unknown): boolean {
  return Array.isArray(value) && value.every(text);
}

function count(value: unknown): boolean {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

function quantity(value: unknown): boolean {
  return value === null || count(value);
}

function member(value: unknown, allowed: readonly string[]): boolean {
  return typeof value === 'string' && allowed.includes(value);
}

function price(value: unknown): boolean {
  return (
    typeof value === 'string' &&
    /^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value) &&
    Number.isFinite(Number(value)) &&
    Number(value) > 0
  );
}

function currency(value: unknown): boolean {
  return value === null || (typeof value === 'string' && /^[A-Z]{3}$/.test(value));
}

function evidence(value: unknown): boolean {
  return (
    value === null ||
    (object(value) &&
      value.time_precision === 'DATE_ONLY' &&
      text(value.trading_date) &&
      /^\d{4}-\d{2}-\d{2}$/.test(value.trading_date) &&
      price(value.high) &&
      [
        'interval_start',
        'interval_end',
        'source_row_id',
        'source_fingerprint',
        'provider',
        'provider_symbol',
        'listing_id',
        'detected_at',
      ].every((key) => text(value[key])))
  );
}

function target(value: unknown): value is HebeltraderTarget {
  return (
    object(value) &&
    member(value.target, ['Z1', 'Z2']) &&
    member(value.status, ['PROVEN', 'NOT_PROVEN', 'NOT_ASSESSABLE', 'REVIEW_REQUIRED']) &&
    (value.threshold === null || price(value.threshold)) &&
    currency(value.currency) &&
    nullableText(value.event_id) &&
    nullableText(value.proof_source_version_id) &&
    nullableText(value.proof_scale_reference) &&
    text(value.detail) &&
    strings(value.reasons) &&
    evidence(value.evidence) &&
    (value.evidence === null ||
      (text(value.proof_source_version_id) && text(value.proof_scale_reference))) &&
    (value.status !== 'PROVEN' ||
      (text(value.event_id) &&
        value.evidence !== null &&
        value.threshold !== null &&
        value.currency !== null))
  );
}

function assessment(value: unknown): boolean {
  if (value === null) return true;
  if (!object(value) || !object(value.orientation) || !object(value.protection_basis)) return false;
  const orientation = value.orientation;
  const protection = value.protection_basis;
  const statuses = ['AVAILABLE', 'NOT_ASSESSABLE', 'NOT_APPLICABLE'];
  return (
    ['id', 'recorded_at', 'basis_id'].every((key) => text(value[key])) &&
    nullableText(value.source_version_id) &&
    nullableText(value.previous_assessment_id) &&
    Array.isArray(value.targets) &&
    value.targets.length === 2 &&
    value.targets.every(target) &&
    new Set(value.targets.map((row) => row.target)).size === 2 &&
    member(orientation.status, statuses) &&
    quantity(orientation.original_quantity) &&
    quantity(orientation.assigned_sold_quantity) &&
    orientation.proportion === '0.5' &&
    text(orientation.detail) &&
    member(protection.status, statuses) &&
    (protection.personal_underlying_entry === null ||
      price(protection.personal_underlying_entry)) &&
    currency(protection.currency) &&
    text(protection.detail)
  );
}

function verified(value: unknown, tradeId: string, positionId: string): HebeltraderTargetsReport {
  if (
    !object(value) ||
    value.trade_id !== tradeId ||
    value.position_id !== positionId ||
    value.definition_version !== 'hebeltrader-targets-v1' ||
    value.baseline_id !== 'HEBELTRADER_CONFIRMED_BASELINE' ||
    value.baseline_version !== '1.0.0' ||
    value.implementation_status !== 'F207_2_TARGET_HISTORY_ONLY' ||
    value.operation_status !== 'NOT_ACTIVATED' ||
    !text(value.current_basis_id) ||
    !member(value.currentness, ['CURRENT', 'CHANGED_INPUTS', 'NO_ASSESSMENT']) ||
    !member(value.position_state, ['OPEN', 'CLOSED', 'CANCELLED']) ||
    !text(value.read_started_at) ||
    !text(value.read_completed_at) ||
    !count(value.assessment_count) ||
    !object(value.inputs) ||
    !nullableText(value.inputs.source_version_id) ||
    !nullableText(value.inputs.source_scale_reference) ||
    !text(value.inputs.price_history_fingerprint) ||
    !nullableText(value.inputs.listing_binding_fingerprint) ||
    typeof value.inputs.qualification_reusable !== 'boolean' ||
    !count(value.inputs.available_price_rows) ||
    !strings(value.inputs.issues) ||
    !assessment(value.latest_assessment) ||
    (value.currentness === 'NO_ASSESSMENT') !== (value.latest_assessment === null) ||
    (value.assessment_count === 0) !== (value.latest_assessment === null)
  ) {
    throw new Error(
      'Der Prüfstand lässt sich dieser Position und dem Zielereignisvertrag nicht sicher zuordnen.',
    );
  }
  return value as unknown as HebeltraderTargetsReport;
}

function baseUrl(tradeId: string): string {
  return `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/hebeltrader-targets`;
}

export async function readHebeltraderTargets(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<HebeltraderTargetsReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(
      `${baseUrl(tradeId)}?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für diese Zielhistorie.'
        : 'Die Zielhistorie konnte nicht gelesen werden. Daraus folgt keine Entwarnung.',
    );
  }
  return verified(value, tradeId, positionId);
}

export async function assessHebeltraderTargets(
  tradeId: string,
  payload: HebeltraderTargetAssessmentRequest,
  signal?: AbortSignal,
): Promise<HebeltraderTargetsReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(`${baseUrl(tradeId)}/assessments`, {
      method: 'POST',
      body: payload,
      signal,
    });
  } catch (error) {
    throw new Error(
      error instanceof MarketApiError && error.status === 409
        ? 'Die Beleggrundlage hat sich geändert. Den gespeicherten Prüfstand erneut lesen.'
        : error instanceof MarketApiError && error.status === 403
          ? 'Keine Berechtigung für diese Prüfung. Den gespeicherten Prüfstand erneut lesen.'
          : 'Der Ausgang der Prüfung konnte nicht bestätigt werden. Den gespeicherten Prüfstand erneut lesen; die Prüfung wird nicht automatisch wiederholt.',
    );
  }
  return verified(value, tradeId, payload.position_id);
}
