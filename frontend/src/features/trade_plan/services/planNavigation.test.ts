import { describe, expect, it } from 'vitest';
import { planOverviewReturnUrl, planPurchaseFilter, withPlanListContext } from './planNavigation';

describe('trade plan list context', () => {
  it('carries the purchase filter through exact historical selection links and returns to the same plan', () => {
    const source = new URLSearchParams('purchase_status=OPEN&return_to=https://example.invalid');
    const detail = withPlanListContext(
      '/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=historical-2&review_id=review-3#sources',
      source,
    );
    expect(detail).toBe(
      '/trade-plans?trade_plan_id=plan-1&trade_plan_version_id=historical-2&review_id=review-3&plan_filter=OPEN#sources',
    );
    const params = new URL(detail, 'https://workspace.invalid').searchParams;
    expect(withPlanListContext('/product-selection?run_id=saved-4#purchase', params)).toBe(
      '/product-selection?run_id=saved-4&plan_filter=OPEN#purchase',
    );
    expect(planOverviewReturnUrl(params, 'plan-1')).toBe(
      '/trade-plans/overview?purchase_status=OPEN#plan-plan-1',
    );
    expect(source.get('purchase_status')).toBe('OPEN');
  });

  it.each([
    'purchase_status=APPROVED',
    'purchase_status=OPEN&purchase_status=CLOSED',
    'purchase_status=__proto__',
  ])('does not reinterpret an unknown or ambiguous purchase filter: %s', (query) => {
    const params = new URLSearchParams(query);
    expect(planPurchaseFilter(params)).toBe('ALL');
    expect(withPlanListContext('/trade-plans?trade_plan_id=plan-1', params)).toBe(
      '/trade-plans?trade_plan_id=plan-1',
    );
  });

  it('uses only a valid list filter for the return destination', () => {
    expect(
      planOverviewReturnUrl(new URLSearchParams('plan_filter=CLOSED&return_to=/elsewhere')),
    ).toBe('/trade-plans/overview?purchase_status=CLOSED');
    expect(planOverviewReturnUrl(new URLSearchParams('plan_filter=OPEN&plan_filter=CLOSED'))).toBe(
      '/trade-plans/overview',
    );
  });
});
