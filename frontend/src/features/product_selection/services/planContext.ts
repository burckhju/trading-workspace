import { tradePlanApiClient } from '../../trade_plan/services/client';
import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../../trade_plan/types/api';
import type { ProductSelectionRunDetailResponse } from '../types/api';

export interface SelectionPlanContext {
  detail: TradePlanDetailResponse;
  version: TradePlanVersionResponse;
}

export type SelectionRoute =
  | { kind: 'plan'; planId: string; versionId: string }
  | { kind: 'run'; runId: string; planId: string; versionId: string }
  | { kind: 'invalid'; message: string };

export function selectionRoute(params: URLSearchParams): SelectionRoute {
  const keys = ['run_id', 'trade_plan_id', 'trade_plan_version_id'];
  const runId = params.get('run_id')?.trim() ?? '';
  const planId = params.get('trade_plan_id')?.trim() ?? '';
  const versionId = params.get('trade_plan_version_id')?.trim() ?? '';
  if (
    keys.some(
      (key) => params.getAll(key).length > 1 || (params.has(key) && !params.get(key)?.trim()),
    ) ||
    Boolean(planId) !== Boolean(versionId) ||
    (!runId && !planId)
  ) {
    return {
      kind: 'invalid',
      message:
        'Der Auswahlkontext ist unvollständig oder widersprüchlich. Bitte einen Plan und eine konkrete freigegebene Version auswählen.',
    };
  }
  return runId ? { kind: 'run', runId, planId, versionId } : { kind: 'plan', planId, versionId };
}

/** A current overview label is never used to resolve a historical version. */
export async function loadSelectionPlanContext(
  planId: string,
  versionId: string,
  signal?: AbortSignal,
): Promise<SelectionPlanContext> {
  const [detail, version] = await Promise.all([
    tradePlanApiClient.get(planId, signal),
    tradePlanApiClient.version(planId, versionId, signal),
  ]);
  if (
    detail.plan.id !== planId ||
    detail.latest_version.trade_plan_id !== planId ||
    version.id !== versionId ||
    version.trade_plan_id !== planId
  ) {
    throw new Error('Plan und angeforderte Version gehören nicht zum übergebenen Kontext.');
  }
  return { detail, version };
}

export function assertRunContext(
  detail: ProductSelectionRunDetailResponse,
  expected: { runId?: string; planId?: string; versionId?: string; underlyingId?: string },
): void {
  const { run } = detail;
  if (
    (expected.runId && run.id !== expected.runId) ||
    (expected.planId && run.trade_plan_id !== expected.planId) ||
    (expected.versionId && run.trade_plan_version_id !== expected.versionId) ||
    (expected.underlyingId && run.underlying_id !== expected.underlyingId) ||
    detail.evaluations.some((evaluation) => evaluation.run_id !== run.id) ||
    (detail.selection &&
      (detail.selection.run_id !== run.id ||
        !detail.evaluations.some(
          (evaluation) => evaluation.id === detail.selection?.product_evaluation_id,
        )))
  ) {
    throw new Error(
      'Der gespeicherte Run passt nicht zu den angeforderten Plan- und Versionsreferenzen.',
    );
  }
}
