import { describe, expect, it } from 'vitest';
import { workspaceActionTarget } from './workspaceActionTarget';

describe('exact owner action target', () => {
  it.each(['POSITION_ALERT', 'POSITION_DATA_HEALTH', 'NOTIFICATION_DELIVERY_FAILURE'])(
    'opens %s at the visible monitoring area without rewriting pins',
    (action_type) => {
      const target = '/trade-management?trade_id=exact&journal_version_id=historical&report_page=2';
      expect(workspaceActionTarget({ action_type, target })).toBe(`${target}#trade-risk`);
      expect(workspaceActionTarget({ action_type, target: `${target}#execution-dates` })).toBe(
        `${target}#execution-dates`,
      );
    },
  );
  it('uses the actual purchase form for exactly the selected run', () => {
    expect(
      workspaceActionTarget({
        action_type: 'INITIAL_PURCHASE',
        target: '/product-selection?run_id=exact&plan_filter=NOT_PURCHASED#selection',
      }),
    ).toBe('/product-selection?run_id=exact&plan_filter=NOT_PURCHASED#purchase');
  });
  it('keeps other actions and other owner routes unchanged', () => {
    for (const action_type of ['OPEN_POSITION_MANAGEMENT', 'EXIT_REVIEW', 'UNKNOWN'])
      expect(
        workspaceActionTarget({ action_type, target: '/trade-management?trade_id=exact' }),
      ).toBe('/trade-management?trade_id=exact');
    expect(
      workspaceActionTarget({ action_type: 'POSITION_ALERT', target: '/other?trade_id=exact' }),
    ).toBe('/other?trade_id=exact');
    expect(
      workspaceActionTarget({
        action_type: 'INITIAL_PURCHASE',
        target: '/product-selection-other?run_id=exact',
      }),
    ).toBe('/product-selection-other?run_id=exact');
  });
});
