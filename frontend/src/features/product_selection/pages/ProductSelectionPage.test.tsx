import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import { warrantApiClient } from '../../product/services/client';
import { tradePlanOverviewApiClient } from '../../trade_plan/services/overviewClient';

import { productSelectionApiClient } from '../services/client';
import { tradePlanApiClient } from '../../trade_plan/services/client';
import { selectionPlanFixture } from '../test/planContextFixtures';
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

const selectedNotEvaluable = {
  ...runDetail,
  selection: {
    id: '00000000-0000-4000-8000-000000000702',
    run_id: runDetail.run.id,
    product_evaluation_id: runDetail.evaluations[1].id,
    selected_at: '2026-08-16T10:05:00Z',
    selected_by: '00000000-0000-4000-8000-000000000002',
    rationale: 'Brokerdaten manuell geprüft; Quote-Provider derzeit nicht verfügbar.',
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

function CurrentRoute() {
  const location = useLocation();
  return <div data-testid="current-route">{location.search}</div>;
}

async function readyProductChoices() {
  return waitFor(() => {
    expect(screen.getByTestId('current-route').textContent).toBe(`?run_id=${runDetail.run.id}`);
    const buttons = screen.getAllByRole('button', { name: 'Dieses Produkt auswählen' });
    expect(buttons).toHaveLength(2);
    buttons.forEach((button) => expect(button).toBeEnabled());
    return buttons;
  });
}

beforeEach(() => {
  vi.spyOn(productSelectionApiClient, 'listForTradePlanVersion').mockResolvedValue([]);
  vi.spyOn(tradePlanApiClient, 'get').mockResolvedValue(selectionPlanFixture);
  vi.spyOn(tradePlanApiClient, 'version').mockResolvedValue(selectionPlanFixture.latest_version);
  vi.spyOn(warrantApiClient, 'list').mockResolvedValue(
    runDetail.evaluations.map((e, i) => ({
      id: e.warrant_id,
      workspace_id: 'w',
      issuer_id: 'i',
      underlying_id: runDetail.run.underlying_id,
      product_family: 'WARRANT',
      display_name: `Selected warrant ${i}`,
      isin: null,
      wkn: `TEST0${i}`,
      lifecycle_status: 'ACTIVE',
      version: 1,
      created_at: '2026-08-16T10:00:00Z',
      updated_at: '2026-08-16T10:00:00Z',
    })),
  );
  vi.spyOn(tradePlanOverviewApiClient, 'list').mockResolvedValue([]);
});

describe('ProductSelectionPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('keeps not evaluable products selectable while preserving their warning status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(runDetail), { status: 201 }),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          `/product-selection?trade_plan_id=${runDetail.run.trade_plan_id}&trade_plan_version_id=${runDetail.run.trade_plan_version_id}`,
        ]}
      >
        <CurrentRoute />
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeEnabled(),
    );
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));

    const buttons = await readyProductChoices();
    expect(screen.getByText('Produktvergleich')).toBeInTheDocument();
    expect(screen.getByText('NOT_EVALUABLE')).toBeInTheDocument();
    expect(buttons).toHaveLength(2);
    expect(buttons[0]).toBeEnabled();
    expect(buttons[1]).toBeEnabled();
  });

  it('requires a rationale before documenting a not evaluable selection', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(runDetail), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(selectedNotEvaluable), { status: 201 }));
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          `/product-selection?trade_plan_id=${runDetail.run.trade_plan_id}&trade_plan_version_id=${runDetail.run.trade_plan_version_id}`,
        ]}
      >
        <CurrentRoute />
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeEnabled(),
    );
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    const buttons = await readyProductChoices();
    expect(screen.getByText('Produktvergleich')).toBeInTheDocument();
    await user.click(buttons[1]);

    expect(screen.getByText('Bewertung unvollständig')).toBeInTheDocument();
    expect(screen.getByText('Quote missing')).toBeInTheDocument();
    const confirm = screen.getByRole('button', { name: 'Auswahl dokumentieren' });
    expect(confirm).toBeDisabled();

    await user.type(
      screen.getByLabelText('Begründung (erforderlich bei nicht bewertbar)'),
      'Brokerdaten manuell geprüft; Quote-Provider derzeit nicht verfügbar.',
    );
    expect(confirm).toBeEnabled();
    await user.click(confirm);

    await screen.findByText('Produkt ausgewählt');
    const selectionCall = fetchMock.mock.calls.find(([url]) => {
      if (typeof url === 'string') return url.includes('/selection');
      if (url instanceof URL) return url.href.includes('/selection');
      return url.url.includes('/selection');
    });
    expect(selectionCall).toBeDefined();
  });

  it('requires explicit confirmation before documenting a selection', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(runDetail), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(selected), { status: 201 }));
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          `/product-selection?trade_plan_id=${runDetail.run.trade_plan_id}&trade_plan_version_id=${runDetail.run.trade_plan_version_id}`,
        ]}
      >
        <CurrentRoute />
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeEnabled(),
    );
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    const buttons = await readyProductChoices();
    expect(screen.getByText('Produktvergleich')).toBeInTheDocument();
    await user.click(buttons[0]);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Begründung (optional)'), 'Nach Vergleich gewählt');
    await user.click(screen.getByRole('button', { name: 'Auswahl dokumentieren' }));

    await screen.findByText('Produkt ausgewählt');
    expect(screen.getAllByText(runDetail.evaluations[0].warrant_id).length).toBeGreaterThanOrEqual(
      2,
    );
    expect(screen.getAllByText('Selected warrant 0').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(runDetail.evaluations[0].warrant_listing_id)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /tatsächlichen Kauf erfassen/i }),
    ).toBeInTheDocument();
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
      .mockResolvedValueOnce(new Response(JSON.stringify(selected), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(purchaseResponse), { status: 201 }));
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={[
          `/product-selection?trade_plan_id=${runDetail.run.trade_plan_id}&trade_plan_version_id=${runDetail.run.trade_plan_version_id}`,
        ]}
      >
        <CurrentRoute />
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Produkte neu bewerten' })).toBeEnabled(),
    );
    expect(screen.queryByLabelText('TradePlan-ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('TradePlanVersion-ID')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Produkte neu bewerten' }));
    const buttons = await readyProductChoices();
    expect(screen.getByText('Produktvergleich')).toBeInTheDocument();
    await user.click(buttons[0]);
    await user.click(screen.getByRole('button', { name: 'Auswahl dokumentieren' }));
    await screen.findByRole('heading', { name: /tatsächlichen Kauf erfassen/i });

    await user.type(screen.getByLabelText('Kaufmenge'), '10');
    await user.type(screen.getByLabelText('Kaufpreis'), '2,35');
    await user.type(screen.getByLabelText('Ausführungswährung (Code)'), 'EU');
    await user.click(screen.getByRole('button', { name: 'BUY erfassen und Position eröffnen' }));
    expect(await screen.findByText(/dreistelligen Währungscode/)).toBeVisible();
    expect(
      fetchMock.mock.calls.some(([url]) => {
        const address = typeof url === 'string' ? url : url instanceof URL ? url.href : url.url;
        return address.includes('/purchases/from-selection');
      }),
    ).toBe(false);
    await user.type(screen.getByLabelText('Ausführungswährung (Code)'), 'R');
    expect(
      screen.queryByRole('checkbox', { name: /als tatsächliche Währung/ }),
    ).not.toBeInTheDocument();
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
    const purchaseBody = purchaseCall?.[1]?.body;
    if (typeof purchaseBody !== 'string') throw new Error('Expected a JSON purchase request');
    expect(JSON.parse(purchaseBody)).toMatchObject({
      price_per_unit: '2.35',
      currency_confirmation: { currency_code: 'EUR', source: 'USER_CONFIRMED', note: null },
    });
  });
});
