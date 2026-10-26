import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateEvaluation } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';

export type TradePlanOriginContext =
  | { type: 'MANUAL'; underlying: UnderlyingDetailResponse }
  | {
      type: 'CANDIDATE_EVALUATION';
      underlying: UnderlyingDetailResponse;
      candidateId: string;
      evaluation: CandidateEvaluation;
    };

/** Resolve only the explicitly supplied identity using the existing workspace-scoped reads. */
export async function loadTradePlanOrigin(
  params: URLSearchParams,
  signal: AbortSignal,
): Promise<TradePlanOriginContext | null> {
  for (const key of ['underlying_id', 'candidate_id', 'candidate_evaluation_id']) {
    if (params.getAll(key).length > 1 || (params.has(key) && !params.get(key)?.trim())) {
      throw new Error(
        'Der übergebene Ursprung ist unvollständig oder mehrdeutig. Bitte erneut auswählen.',
      );
    }
  }
  const underlyingId = params.get('underlying_id');
  const candidateId = params.get('candidate_id');
  const evaluationId = params.get('candidate_evaluation_id');

  if (params.has('candidate_id') || params.has('candidate_evaluation_id')) {
    if (!candidateId || !evaluationId) {
      throw new Error(
        'Für den Kandidatenursprung fehlen Kandidat oder konkrete Evaluation. Bitte im Kandidaten erneut auswählen.',
      );
    }
    const [candidates, evaluations] = await Promise.all([
      candidateApiClient.list(signal),
      candidateApiClient.evaluations(candidateId, signal),
    ]);
    const candidate = candidates.find((item) => item.id === candidateId);
    const evaluation = evaluations.find((item) => item.id === evaluationId);
    if (!candidate || !evaluation || !candidate.underlying_id) {
      throw new Error(
        'Die gewählte Evaluation gehört nicht zu einem verfügbaren Kandidaten. Es wurde kein Ersatz gewählt.',
      );
    }
    if (
      evaluation.direction !== 'LONG' ||
      !Number.isInteger(evaluation.version) ||
      evaluation.version < 1
    ) {
      throw new Error('Die gewählte CandidateEvaluation ist kein gültiger LONG-Planungsursprung.');
    }
    if (underlyingId && underlyingId !== candidate.underlying_id) {
      throw new Error(
        'Der übergebene Basiswert passt nicht zum gewählten Kandidaten. Bitte den Ursprung erneut auswählen.',
      );
    }
    const underlying = await marketApiClient.getUnderlying(candidate.underlying_id, signal);
    if (underlying.id !== candidate.underlying_id) {
      throw new Error('Der geladene Basiswert passt nicht zum gewählten Kandidaten.');
    }
    return { type: 'CANDIDATE_EVALUATION', underlying, candidateId, evaluation };
  }

  if (!underlyingId) return null;
  const underlying = await marketApiClient.getUnderlying(underlyingId, signal);
  if (underlying.id !== underlyingId || underlying.lifecycle_status !== 'ACTIVE') {
    throw new Error(
      'Der ausgewählte Basiswert ist nicht als aktiver Planungsursprung verfügbar. Bitte erneut auswählen.',
    );
  }
  return { type: 'MANUAL', underlying };
}
