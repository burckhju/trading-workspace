import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { tradePlanOverviewApiClient, type TradePlanOverviewItem } from '../services/overviewClient';
import { TradePlanOverviewPage } from './TradePlanOverviewPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: { getUnderlying: vi.fn() },
}));
vi.mock('../services/overviewClient', () => ({
  tradePlanOverviewApiClient: { list: vi.fn() },
}));
const api = vi.mocked(tradePlanOverviewApiClient);
const marketApi = vi.mocked(marketApiClient);

function plan(overrides: Partial<TradePlanOverviewItem> = {}): TradePlanOverviewItem {
  return {
    id: '12345678-0000-4000-8000-000000000001',
    underlying_id: 'synthetic-stock',
    underlying_name: 'Synthetischer Basiswert',
    underlying_isin: 'US000SYN0001',
    underlying_wkn: 'BAS001',
    origin_type: 'MANUAL',
    created_at: '2026-09-01T10:00:00Z',
    latest_version_id: 'version-2',
    latest_version: 2,
    status: 'APPROVED',
    selected_product: {
      run_id: 'selected-run-2',
      product_evaluation_id: 'selected-evaluation-2',
      warrant_id: 'selected-warrant',
      display_name: 'Synthetischer Call Alpha',
      isin: 'DE000SYN0001',
      wkn: 'SYN001',
    },
    execution: { status: 'NOT_STARTED', current_version_status: 'NOT_STARTED', trades: [] },
    ...overrides,
  };
}

const purchased: TradePlanOverviewItem['execution'] = {
  status: 'OPEN',
  current_version_status: 'NOT_STARTED',
  trades: [
    {
      trade_id: 'purchased-trade',
      trade_plan_version_id: 'version-1',
      plan_version: 1,
      product_id: 'purchased-warrant',
      product_name: 'Tatsächlich gekaufter Call Beta',
      product_isin: 'DE000SYN0002',
      product_wkn: 'SYN002',
      status: 'OPEN',
      open_quantity: 5,
      purchased_on: '2026-08-17',
      purchased_at: null,
      closed_on: null,
      closed_at: null,
    },
  ],
};

function show() {
  return render(
    <MemoryRouter>
      <TradePlanOverviewPage />
    </MemoryRouter>,
  );
}

