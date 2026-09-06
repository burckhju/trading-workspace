import { expect, test, type Route } from "@playwright/test";

const tradeId = "10000000-0000-4000-8000-000000000010";
const positionId = "10000000-0000-4000-8000-000000000011";
const productId = "10000000-0000-4000-8000-000000000012";
const now = "2026-09-06T10:00:00Z";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

test("shows stale underlying data as data health and not as a trading alert", async ({ page }) => {
  await page.route(/\/api\/api\/v1\/.*/, async (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path.endsWith(`/trade-position/trades/${tradeId}`)) {
      return json(route, {
        id: tradeId,
        product_id: productId,
        origin: "WORKSPACE_SELECTION",
        trade_plan_id: "10000000-0000-4000-8000-000000000013",
        trade_plan_version_id: "10000000-0000-4000-8000-000000000014",
        product_selection_id: "10000000-0000-4000-8000-000000000015",
        product_evaluation_id: null,
        created_at: now,
      });
    }
    if (path.endsWith(`/trade-position/trades/${tradeId}/position`)) {
      return json(route, {
        id: positionId,
        trade_id: tradeId,
        product_id: productId,
        open_quantity: 100,
        cost_basis: "200.00",
        average_entry_price: "2.00",
        realized_gross_pnl: "0",
        opened_at: now,
        last_execution_at: now,
        closed_at: null,
        is_closed: false,
      });
    }
    if (path.endsWith(`/trade-position/trades/${tradeId}/management`)) {
      return json(route, {
        trade_id: tradeId,
        stop_price: "23900",
        target_price: "25000",
        thesis: null,
        notes: [],
        last_event_at: null,
      });
    }
    if (path.endsWith(`/warrants/${productId}`)) {
      return json(route, {
        id: productId,
        workspace_id: "00000000-0000-4000-8000-000000000001",
        issuer_id: "30000000-0000-4000-8000-000000000001",
        underlying_id: "40000000-0000-4000-8000-000000000001",
        product_family: "WARRANT",
        display_name: "DAX Call 24000",
        isin: "DE000TEST123",
        wkn: "TEST12",
        lifecycle_status: "ACTIVE",
        version: 1,
        created_at: now,
        updated_at: now,
      });
    }
    if (path.endsWith(`/alerts/trades/${tradeId}`)) {
      return json(route, []);
    }
    if (path.endsWith(`/position-monitoring/trades/${tradeId}/health`)) {
      return json(route, {
        trade_id: tradeId,
        position_id: positionId,
        status: "STALE",
        reason: "COMPLETED_DAILY_PRICE_STALE",
        symbol: "DAX.INDX",
        trading_date: "2026-09-01",
        market_data_observed_at: "2026-09-01T20:00:00Z",
        age_days: 5,
      });
    }
    return json(route, { code: "E2E_ROUTE_MISSING", message: path }, 500);
  });

  await page.goto(`/trade-management?trade_id=${tradeId}`);

  await expect(page.getByText("Daten veraltet")).toBeVisible();
  await expect(page.getByText("STALE", { exact: true })).toBeVisible();
  await expect(page.getByText("DAX.INDX")).toBeVisible();
  await expect(
    page.getByText(/Daraus wird kein Stop-\/Target-Alert abgeleitet/i),
  ).toBeVisible();
  await expect(page.getByText("Für diesen Trade liegen noch keine Alerts vor.")).toBeVisible();
});
