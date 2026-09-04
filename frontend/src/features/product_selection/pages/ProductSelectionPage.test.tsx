import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProductSelectionPage } from './ProductSelectionPage';

const runDetail = {
  run: {
    id: '00000000-0000-4000-8000-000000000101',
    trade_plan_id: '00000000-0000-4000-8000-000000000201',
    trade_plan_version_id: '00000000-0000-4000-8000-000000000202',
    trade_plan_version_status: 'APPROVED',
    underlying_id: '00000000-0000-4000-8000-000000000301',
    evaluated_at: '2026-08-16T10:00:00Z',
    universe_model: { model_id: 'universe', model_version: '1' },
    eligibility_model: { model_id: 'eligibility', model_version: '1' },
    evaluation_model: { model_id: 'evaluation', model_version: '1' },
    created_at: '2026-08-16T10:00:00Z',
    created_by: '00000000-0000-4000-8000-000000000002',
  },
  evaluations: [
    {
      id: '00000000-0000-4000-8000-000000000401',
      run_id: '00000000-0000-4000-8000-000000000101',
      warrant_id: '00000000-0000-4000-8000-000000000501',
      warrant_terms_version_id: '00000000-0000-4000-8000-000000000502',
      warrant_listing_id: '00000000-0000-4000-8000-000000000503',
      evaluated_at: '2026-08-16T10:00:00Z',
      eligibility_model: { model_id: 'eligibility', model_version: '1' },
      evaluation_model: { model_id: 'evaluation', model_version: '1' },
      inputs: [],
      criteria: [],
      metrics: [],
      eligibility_status: 'ELIGIBLE',
      reasons: [],
    },
    {
      id: '00000000-0000-4000-8000-000000000402',
      run_id: '00000000-0000-4000-8000-000000000101',
      warrant_id: '00000000-0000-4000-8000-000000000601',
      warrant_terms_version_id: '00000000-0000-4000-8000-000000000602',
      warrant_listing_id: '00000000-0000-4000-8000-000000000603',
      evaluated_at: '2026-08-16T10:00:00Z',
      eligibility_model: { model_id: 'eligibility', model_version: '1' },
      evaluation_model: { model_id: 'evaluation', model_version: '1' },
      inputs: [],
      criteria: [],
      metrics: [],
      eligibility_status: 'NOT_EVALUABLE',
      reasons: ['Quote missing'],
    },
  ],
  universe_omissions: [],
  selection: null,
};

const selected = {
  ...runDetail,
  selection: {
    id: '00000000-0000-4000-8000-000000000701',
    run_id: runDetail.run.id,
    product_evaluation_id: runDetail.evaluations[0].id,
    selected_at: '2026-08-16T10:05:00Z',
    selected_by: '00000000-0000-4000-8000-000000000002',
    rationale: 'Nach Vergleich gewählt',
  },
};

const purchaseResponse = {
  trade: {
    id: '12345678-0000-4000-8000-000000000801',
    product_id: runDetail.evaluations[0].warrant_id,
    origin: 'WORKSPACE_SELECTION',
    trade_plan_id: runDetail.run.trade_plan_id,
    trade_plan_version_id: runDetail.run.trade_plan_version_id,
    product_selection_id: selected.selection.id,
    product_evaluation_id: runDetail.evaluations[0].id,
    created_at: '2026-08-16T10:06:00Z',
  },
  execution: {
    id: '00000000-0000-4000-8000-000000000802',
    trade_id: '12345678-0000-4000-8000-000000000801',
    product_id: runDetail.evaluations[0].warrant_id,
    side: 'BUY',
    quantity: 10,
    price_per_unit: '2.35',
    gross_amount: '23.50',
    executed_at: '2026-08-16T10:06:00Z',
    recorded_at: '2026-08-16T10:06:01Z',
  },
  position: {
    id: '00000000-0000-4000-8000-000000000803',
    trade_id: '12345678-0000-4000-8000-000000000801',
    product_id: runDetail.evaluations[0].warrant_id,
    open_quantity: 10,
    cost_basis: '23.50',
    average_entry_price: '2.35',
    realized_gross_pnl: '0',
    opened_at: '2026-08-16T10:06:00Z',
    last_execution_at: '2026-08-16T10:06:00Z',
    closed_at: null,
    is_closed: false,
  },
};

