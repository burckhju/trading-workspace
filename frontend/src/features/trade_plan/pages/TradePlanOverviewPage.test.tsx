import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { tradePlanOverviewApiClient } from '../services/overviewClient';
import { TradePlanOverviewPage } from './TradePlanOverviewPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    getUnderlying: vi.fn(),
  },
}));

vi.mock('../services/overviewClient', () => ({
  tradePlanOverviewApiClient: {
    list: vi.fn(),
  },
}));

const overviewApi = vi.mocked(tradePlanOverviewApiClient);
const marketApi = vi.mocked(marketApiClient);

describe('TradePlanOverviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    overviewApi.list.mockResolvedValue([
      {
        id: '12345678-0000-4000-8000-000000000001',
        underlying_id: 'underlying-1',
        origin_type: 'MANUAL',
        created_at: '2026-09-05T06:00:00Z',
        latest_version_id: 'version-1',
        latest_version: 1,
        status: 'DRAFT',
      },
    ]);
    marketApi.getUnderlying.mockResolvedValue({
      id: 'underlying-1',
      type: 'STOCK',
      name: 'Apple Inc.',
      isin: 'US0378331005',
      wkn: '865985',
      lifecycle_status: 'ACTIVE',
      quality_status: 'VERIFIED',
      version: 1,
      created_at: '2026-09-05T05:00:00Z',
      updated_at: '2026-09-05T05:00:00Z',
      primary_listing: {
        id: 'listing-1',
        ticker: 'AAPL',
        trading_venue_id: 'venue-1',
        trading_venue_mic: 'XNAS',
        trading_venue_name: 'Nasdaq',
        currency_code: 'USD',
      },
      listings: [],
    });
  });

  it('shows existing plans with user-facing identity and open action', async () => {
    render(
      <MemoryRouter>
        <TradePlanOverviewPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('TP-12345678')).toBeInTheDocument();
    expect(screen.getByText(/AAPL · US0378331005 · 865985/)).toBeInTheDocument();
    expect(screen.getByText('Entwurf')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Öffnen' })).toHaveAttribute(
      'href',
      '/trade-plans?trade_plan_id=12345678-0000-4000-8000-000000000001',
    );
  });
  it('filters purchase state independently of approval and refreshes persisted progress', async () => {
    const user = userEvent.setup();
    const base = {
      id: 'plan',
      underlying_id: 'u',
      underlying_name: 'Status stock',
      origin_type: 'MANUAL' as const,
      created_at: '2026-09-13T08:00:00Z',
      latest_version_id: 'v1',
      latest_version: 1,
      status: 'APPROVED' as const,
    };
    overviewApi.list.mockResolvedValue([
      {
        ...base,
        execution: { status: 'NOT_STARTED', current_version_status: 'NOT_STARTED', trades: [] },
      },
      {
        ...base,
        id: 'bought-plan',
        execution: { status: 'OPEN', current_version_status: 'OPEN', trades: [] },
      },
    ]);
    render(
      <MemoryRouter>
        <TradePlanOverviewPage />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText('Noch kein Kauf erfasst', { selector: 'span' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Kauf erfasst · Position offen', { selector: 'span' }),
    ).toBeInTheDocument();
    expect(marketApi.getUnderlying).not.toHaveBeenCalled();
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Nach Kaufstatus filtern' }),
      'NOT_STARTED',
    );
    expect(screen.getByText('1 von 2 Tradeplänen')).toBeInTheDocument();
    expect(
      screen.queryByText('Kauf erfasst · Position offen', { selector: 'span' }),
    ).not.toBeInTheDocument();
    overviewApi.list.mockResolvedValue([
      { ...base, execution: { status: 'OPEN', current_version_status: 'OPEN', trades: [] } },
    ]);
    await user.click(screen.getByRole('button', { name: 'Übersicht aktualisieren' }));
    expect(await screen.findByText('Keine Tradepläne mit diesem Kaufstatus.')).toBeInTheDocument();
    await user.selectOptions(screen.getByRole('combobox'), 'OPEN');
    expect(
      screen.getByText('Kauf erfasst · Position offen', { selector: 'span' }),
    ).toBeInTheDocument();
    overviewApi.list.mockRejectedValue(new Error('Status request failed'));
    await user.click(screen.getByRole('button', { name: 'Übersicht aktualisieren' }));
    expect(await screen.findByText('Status request failed')).toBeInTheDocument();
    expect(
      screen.queryByText('Kauf erfasst · Position offen', { selector: 'span' }),
    ).not.toBeInTheDocument();
  });

  it('restores a bookmarked purchase filter and keeps it in detail and selected-product entries', async () => {
    const user = userEvent.setup();
    overviewApi.list.mockResolvedValue([
      {
        id: 'plan-1',
        underlying_id: 'u',
        underlying_name: 'Apple Inc.',
        origin_type: 'MANUAL',
        created_at: '2026-09-05T06:00:00Z',
        latest_version_id: 'version-1',
        latest_version: 1,
        status: 'APPROVED',
        execution: { status: 'OPEN', current_version_status: 'OPEN', trades: [] },
        selected_product: {
          run_id: 'saved-run',
          product_evaluation_id: 'evaluation-1',
          warrant_id: 'product-1',
          display_name: 'Apple CALL',
          isin: 'DE000TEST001',
          wkn: 'TEST01',
        },
      },
    ]);
    const router = createMemoryRouter(
      [{ path: '/trade-plans/overview', element: <TradePlanOverviewPage /> }],
      { initialEntries: ['/trade-plans/overview?purchase_status=OPEN'] },
    );
    render(<RouterProvider router={router} />);
    await screen.findByText('Apple Inc.');
    expect(screen.getByRole('combobox')).toHaveValue('OPEN');
    expect(screen.getByRole('link', { name: 'Öffnen' })).toHaveAttribute(
      'href',
      '/trade-plans?trade_plan_id=plan-1&plan_filter=OPEN',
    );
    expect(screen.getByRole('link', { name: 'Ausgewählten Optionsschein prüfen' })).toHaveAttribute(
      'href',
      '/product-selection?run_id=saved-run&plan_filter=OPEN',
    );
    await user.selectOptions(screen.getByRole('combobox'), 'CLOSED');
    expect(router.state.location.search).toBe('?purchase_status=CLOSED');
    expect(screen.getByText('Keine Tradepläne mit diesem Kaufstatus.')).toBeInTheDocument();
    await act(() => router.navigate(-1));
    expect(screen.getByRole('combobox')).toHaveValue('OPEN');
    expect(screen.getByRole('link', { name: 'Öffnen' })).toBeVisible();
    expect(overviewApi.list).toHaveBeenCalledOnce();
  });
});
