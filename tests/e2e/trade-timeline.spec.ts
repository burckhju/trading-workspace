import { expect, test, type Route } from "@playwright/test";

const tradeId = "10000000-0000-4000-8000-000000000010";
const positionId = "10000000-0000-4000-8000-000000000011";
const productId = "10000000-0000-4000-8000-000000000012";
const now = "2026-09-06T10:00:00Z";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

test("refreshes immutable timeline after a captured partial sale", async ({ page }) => {
  let openQuantity = 100;
  const timeline = [
    {
      id: "20000000-0000-4000-8000-000000000001",
      trade_id: tradeId,
      occurred_at: "2026-09-01T08:00:00Z",
      recorded_at: "2026-09-01T08:00:00Z",
      kind: "EXECUTION",
      execution_side: "BUY",
      management_event_type: null,
      quantity: 100,
      price_per_unit: "2.00",
      numeric_value: null,
      text_value: null,
      supersedes_id: null,
    },
  ];

  await page.route(/\/api\/api\/v1\/.*/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (method === "GET" && path.endsWith(`/trade-position/trades/${tradeId}`)) {
      return json(route, {
        id: tradeId,
        product_id: productId,
        origin: "WORKSPACE_SELECTION",
        trade_plan_id: "10000000-0000-4000-8000-000000000013",
        trade_plan_version_id: "10000000-0000-4000-8000-000000000014",
        product_selection_id: "10000000-0000-4000-8000-000000000015",
        product_evaluation_id: "10000000-0000-4000-8000-000000000016",
        created_at: now,
      });
    }
    if (method === "GET" && path.endsWith(`/trade-position/trades/${tradeId}/position`)) {
      return json(route, {
        id: positionId,
        trade_id: tradeId,
        product_id: productId,
        open_quantity: openQuantity,
        cost_basis: openQuantity === 100 ? "200.00" : "120.00",
        average_entry_price: "2.00",
        realized_gross_pnl: openQuantity === 100 ? "0" : "20.00",
        opened_at: "2026-09-01T08:00:00Z",
        last_execution_at: now,
        closed_at: null,
        is_closed: false,
      });
    }
    if (method === "GET" && path.endsWith(`/trade-position/trades/${tradeId}/management`)) {
      return json(route, {
        trade_id: tradeId,
        stop_price: "23900",
        target_price: "25000",
        thesis: null,
        notes: [],
        last_event_at: null,
      });
    }
    if (method === "GET" && path.endsWith(`/trade-position/trades/${tradeId}/timeline`)) {
      return json(route, timeline);
    }
    if (method === "POST" && path.endsWith(`/trade-position/trades/${tradeId}/sales`)) {
      const body = request.postDataJSON() as { quantity: number; price_per_unit: string };
      openQuantity -= body.quantity;
      timeline.push({
        id: "20000000-0000-4000-8000-000000000002",
        trade_id: tradeId,
        occurred_at: now,
        recorded_at: now,
        kind: "EXECUTION",
        execution_side: "SELL",
        management_event_type: null,
        quantity: body.quantity,
        price_per_unit: body.price_per_unit,
        numeric_value: null,
        text_value: null,
        supersedes_id: null,
      });
      return json(
        route,
        {
          execution: {
            id: "20000000-0000-4000-8000-000000000002",
            trade_id: tradeId,
            product_id: productId,
            side: "SELL",
            quantity: body.quantity,
            price_per_unit: body.price_per_unit,
            gross_amount: "100.00",
            executed_at: now,
            recorded_at: now,
          },
          position: {
            id: positionId,
            trade_id: tradeId,
            product_id: productId,
            open_quantity: openQuantity,
            cost_basis: "120.00",
            average_entry_price: "2.00",
            realized_gross_pnl: "20.00",
            opened_at: "2026-09-01T08:00:00Z",
            last_execution_at: now,
            closed_at: null,
            is_closed: false,
          },
        },
        201,
      );
    }
    if (method === "GET" && path.endsWith(`/warrants/${productId}`)) {
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
    if (method === "GET" && path.endsWith(`/alerts/trades/${tradeId}`)) return json(route, []);
    if (method === "GET" && path.endsWith(`/position-monitoring/trades/${tradeId}/health`)) {
      return json(route, {
        trade_id: tradeId,
        position_id: positionId,
        status: "OK",
        reason: "COMPLETED_DAILY_PRICE_CURRENT",
        symbol: "DAX.INDX",
        trading_date: "2026-09-04",
        market_data_observed_at: "2026-09-04T20:00:00Z",
        age_days: 2,
      });
    }
    return json(route, { code: "E2E_ROUTE_MISSING", message: `${method} ${path}` }, 500);
  });

  await page.goto(`/trade-management?trade_id=${tradeId}`);
  await expect(page.getByRole("heading", { name: "Trade Timeline" })).toBeVisible();
  await expect(page.getByText("Kauf erfasst", { exact: true })).toBeVisible();

  await page.getByLabel("Verkaufsmenge").fill("40");
  await page.getByLabel("Verkaufspreis").fill("2.50");
  await page.getByRole("button", { name: "Teilverkauf erfassen" }).click();

  await expect(page.getByText("Verkauf erfasst", { exact: true })).toBeVisible();
  await expect(page.getByText("40 Stück · 2,5 je Einheit", { exact: true })).toBeVisible();
  await expect(page.getByText("60 offen", { exact: true })).toBeVisible();
});