describe('ProductSelectionPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('shows transparent statuses and disables selection for not evaluable products', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(runDetail), { status: 201 }),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('TradePlan-ID'), runDetail.run.trade_plan_id);
    await user.type(
      screen.getByLabelText('TradePlanVersion-ID'),
      runDetail.run.trade_plan_version_id,
    );
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));

    await waitFor(() => expect(screen.getByText('Produktvergleich')).toBeInTheDocument());
    expect(screen.getByText('NOT_EVALUABLE')).toBeInTheDocument();
    const buttons = screen.getAllByRole('button', { name: 'Dieses Produkt auswählen' });
    expect(buttons).toHaveLength(2);
    expect(buttons[0]).toBeEnabled();
    expect(buttons[1]).toBeDisabled();
  });

  it('requires explicit confirmation before documenting a selection', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(runDetail), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(selected), { status: 201 }));
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('TradePlan-ID'), runDetail.run.trade_plan_id);
    await user.type(
      screen.getByLabelText('TradePlanVersion-ID'),
      runDetail.run.trade_plan_version_id,
    );
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    await screen.findByText('Produktvergleich');
    await user.click(screen.getAllByRole('button', { name: 'Dieses Produkt auswählen' })[0]);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Begründung (optional)'), 'Nach Vergleich gewählt');
    await user.click(screen.getByRole('button', { name: 'Auswahl dokumentieren' }));

    await screen.findByText('Produkt ausgewählt');
    expect(screen.getByText(runDetail.evaluations[0].warrant_id)).toBeInTheDocument();
    expect(screen.getByText(runDetail.evaluations[0].warrant_listing_id)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /tatsächlichen Kauf erfassen/i })).toBeInTheDocument();
    const selectionCall = fetchMock.mock.calls.find(([url]) => {
      if (typeof url === 'string') return url.includes('/selection');
      if (url instanceof URL) return url.href.includes('/selection');
      return url.url.includes('/selection');
    });
    expect(selectionCall).toBeDefined();
  });

  it('captures the actual BUY and hands the open position to trade management', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(runDetail), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(selected), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(purchaseResponse), { status: 201 }));
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('TradePlan-ID'), runDetail.run.trade_plan_id);
    await user.type(
      screen.getByLabelText('TradePlanVersion-ID'),
      runDetail.run.trade_plan_version_id,
    );
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    await screen.findByText('Produktvergleich');
    await user.click(screen.getAllByRole('button', { name: 'Dieses Produkt auswählen' })[0]);
    await user.click(screen.getByRole('button', { name: 'Auswahl dokumentieren' }));
    await screen.findByRole('heading', { name: /tatsächlichen Kauf erfassen/i });

    await user.type(screen.getByLabelText('Kaufmenge'), '10');
    await user.type(screen.getByLabelText('Kaufpreis'), '2,35');
    await user.click(screen.getByRole('button', { name: 'BUY erfassen und Position eröffnen' }));

    expect(await screen.findByRole('heading', { name: 'TR-12345678' })).toBeInTheDocument();
    expect(screen.getByText('23.50')).toBeInTheDocument();
    expect(screen.getByText(/Position ist jetzt die wirtschaftliche Wahrheit/)).toBeInTheDocument();

    const managementLink = screen.getByRole('link', {
      name: 'Position verwalten und Monitoring öffnen',
    });
    expect(managementLink).toHaveAttribute(
      'href',
      '/trade-management?trade_id=12345678-0000-4000-8000-000000000801',
    );

    const purchaseCall = fetchMock.mock.calls.find(([url]) => {
      if (typeof url === 'string') return url.includes('/purchases/from-selection');
      if (url instanceof URL) return url.href.includes('/purchases/from-selection');
      return url.url.includes('/purchases/from-selection');
    });
    expect(purchaseCall).toBeDefined();
  });
});
