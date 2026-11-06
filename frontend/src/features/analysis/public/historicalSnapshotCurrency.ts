import { analysisApiClient } from '../services/client';

export type HistoricalAnalysisReference = {
  analysisId: string;
  version: number;
  underlyingId: string;
  modelId: string;
  modelVersion: string;
};

export type HistoricalAnalysisCurrency = {
  currency: string;
  analysisId: string;
  version: number;
  listingId: string;
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nonempty(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function positiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

function calendarDate(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return (
    Number.isFinite(date.getTime()) &&
    date.getUTCFullYear() > 0 &&
    date.toISOString().slice(0, 10) === value
  );
}

/**
 * Read one exact stored source through the existing Analysis GETs. The run response
 * carries identity; snapshot pages are bound to that immutable run by the server's
 * run_id-scoped reader. A page alone is never a complete currency source.
 */
export async function readHistoricalAnalysisCurrency(
  reference: HistoricalAnalysisReference,
  signal: AbortSignal,
): Promise<HistoricalAnalysisCurrency | null> {
  signal.throwIfAborted();
  if (
    !record(reference) ||
    !nonempty(reference.analysisId) ||
    !positiveInteger(reference.version) ||
    !nonempty(reference.underlyingId) ||
    !nonempty(reference.modelId) ||
    !nonempty(reference.modelVersion)
  )
    return null;

  const { analysisId, version, underlyingId, modelId, modelVersion } = reference;
  const detail: unknown = await analysisApiClient.getRun(analysisId, version, signal);
  signal.throwIfAborted();
  if (!record(detail) || !record(detail.analysis) || !record(detail.run)) return null;
  const { analysis, run } = detail;
  if (
    analysis.id !== analysisId ||
    analysis.underlying_id !== underlyingId ||
    !nonempty(analysis.listing_id) ||
    run.version !== version ||
    run.model_id !== modelId ||
    run.model_version !== modelVersion ||
    !positiveInteger(run.observation_count)
  )
    return null;

  const listingId = analysis.listing_id;
  const total = run.observation_count;
  const limit = 200; // Existing API page limit, not a cap on the complete snapshot.
  let offset = 0;
  let currency: string | null = null;
  let previousDate: string | null = null;
  while (offset < total) {
    signal.throwIfAborted();
    const page: unknown = await analysisApiClient.getSnapshot(
      analysisId,
      version,
      offset,
      limit,
      signal,
    );
    signal.throwIfAborted();
    if (
      !record(page) ||
      !Array.isArray(page.items) ||
      page.total !== total ||
      page.offset !== offset ||
      page.limit !== limit ||
      page.items.length !== Math.min(limit, total - offset)
    )
      return null;

    const rows: unknown[] = page.items;
    for (const row of rows) {
      if (
        !record(row) ||
        !calendarDate(row.trading_date) ||
        (previousDate !== null && row.trading_date <= previousDate) ||
        !nonempty(row.currency) ||
        (currency !== null && row.currency !== currency)
      )
        return null;
      previousDate = row.trading_date;
      currency = row.currency;
    }
    offset += rows.length;
  }
  signal.throwIfAborted();
  return currency === null ? null : { currency, analysisId, version, listingId };
}
