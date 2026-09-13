import { expect, test, type Route } from '@playwright/test';

test.use({ timezoneId: 'Europe/Berlin' });

const tradePlanId = '71000000-0000-4000-8000-000000000001';
const versionId = '71000000-0000-4000-8000-000000000002';
const underlyingId = '71000000-0000-4000-8000-000000000003';
const runId = '71000000-0000-4000-8000-000000000004';
const evaluationId = '71000000-0000-4000-8000-000000000005';
const selectionId = '71000000-0000-4000-8000-000000000006';
const productId = '71000000-0000-4000-8000-000000000007';
const tradeId = '71000000-0000-4000-8000-000000000008';
const positionId = '71000000-0000-4000-8000-000000000009';
const actorId = '71000000-0000-4000-8000-000000000010';
const now = '2026-09-09T20:00:00Z';

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

const summary = {
  id: runId,
  trade_plan_id: tradePlanId,
  trade_plan_version_id: versionId,
  trade_plan_version_status: 'APPROVED',
  underlying_id: underlyingId,
  evaluated_at: now,
  universe_model: { model_id: 'ft008-universe', model_version: '1.0.0' },
  eligibility_model: { model_id: 'ft008-eligibility', model_version: '1.0.0' },
  evaluation_model: { model_id: 'ft008-evaluation', model_version: '1.0.0' },
  created_at: now,
  created_by: actorId,
};

const evaluation = {
  id: evaluationId,
  run_id: runId,
  warrant_id: productId,
  warrant_terms_version_id: '71000000-0000-4000-8000-000000000011',
  warrant_listing_id: '71000000-0000-4000-8000-000000000012',
  evaluated_at: now,
  eligibility_model: { model_id: 'ft008-eligibility', model_version: '1.0.0' },
  evaluation_model: { model_id: 'ft008-evaluation', model_version: '1.0.0' },
  inputs: [],
  criteria: [],
  metrics: [],
  eligibility_status: 'ELIGIBLE',
  reasons: [],
};

const selectedDetail = {
  run: summary,
  evaluations: [evaluation],
  universe_omissions: [],
  selection: {
    id: selectionId,
    run_id: runId,
    product_evaluation_id: evaluationId,
    selected_at: now,
    selected_by: actorId,
    rationale: 'Aktuelle Auswahl',
  },
};

const purchaseResponse = {
  trade: {
    id: tradeId,
    product_id: productId,
    origin: 'WORKSPACE_SELECTION',
    trade_plan_id: tradePlanId,
    trade_plan_version_id: versionId,
    product_selection_id: selectionId,
    product_evaluation_id: evaluationId,
    created_at: now,
  },
  execution: {
    id: '71000000-0000-4000-8000-000000000013',
    trade_id: tradeId,
    product_id: productId,
    side: 'BUY',
    quantity: 10,
    price_per_unit: '2.40',
    gross_amount: '24.00',
    executed_at: now,
    recorded_at: now,
  },
  position: {
    id: positionId,
    trade_id: tradeId,
    product_id: productId,
    open_quantity: 10,
    cost_basis: '24.00',
    average_entry_price: '2.40',
    realized_gross_pnl: '0',
    opened_at: now,
    last_execution_at: now,
    closed_at: null,
    is_closed: false,
  },
};

test('successful BUY hands off to the operational workspace without a hard reload', async ({ page }) => {
  let purchased = false;
  let purchasePosts = 0;

  await page.route(/\/api\/api\/v1\/product-selection-runs(?:\/.*)?(?:\?.*)?$/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === 'GET' && url.pathname.endsWith(`/${runId}`)) {
      return json(route, selectedDetail);
    }
    if (request.method() === 'GET' && url.searchParams.get('trade_plan_version_id') === versionId) {
      return json(route, [summary]);
    }
    return json(route, { code: 'E2E_ROUTE_MISSING', message: `${request.method()} ${url.pathname}` }, 500);
  });

  await page.route('**/api/api/v1/trade-position/purchases/from-selection', async (route) => {
    const request = route.request();
    expect(request.postDataJSON()).toEqual({
      product_selection_id: selectionId,
      quantity: 10,
      price_per_unit: '2.40',
      executed_on: '2026-08-17',
      execution_timezone: 'Europe/Berlin',
      request_id: expect.stringMatching(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/),
    });
    purchasePosts += 1;
    purchased = true;
    return json(route, purchaseResponse, 201);
  });

  await page.route('**/api/api/v1/operational-workspace/actions', (route) =>
    json(route, {
      generated_at: now,
      actions: purchased
        ? [
            {
              id: `trade:${tradeId}:open-position`,
              source_feature: 'FT-009/FT-010 Trade Management',
              action_type: 'OPEN_POSITION_MANAGEMENT',
              priority: 'ACTION',
              state: 'ACTIONABLE',
              title: 'Offene Position verwalten',
              detail: 'Die Position ist offen.',
              resource_type: 'trade',
              resource_id: tradeId,
              next_action: 'Trade-Management öffnen',
              target: `/trade-management?trade_id=${tradeId}`,
              occurred_at: now,
            },
          ]
        : [
            {
              id: `product-selection:${selectionId}:initial-buy`,
              source_feature: 'FT-008/FT-009 Product Selection → Trade',
              action_type: 'INITIAL_PURCHASE',
              priority: 'ACTION',
              state: 'ACTIONABLE',
              title: 'Kauf erfassen',
              detail: 'Der tatsächliche BUY fehlt noch.',
              resource_type: 'product_selection',
              resource_id: selectionId,
              next_action: 'BUY erfassen',
              target: `/product-selection?run_id=${runId}`,
              occurred_at: now,
            },
          ],
    }),
  );
  await page.route('**/api/api/v1/operational-workspace/positions', (route) =>
    json(route, {
      generated_at: now,
      positions: purchased
        ? [
            {
              trade_id: tradeId,
              position_id: positionId,
              product_name: 'Handoff Warrant',
              opened_at: now,
              open_quantity: 10,
              average_entry_price: '2.40',
              cost_basis: '24.00',
              realized_gross_pnl: '0',
              stop_price: null,
              target_price: null,
              monitoring_status: 'OK',
              underlying_symbol: 'TEST.INDX',
              valuation_status: 'UNAVAILABLE',
              product_symbol: 'HANDOFF.STU',
              valuation_currency: 'EUR',
              market_value: null,
              unrealized_gross_pnl: null,
              open_alert_count: 0,
              open_alert_types: [],
              attention_state: 'NORMAL',
              target: `/trade-management?trade_id=${tradeId}`,
            },
          ]
        : [],
    }),
  );

  await page.goto(`/product-selection?run_id=${runId}`);
  await expect(page.getByRole('heading', { name: /tatsächlichen Kauf erfassen/i })).toBeVisible();
  await page.getByLabel('Kaufdatum', { exact: true }).fill('2026-08-17');
  await page.getByLabel('Kaufmenge').fill('10');
  await page.getByLabel('Kaufpreis').fill('2.40');
  await page.getByRole('button', { name: 'BUY erfassen und Position eröffnen' }).click();

  await expect.poll(() => purchasePosts).toBe(1);
  await expect(page.getByText(/Kauf wurde als BUY erfasst/)).toBeVisible();
  await expect(page.getByText('Offene Position', { exact: true })).toBeVisible();

  await page.getByRole('link', { name: 'Arbeitsbereich' }).click();
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByRole('heading', { name: /Offene Positionen/ })).toBeVisible();
  await expect(page.getByText('Kauf erfassen', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Offene Position verwalten', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Verkauf erfassen' })).toBeVisible();
});
