export const pinKeys = ['review_version_id', 'journal_version_id'] as const;
export type PinKey = (typeof pinKeys)[number];

// Deliberately no URL/returnTo, amount, classification, workspace or source ID.
// This is navigation context, never a historical report or trusted money input.
export const closedContextKeys = [
  'report_context',
  'from_date',
  'to_date',
  'report_currency',
  'report_timezone',
  'report_view',
  'report_page',
  'report_basis',
] as const;

export function preserveClosedContext(from: URLSearchParams, to: URLSearchParams): void {
  // Preserve even an invalid context as invalid when switching historical pins;
  // do not silently turn it into a different, unqualified navigation context.
  for (const key of closedContextKeys) for (const value of from.getAll(key)) to.append(key, value);
}