describe('TradePlan overview warrant identity', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.list.mockResolvedValue([plan()]);
  });

  it('shows the selected warrant separately from its underlying before any purchase', async () => {
    show();
    expect(await screen.findByText('Synthetischer Call Alpha')).toBeVisible();
    const selection = screen.getByRole('region', { name: 'Optionsschein-Auswahl' });
    expect(within(selection).getByText('Ausgewählter Optionsschein · Version 2')).toBeVisible();
    expect(selection).toHaveTextContent('WKN SYN001 · ISIN DE000SYN0001');
    expect(selection).not.toHaveTextContent('US000SYN0001');
    expect(screen.getByText('Basiswert')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Synthetischer Basiswert' })).toBeVisible();
    expect(selection).toHaveTextContent('Eine Produktauswahl ist kein Kaufnachweis.');
    expect(screen.getByRole('region', { name: 'Kaufstatus' })).toHaveTextContent(
      'Noch kein Kauf erfasst',
    );
    expect(
      within(selection).getByRole('link', { name: 'Ausgewählten Optionsschein prüfen' }),
    ).toHaveAttribute('href', '/product-selection?run_id=selected-run-2');
    expect(screen.queryByRole('link', { name: 'Produkt auswählen' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Produktauswahl öffnen' })).toBeVisible();
    expect(api.list).toHaveBeenCalledTimes(1);
    expect(marketApi.getUnderlying).not.toHaveBeenCalled();
  });

  it('does not mix different selections for the same underlying or replace a historical purchase', async () => {
    const second = plan({ id: '87654321-0000-4000-8000-000000000002' });
    second.selected_product = {
      ...second.selected_product!,
      run_id: 'other-run',
      warrant_id: 'other-warrant',
      display_name: 'Synthetischer Call Gamma',
      wkn: 'SYN003',
      isin: 'DE000SYN0003',
    };
    api.list.mockResolvedValue([plan({ execution: purchased }), second]);
    show();
    const first = (await screen.findByText('TP-12345678')).closest('article')!;
    const other = screen.getByText('TP-87654321').closest('article')!;
    const selection = within(first).getByRole('region', { name: 'Optionsschein-Auswahl' });
    expect(selection).toHaveTextContent('Synthetischer Call Alpha');
    expect(selection).not.toHaveTextContent('SYN002');
    expect(first).not.toHaveTextContent('SYN003');
    expect(other).toHaveTextContent('Synthetischer Call Gamma');
    expect(other).not.toHaveTextContent('SYN001');
    const history = within(first).getByRole('region', { name: 'Kaufstatus' });
    expect(history).toHaveTextContent('Tatsächlich gekaufter Call Beta · Planversion 1');
    expect(history).toHaveTextContent('WKN SYN002 · ISIN DE000SYN0002');
    expect(history).not.toHaveTextContent('SYN001');
    expect(
      within(history).getByRole('link', { name: 'Trade verwalten / Nachkauf' }),
    ).toHaveAttribute('href', '/trade-management?trade_id=purchased-trade');
  });

  it('shows no selection for the current version without borrowing an older purchased warrant', async () => {
    api.list.mockResolvedValue([plan({ selected_product: null, execution: purchased })]);
    show();
    const selection = await screen.findByRole('region', { name: 'Optionsschein-Auswahl' });
    expect(selection).toHaveTextContent(
      'Für diese Planversion wurde noch kein Optionsschein ausgewählt.',
    );
    expect(selection).not.toHaveTextContent('SYN002');
    expect(within(selection).queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Kaufstatus' })).toHaveTextContent('SYN002');
  });

  it('distinguishes unavailable selection data from an explicit empty selection on older backends', async () => {
    api.list.mockResolvedValue([plan({ selected_product: undefined })]);
    show();
    const selection = await screen.findByRole('region', { name: 'Optionsschein-Auswahl' });
    expect(selection).toHaveTextContent('Optionsschein-Auswahl nicht verfügbar.');
    expect(selection).not.toHaveTextContent('noch kein Optionsschein ausgewählt');
    expect(selection).not.toHaveTextContent('SYN001');
    expect(within(selection).queryByRole('link')).not.toBeInTheDocument();
  });

  it.each([null, '   '])(
    'keeps missing product metadata explicit (%s) instead of using the underlying',
    async (missing) => {
      const item = plan({ execution: purchased });
      item.selected_product = {
        ...item.selected_product!,
        display_name: missing,
        isin: missing,
        wkn: missing,
      };
      api.list.mockResolvedValue([item]);
      show();
      const selection = await screen.findByRole('region', { name: 'Optionsschein-Auswahl' });
      expect(selection).toHaveTextContent('Produktname nicht verfügbar');
      expect(selection).toHaveTextContent('WKN nicht hinterlegt · ISIN nicht hinterlegt');
      expect(selection).toHaveTextContent('Produktdaten unvollständig');
      expect(selection).not.toHaveTextContent('Synthetischer Basiswert');
      expect(selection).not.toHaveTextContent('BAS001');
      expect(selection).not.toHaveTextContent('SYN002');
      expect(within(selection).getByRole('link')).toHaveAttribute(
        'href',
        '/product-selection?run_id=selected-run-2',
      );
    },
  );

  it('refreshes the exact version and clears a previous selection without clearing historical purchases', async () => {
    const user = userEvent.setup();
    api.list.mockResolvedValue([plan({ execution: purchased })]);
    show();
    expect(await screen.findByText('Synthetischer Call Alpha')).toBeVisible();
    api.list.mockResolvedValue([
      plan({
        latest_version_id: 'version-3',
        latest_version: 3,
        status: 'DRAFT',
        selected_product: null,
        execution: purchased,
      }),
    ]);
    await user.click(screen.getByRole('button', { name: 'Übersicht aktualisieren' }));
    expect(await screen.findByText('Ausgewählter Optionsschein · Version 3')).toBeVisible();
    expect(screen.queryByText('Synthetischer Call Alpha')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Ausgewählten Optionsschein prüfen' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Kaufstatus' })).toHaveTextContent('SYN002');
  });

  it('hides obsolete warrant identities after a failed refresh', async () => {
    const user = userEvent.setup();
    show();
    expect(await screen.findByText('Synthetischer Call Alpha')).toBeVisible();
    api.list.mockRejectedValue(new Error('Synthetic overview read failed'));
    await user.click(screen.getByRole('button', { name: 'Übersicht aktualisieren' }));
    expect(await screen.findByText('Synthetic overview read failed')).toBeVisible();
    expect(screen.queryByText('Synthetischer Call Alpha')).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Optionsschein-Auswahl' })).not.toBeInTheDocument();
  });

  it('ignores an aborted older response after navigation back to the overview', async () => {
    let finish!: (items: TradePlanOverviewItem[]) => void;
    api.list.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const first = show();
    const signal = api.list.mock.calls[0][0];
    first.unmount();
    expect(signal?.aborted).toBe(true);
    api.list.mockResolvedValue([plan({ selected_product: null })]);
    show();
    expect(
      await screen.findByText('Für diese Planversion wurde noch kein Optionsschein ausgewählt.'),
    ).toBeVisible();
    await act(async () => {
      finish([plan()]);
      await Promise.resolve();
    });
    expect(screen.queryByText('Synthetischer Call Alpha')).not.toBeInTheDocument();
  });
});
