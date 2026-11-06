import { readHistoricalAnalysisCurrency, type HistoricalAnalysisCurrency } from '../../analysis';
import type { TradePlanOriginContext } from './originContext';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Optional source read; the required Candidate/Underlying origin read remains separate. */
export async function loadCandidatePlanCurrencySuggestion(
  origin: TradePlanOriginContext,
  signal: AbortSignal,
): Promise<HistoricalAnalysisCurrency | null> {
  if (origin.type !== 'CANDIDATE_EVALUATION') return null;
  const sources: unknown = origin.evaluation.sources;
  if (!Array.isArray(sources)) return null;
  const rows: unknown[] = sources;
  if (
    rows.some((source) => !record(source) || typeof source.role !== 'string' || !source.role.trim())
  )
    return null;
  // Count the role before checking its type: a second UNDERLYING is ambiguous,
  // even if only one of those references happens to be an ANALYSIS.
  const underlying = rows.filter((source) => record(source) && source.role === 'UNDERLYING');
  if (underlying.length !== 1) return null;
  const source = underlying[0];
  if (
    !record(source) ||
    source.source_type !== 'ANALYSIS' ||
    typeof source.source_id !== 'string' ||
    !source.source_id.trim() ||
    typeof source.source_version !== 'number' ||
    !Number.isSafeInteger(source.source_version) ||
    source.source_version <= 0 ||
    typeof source.model_id !== 'string' ||
    !source.model_id.trim() ||
    typeof source.model_version !== 'string' ||
    !source.model_version.trim()
  )
    return null;

  return readHistoricalAnalysisCurrency(
    {
      analysisId: source.source_id,
      version: source.source_version,
      underlyingId: origin.underlying.id,
      modelId: source.model_id,
      modelVersion: source.model_version,
    },
    signal,
  );
}
