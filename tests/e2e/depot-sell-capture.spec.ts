import { expect, test, type Route } from '@playwright/test';

const tradeId = '10000000-0000-4000-8000-000000000010';
const positionId = '10000000-0000-4000-8000-000000000011';
const productId = '10000000-0000-4000-8000-000000000012';
const now = '2026-09-09T18:00:00Z';
const tradeManagementRoute =
  /\/api\/api\/v1\/trade-position\/trades\/10000000-0000-4000-8000-000000000010(?:\/.*)?(?:\?.*)?$/;

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

test('captures a partial sale from the operational depot without manual trade id lookup', async ({
  page,
}) => {
  let openQuantity = 10;
  let salePosts = 0;

  await page.route('**/api/api/v1/operational-workspace/actions', (route) =>
    json(route, { generated_at: now, actions: [] }),
  );
  await page.route('**/api/api/v1/operational-workspace/positions', (route) =>
    json(route, {
      generated_at: now,
      positions:
        openQuantity > 0
          ? [
              {
                trade_id: tradeId,
                position_id: positionId,
                product_name: 'DAX Call 19000',
                opened_at: now,
                open_quantity: openQuantity,
                average_entry_price: '2.00',
                cost_basis: String(openQuantity * 2),
                realized_gross_pnl: openQuantity === 10 ? '0' : '2.50',
                stop_price: '1.80',
                target_price: '2.80',
                monitoring_status: 'OK',
                underlying_symbol: 'DAX.INDX',
                valuation_status: 'STALE',
                product_symbol: 'TEST12.STU',
                valuation_currency: 'EUR',
                market_value: null,
                unrealized_gross_pnl: null,
                open_alert_count: 0,
                open_alert_types: [],
                attention_state: 'DATA_HEALTH',
                target: `/trade-management?trade_id=${tradeId}`,
              },
            ]
          : [],
    }),
  );

  await page.route(`**/api/api/v1/warrants/${productId}`, (route) =>
    json(route, {
      id: productId,
      workspace_id: '00000000-0000-4000-8000-000000000001',
      issuer_id: '30000000-0000-4000-8000-000000000001',
      underlying_id: '40000000-0000-4000-8000-000000000001',
      product_family: 'WARRANT',
      display_name: 'DAX Call 19000',
      isin: 'DE000TEST123',
      wkn: 'TEST12',
      lifecycle_status: 'ACTIVE',
      version: 1,
      created_at: now,
      updated_at: now,
    }),
  );

  await page.route(tradeManagementRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (request.method() === 'GET' && path.endsWith(`/trades/${tradeId}`)) {
      return json(route, {
        id: tradeId,
        product_id: productId,
        origin: 'EXTERNAL',
        trade_plan_id: null,
        trade_plan_version_id: null,
        product_selection_id: null,
        product_evaluation_id: null,
        created_at: now,
      });
    }
    if (request.method() === 'GET' && path.endsWith('/position')) {
      return json(route, {
        id: positionId,
        trade_id: tradeId,
        product_id: productId,
        open_quantity: openQuantity,
        cost_basis: String(openQuantity * 2),
        average_entry_price: '2.00',
        realized_gross_pnl: openQuantity === 10 ? '0' : '2.50',
        opened_at: now,
        last_execution_at: now,
        closed_at: null,
        is_closed: false,
      });
    }
    if (request.method() === 'GET' && path.endsWith('/management')) {
      return json(route, {
        trade_id: tradeId,
        stop_price: '1.80',
        target_price: '2.80',
        thesis: 'Trend intact',
        notes: [],
        last_event_at: now,
      });
    }
    if (request.method() === 'POST' && path.endsWith('/sales')) {
      const body = request.postDataJSON() as { quantity: number; price_per_unit: string };
      expect(body).toMatchObject({ quantity: 5, price_per_unit: '2.50' });
      salePosts += 1;
      openQuantity = 5;
      return json(route, { execution: {}, position: {} }, 201);
    }
    return json(route, { code: 'E2E_ROUTE_MISSING', message: path }, 500);
  });

  await page.goto('/workspace');
  await expect(page.getByRole('heading', { name: /Offene Positionen/ })).toBeVisible();
  await expect(page.getByText('Produktkurs: Veraltet')).toBeVisible();

  await page.getByRole('link', { name: 'Verkauf erfassen' }).click();
  await expect(page).toHaveURL(new RegExp(`/trade-management\\?trade_id=${tradeId}$`));
  await expect(page.getByRole('heading', { name: 'OPEN' })).toBeVisible();
  await expect(page.getByLabel('Trade-ID')).toHaveValue(tradeId);
  await expect(page.getByRole("form", { name: "Verkauf erfassen" }).getByText(/keine Broker-Order/i)).toBeVisible();

  await page.getByLabel('Verkaufsmenge').fill('5');
  await page.getByLabel('Verkaufspreis').fill('2.50');
  await page.getByRole('button', { name: 'Teilverkauf erfassen' }).click();

  await expect.poll(() => salePosts).toBe(1);
  await expect(page.getByText('5 offen', { exact: true })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Teilverkauf wurde erfasst');
});
