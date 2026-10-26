import type { TradePlanSummaryResponse } from '../types/api';

const originKeys = ['underlying_id', 'candidate_id', 'candidate_evaluation_id'] as const;

export function planOriginHintQuery(params: URLSearchParams): string {
  const hints = new URLSearchParams();
  for (const key of originKeys) for (const value of params.getAll(key)) hints.append(key, value);
  return hints.toString();
}

export function planViewContextKey(
  planId: string,
  versionId: string,
  params: URLSearchParams,
): string {
  return JSON.stringify([
    planId,
    versionId,
    params.getAll('trade_plan_version_id'),
    planOriginHintQuery(params),
  ]);
}

/** Legacy origin hints may confirm a stored identity, but may never replace any part of it. */
export function planOriginHintError(query: string, plan?: TradePlanSummaryResponse): string | null {
  const hints = new URLSearchParams(query);
  for (const key of originKeys) {
    if (hints.getAll(key).length > 1 || (hints.has(key) && !hints.get(key)?.trim())) {
      return 'Der zusätzliche Ursprungskontext ist leer oder mehrdeutig. Bitte den gespeicherten Plan aus der Übersicht öffnen.';
    }
  }
  if (hints.has('candidate_id') !== hints.has('candidate_evaluation_id')) {
    return 'Der zusätzliche Kandidatenkontext ist unvollständig. Kandidat und konkrete Evaluation müssen gemeinsam übergeben werden.';
  }
  if (!plan) return null;
  if (hints.has('underlying_id') && hints.get('underlying_id') !== plan.underlying_id) {
    return 'Der zusätzlich übergebene Basiswert passt nicht zur gespeicherten Planidentität. Der Ursprung wurde nicht geändert.';
  }
  if (
    hints.has('candidate_id') &&
    (plan.origin_type !== 'CANDIDATE_EVALUATION' ||
      hints.get('candidate_id') !== plan.candidate_id ||
      hints.get('candidate_evaluation_id') !== plan.candidate_evaluation_id)
  ) {
    return 'Der zusätzlich übergebene Kandidatenkontext passt nicht zur gespeicherten Planidentität. Der Ursprung wurde nicht geändert.';
  }
  return null;
}
