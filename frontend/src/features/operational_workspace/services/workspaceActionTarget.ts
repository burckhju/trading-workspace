import type { OperationalAction } from '../types';

/** Preserve the owner's exact identity and query; select only its existing visible area. */
export function workspaceActionTarget(
  action: Pick<OperationalAction, 'action_type' | 'target'>,
): string {
  const path = action.target.split(/[?#]/)[0];
  if (action.action_type === 'INITIAL_PURCHASE' && path === '/product-selection') {
    return `${action.target.split('#')[0]}#purchase`;
  }
  if (
    path === '/trade-management' &&
    !action.target.includes('#') &&
    ['POSITION_ALERT', 'POSITION_DATA_HEALTH', 'NOTIFICATION_DELIVERY_FAILURE'].includes(
      action.action_type,
    )
  ) {
    return `${action.target}#trade-risk`;
  }
  return action.target;
}
