import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProductSelectionWorkflowPage } from './ProductSelectionWorkflowPage';

const approvedPlan = {
  id: '00000000-0000-4000-8000-000000000201',
  underlying_id: '00000000-0000-4000-8000-000000000301',
  origin_type: 'MANUAL',
  created_at: '2026-09-08T10:00:00Z',
  latest_version_id: '00000000-0000-4000-8000-000000000202',
  latest_version: 3,
  status: 'APPROVED',
};

const draftPlan = {
  ...approvedPlan,
  id: '00000000-0000-4000-8000-000000000211',
  latest_version_id: '00000000-0000-4000-8000-000000000212',
  status: 'DRAFT',
};

const underlying = {
  id: approvedPlan.underlying_id,
  name: 'DAX',
  asset_class: 'INDEX',
  currency: 'EUR',
  isin: 'DE0008469008',
  wkn: '846900',
  status: 'ACTIVE',
  primary_listing: {
    id: '00000000-0000-4000-8000-000000000401',
    ticker: 'DAX',
  },
};

describe('ProductSelectionWorkflowPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('offers approved trade plans without requiring UUID input', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify([approvedPlan, draftPlan]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(underlying), { status: 200 }));

    render(
      <MemoryRouter initialEntries={['/product-selection']}>
        <ProductSelectionWorkflowPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('heading', { name: 'DAX' })).toBeInTheDocument();
    expect(screen.getByText('TP-00000000')).toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();

    const link = screen.getByRole('link', {
      name: 'Produktauswahl für diesen TradePlan öffnen',
    });
    expect(link).toHaveAttribute(
      'href',
      `/product-selection?trade_plan_id=${approvedPlan.id}&trade_plan_version_id=${approvedPlan.latest_version_id}`,
    );
  });

  it('shows a helpful empty state when no approved plan exists', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify([draftPlan]), { status: 200 }),
    );

    render(
      <MemoryRouter initialEntries={['/product-selection']}>
        <ProductSelectionWorkflowPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { name: 'Kein freigegebener TradePlan verfügbar' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zu den TradePlans' })).toHaveAttribute(
      'href',
      '/trade-plans/overview',
    );
  });
});
