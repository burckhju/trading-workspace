import type { PurchaseStatus } from './overviewClient';

export const purchaseLabels: Record<PurchaseStatus, string> = {
  NOT_STARTED: 'Noch kein Kauf erfasst',
  OPEN: 'Kauf erfasst · Position offen',
  CLOSED: 'Kauf erfasst · abgeschlossen',
  CANCELLED: 'Nur stornierte Käufe',
  UNKNOWN: 'Kaufstatus ungeklärt',
};
