import { purchaseLabels } from './purchaseStatus';
import type { PurchaseStatus } from './overviewClient';
import type { TradePlanStatus } from '../types/api';

export const planStatusLabels: Record<TradePlanStatus, string> = {
  DRAFT: 'Entwurf',
  READY_FOR_REVIEW: 'Zur Prüfung',
  APPROVED: 'Freigegeben',
  ABANDONED: 'Aufgegeben',
  SUPERSEDED: 'Abgelöst',
};

export function planStatusLabel(status: string): string {
  return planStatusLabels[status as TradePlanStatus] ?? status;
}

/** Presentation context only: never changes a plan or its approval/purchase state. */
export function planPurchaseFilter(
  params: URLSearchParams,
  key = 'purchase_status',
): PurchaseStatus | 'ALL' {
  const values = params.getAll(key);
  const value = values[0];
  return values.length === 1 && value && Object.hasOwn(purchaseLabels, value)
    ? (value as PurchaseStatus)
    : 'ALL';
}

export function withPlanListContext(href: string, params: URLSearchParams): string {
  const filter = params.has('purchase_status')
    ? planPurchaseFilter(params)
    : planPurchaseFilter(params, 'plan_filter');
  if (filter === 'ALL') return href;
  const url = new URL(href, 'https://workspace.invalid');
  url.searchParams.set('plan_filter', filter);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function planOverviewReturnUrl(params: URLSearchParams, planId?: string): string {
  const filter = planPurchaseFilter(params, 'plan_filter');
  const query = filter === 'ALL' ? '' : `?purchase_status=${filter}`;
  const anchor = planId ? `#plan-${encodeURIComponent(planId)}` : '';
  return `/trade-plans/overview${query}${anchor}`;
}
