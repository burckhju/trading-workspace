import type { LifecycleStatus } from '../types/api';

export const UNDERLYING_PAGE_SIZE = 25;
const LIST_PATH = '/underlyings';

export interface UnderlyingListView {
  query: string;
  lifecycle: LifecycleStatus | '';
  venueId: string;
  currencyCode: string;
  offset: number;
}

export function readUnderlyingListView(params: URLSearchParams): UnderlyingListView {
  const rawOffset = params.get('offset') ?? '0';
  const offset = Number(rawOffset);
  const lifecycle = params.get('lifecycle');
  return {
    query: params.get('query')?.trim() ?? '',
    lifecycle: lifecycle === 'ACTIVE' || lifecycle === 'INACTIVE' ? lifecycle : '',
    venueId: params.get('venue') ?? '',
    currencyCode: params.get('currency') ?? '',
    offset:
      /^\d+$/.test(rawOffset) &&
      Number.isSafeInteger(offset) &&
      offset <= Number.MAX_SAFE_INTEGER - UNDERLYING_PAGE_SIZE &&
      offset % UNDERLYING_PAGE_SIZE === 0
        ? offset
        : 0,
  };
}

export function underlyingListParams(view: UnderlyingListView): URLSearchParams {
  const params = new URLSearchParams();
  if (view.query) params.set('query', view.query);
  if (view.lifecycle) params.set('lifecycle', view.lifecycle);
  if (view.venueId) params.set('venue', view.venueId);
  if (view.currencyCode) params.set('currency', view.currencyCode);
  if (view.offset) params.set('offset', String(view.offset));
  return params;
}

export function underlyingListUrl(view: UnderlyingListView): string {
  const query = underlyingListParams(view).toString();
  return query ? `${LIST_PATH}?${query}` : LIST_PATH;
}

// Only our list route and its known view parameters are valid return targets.
// Never use an arbitrary URL or a history delta for this navigation contract.
export function underlyingListReturnTo(params: URLSearchParams): string | undefined {
  const target = params.get('returnTo');
  if (target === LIST_PATH) return LIST_PATH;
  if (!target?.startsWith(`${LIST_PATH}?`)) return undefined;
  return underlyingListUrl(
    readUnderlyingListView(new URLSearchParams(target.slice(LIST_PATH.length + 1))),
  );
}

export function withUnderlyingListReturnTo(path: string, returnTo?: string): string {
  if (!returnTo) return path;
  return `${path}${path.includes('?') ? '&' : '?'}${new URLSearchParams({ returnTo })}`;
}
