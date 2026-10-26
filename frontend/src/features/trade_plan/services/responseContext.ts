import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function strings(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => typeof value[field] === 'string');
}

function nullableStrings(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => value[field] === null || typeof value[field] === 'string');
}

function arrayOf(value: unknown, valid: (item: unknown) => boolean): boolean {
  return Array.isArray(value) && value.every((item: unknown) => valid(item));
}

function entry(value: unknown): boolean {
  return (
    record(value) &&
    typeof value.type === 'string' &&
    ['PRICE', 'PRICE_RANGE', 'TRIGGER'].includes(value.type) &&
    typeof value.currency === 'string' &&
    nullableStrings(value, [
      'price',
      'price_from',
      'price_to',
      'trigger',
      'reference_price',
      'valid_until',
      'rationale',
    ])
  );
}

function candidateProvenance(value: unknown): boolean {
  return (
    value === null ||
    (record(value) &&
      strings(value, [
        'candidate_id',
        'evaluation_id',
        'direction',
        'model_id',
        'model_version',
        'qualification',
        'quality_status',
        'evaluated_at',
      ]) &&
      typeof value.evaluation_version === 'number' &&
      arrayOf(
        value.sources,
        (source) =>
          record(source) &&
          strings(source, ['role', 'source_type', 'source_id', 'model_id', 'model_version']) &&
          typeof source.source_version === 'number',
      ))
  );
}

function approval(value: unknown): boolean {
  return (
    value === null ||
    (record(value) &&
      strings(value, ['approval_id', 'trade_plan_version_id', 'actor', 'approved_at']) &&
      typeof value.version === 'number' &&
      nullableStrings(value, ['correlation_id']))
  );
}

function lifecycleEvent(value: unknown): boolean {
  return (
    record(value) &&
    strings(value, ['id', 'event_type', 'to_status', 'actor', 'occurred_at']) &&
    nullableStrings(value, ['from_status', 'reason', 'correlation_id'])
  );
}

/** Validate the transport shape before a confirmed write response is displayed. No values are changed. */
export function isTradePlanVersionResponse(value: unknown): value is TradePlanVersionResponse {
  return (
    record(value) &&
    strings(value, ['id', 'trade_plan_id', 'thesis', 'created_at', 'created_by']) &&
    typeof value.version === 'number' &&
    value.direction === 'LONG' &&
    typeof value.status === 'string' &&
    ['DRAFT', 'READY_FOR_REVIEW', 'APPROVED', 'ABANDONED', 'SUPERSEDED'].includes(value.status) &&
    nullableStrings(value, ['previous_version_id', 'change_reason']) &&
    entry(value.entry) &&
    record(value.invalidation) &&
    nullableStrings(value.invalidation, ['stop_price', 'invalidation_rule', 'rationale']) &&
    arrayOf(
      value.targets,
      (target) =>
        record(target) &&
        typeof target.sequence === 'number' &&
        typeof target.price === 'string' &&
        nullableStrings(target, ['rationale']),
    ) &&
    record(value.risk_assumptions) &&
    typeof value.risk_assumptions.thesis_risk === 'string' &&
    nullableStrings(value.risk_assumptions, ['max_loss_assumption', 'notes']) &&
    candidateProvenance(value.candidate_evaluation) &&
    approval(value.approval) &&
    arrayOf(value.events, lifecycleEvent)
  );
}

export function isTradePlanDetailResponse(value: unknown): value is TradePlanDetailResponse {
  return (
    record(value) &&
    record(value.plan) &&
    strings(value.plan, ['id', 'underlying_id', 'created_at', 'created_by']) &&
    (value.plan.origin_type === 'MANUAL' || value.plan.origin_type === 'CANDIDATE_EVALUATION') &&
    nullableStrings(value.plan, ['candidate_id', 'candidate_evaluation_id']) &&
    isTradePlanVersionResponse(value.latest_version)
  );
}
