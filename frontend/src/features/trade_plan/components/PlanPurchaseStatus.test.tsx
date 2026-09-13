import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type {
  PlanTradeOverview,
  PurchaseStatus,
  TradePlanOverviewItem,
} from '../services/overviewClient';
import { PlanPurchaseStatus } from './PlanPurchaseStatus';
import { purchaseLabels } from '../services/purchaseStatus';

const plan: TradePlanOverviewItem = {
  id: 'plan',
  underlying_id: 'underlying',
  origin_type: 'MANUAL',
  status: 'APPROVED',
  created_at: '2026-09-13T08:00:00Z',
  latest_version_id: 'v2',
  latest_version: 2,
};
const trade: PlanTradeOverview = {
  trade_id: 'trade-original',
  trade_plan_version_id: 'v1',
  plan_version: 1,
  product_id: 'warrant-original',
  product_name: 'Gekaufter Optionsschein',
  product_isin: 'DE000TEST1234',
  product_wkn: 'TEST12',
  status: 'OPEN',
  open_quantity: 5,
  purchased_on: '2026-08-17',
  purchased_at: '2026-08-16T22:00:00Z',
  closed_on: null,
  closed_at: null,
};
function show(item: TradePlanOverviewItem) {
  render(
    <MemoryRouter>
      <PlanPurchaseStatus item={item} />
    </MemoryRouter>,
  );
}

describe('TradePlan purchase progress', () => {
  it('does not interpret approval or an older API as an unbought plan', () => {
    show(plan);
    expect(screen.getByText('Kaufstatus ungeklärt')).toBeInTheDocument();
    expect(screen.queryByText(purchaseLabels.NOT_STARTED)).not.toBeInTheDocument();
  });
  it('distinguishes a previous-version purchase from an unbought new version', () => {
    show({
      ...plan,
      execution: { status: 'OPEN', current_version_status: 'NOT_STARTED', trades: [trade] },
    });
    expect(screen.getByText(/Aktuelle Version 2: Noch kein Kauf erfasst/)).toBeInTheDocument();
    expect(screen.getByText(/Gekaufter Optionsschein · Planversion 1/)).toBeInTheDocument();
    expect(screen.getByText(/Kaufdatum: 17.08.2026/)).toBeInTheDocument();
    expect(screen.getByText('Offene Stückzahl: 5')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Trade verwalten / Nachkauf' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=trade-original',
    );
  });
  it.each<PurchaseStatus>(['NOT_STARTED', 'CLOSED', 'CANCELLED', 'UNKNOWN'])(
    'renders %s with explicit text',
    (status) => {
      show({ ...plan, execution: { status, current_version_status: status, trades: [] } });
      expect(screen.getByText(purchaseLabels[status])).toBeInTheDocument();
    },
  );
  it('shows full exit dates without calling a cancelled purchase an open holding', () => {
    show({
      ...plan,
      execution: {
        status: 'CLOSED',
        current_version_status: 'NOT_STARTED',
        trades: [
          {
            ...trade,
            status: 'CLOSED',
            open_quantity: 0,
            closed_on: '2026-09-10',
            closed_at: '2026-09-09T22:00:00Z',
          },
          { ...trade, trade_id: 'cancelled', status: 'CANCELLED' },
        ],
      },
    });
    expect(screen.getByText(/Vollständig verkauft: 10.09.2026/)).toBeInTheDocument();
    expect(screen.getByText('0 offen · 1 abgeschlossen · 1 storniert')).toBeInTheDocument();
    expect(screen.queryByText(/Offene Stückzahl/)).not.toBeInTheDocument();
    expect(screen.getByText(/Stornierte Fehleingabe/)).toBeInTheDocument();
  });
  it('keeps data inconsistencies explicit next to another open trade', () => {
    show({
      ...plan,
      execution: {
        status: 'OPEN',
        current_version_status: 'NOT_STARTED',
        trades: [
          trade,
          {
            ...trade,
            trade_id: 'broken',
            status: 'UNKNOWN',
            purchased_on: null,
            purchased_at: null,
          },
        ],
      },
    });
    expect(screen.getByText(/fehlen konsistente Kauf-/)).toBeInTheDocument();
    expect(screen.getByText(/Kaufdatum: unbekannt/)).toBeInTheDocument();
  });
});
