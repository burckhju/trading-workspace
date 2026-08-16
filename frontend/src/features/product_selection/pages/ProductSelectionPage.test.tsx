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
    const selectionCall = fetchMock.mock.calls.find(([url]) => {
      if (typeof url === 'string') return url.includes('/selection');
      if (url instanceof URL) return url.href.includes('/selection');
      return url.url.includes('/selection');
    });
    expect(selectionCall).toBeDefined();
  });
});
