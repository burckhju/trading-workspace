export type TradeManagementArea = 'overview' | 'history' | 'bookings' | 'monitoring' | 'management';

/** Presentation only. Legacy object anchors keep the same owner, drafts and reads mounted. */
export function tradeManagementArea(hash: string): TradeManagementArea {
  if (hash === '#position-price-history') return 'history';
  if (hash === '#execution-dates' || hash === '#sale-capture' || hash === '#additional-purchase')
    return 'bookings';
  if (hash === '#trade-risk' || hash === '#trade-monitoring') return 'monitoring';
  if (hash === '#trade-management-state' || hash === '#trade-cancellation') return 'management';
  return 'overview';
}
