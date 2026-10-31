import { preserveClosedContext } from '../../performance/services/closedReportContext';
import { pinKeys } from './sourceView';

export type TradeWorkspaceView = 'management' | 'sources' | 'journal';

/** Navigation only: never use these parameters as financial or review evidence. */
function contextQuery(tradeId: string, from: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams({ trade_id: tradeId });
  for (const key of pinKeys) for (const value of from.getAll(key)) next.append(key, value);
  preserveClosedContext(from, next);
  return next;
}

export function tradeWorkspaceLink(
  view: TradeWorkspaceView,
  tradeId: string,
  from: URLSearchParams,
  hash = '',
): string {
  const query = contextQuery(tradeId, from);
  if (view === 'sources') query.set('view', 'sources');
  return `${view === 'journal' ? '/post-trade' : '/trade-management'}?${query}${hash}`;
}

export function tradeLessonLink(
  lessonId: string,
  versionId: string | null,
  tradeId: string,
  from: URLSearchParams,
  returnView: 'sources' | 'journal' = 'journal',
): string {
  const query = tradeId ? contextQuery(tradeId, from) : new URLSearchParams();
  if (tradeId) query.set('trade_return_view', returnView);
  if (versionId) query.set('lesson_version_id', versionId);
  return `/lessons/${encodeURIComponent(lessonId)}${query.size ? `?${query}` : ''}#lesson-history`;
}

export function lessonTradeReturnLink(query: URLSearchParams): string | null {
  const ids = query.getAll('trade_id');
  const views = query.getAll('trade_return_view');
  if (ids.length !== 1 || !ids[0].trim() || views.length !== 1) return null;
  if (views[0] !== 'sources' && views[0] !== 'journal') return null;
  return tradeWorkspaceLink(
    views[0],
    ids[0],
    query,
    views[0] === 'sources' ? '#trade-evidence-sources' : '#trade-journal',
  );
}
