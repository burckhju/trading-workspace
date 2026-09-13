import type { UnderlyingSummaryResponse } from '../../market/types/api';

/** Resolved from the saved selection run, never inferred from names or query labels. */
export interface SelectionRepairContext {
  runId: string;
  underlying: UnderlyingSummaryResponse;
  warrantId?: string;
}

export function selectionRepairUrl(runId: string, warrantId?: string): string {
  const params = new URLSearchParams({ selection_run_id: runId });
  if (warrantId) params.set('warrant_id', warrantId);
  return `/warrants-admin?${params.toString()}`;
}
