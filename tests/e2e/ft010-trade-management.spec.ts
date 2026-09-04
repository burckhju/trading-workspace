import { expect, test, type Route } from "@playwright/test";

const tradeId = "10000000-0000-4000-8000-000000000010";
const positionId = "10000000-0000-4000-8000-000000000011";
const productId = "10000000-0000-4000-8000-000000000012";
const tradePlanId = "10000000-0000-4000-8000-000000000013";
const now = "2026-08-17T10:00:00Z";
const tradeManagementRoute =
  /\/api\/api\/v1\/trade-position\/trades\/10000000-0000-4000-8000-000000000010(?:\/.*)?(?:\?.*)?$/;
const warrantRoute =
  /\/api\/api\/v1\/warrants\/10000000-0000-4000-8000-000000000012(?:\?.*)?$/;

function position(overrides: Record<string, unknown> = {}) {
  return {
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
    ...overrides,
  };
}

function management(overrides: Record<string, unknown> = {}) {
  return {
    trade_id: tradeId,
    stop_price: "1.80",
    target_price: "2.80",
    thesis: "Initial thesis",
    notes: [],
    last_event_at: now,
    ...overrides,
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

test("manages partial/full exit and explicit management decisions without provider dependency", async ({
  page,
}) => {
  let currentPosition = position();
  let currentManagement = management();
  let salePosts = 0;
  let stopPosts = 0;
  let targetPosts = 0;
  let thesisPosts = 0;
  let notePosts = 0;

  await page.route(warrantRoute, async (route) => {
    return json(route, {
      id: productId,
      workspace_id: "00000000-0000-4000-8000-000000000001",
      issuer_id: "30000000-0000-4000-8000-000000000001",
      underlying_id: "40000000-0000-4000-8000-000000000001",
      product_family: "WARRANT",
      display_name: "DAX Call 19000",
      isin: "DE000TEST123",
      wkn: "TEST12",
      lifecycle_status: "ACTIVE",
      version: 1,
      created_at: now,
      updated_at: now,
    });
  });

  await page.route(tradeManagementRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (method === "GET" && path.endsWith(`/trades/${tradeId}`)) {
      return json(route, {
        id: tradeId,
        product_id: productId,
        origin: "WORKSPACE_SELECTION",
        trade_plan_id: tradePlanId,
        trade_plan_version_id: "10000000-0000-4000-8000-000000000014",
        product_selection_id: "10000000-0000-4000-8000-000000000015",
        product_evaluation_id: "10000000-0000-4000-8000-000000000016",
        created_at: now,
      });
    }
    if (method === "GET" && path.endsWith("/position")) {
      return json(route, currentPosition);
    }
    if (method === "GET" && path.endsWith("/management")) {
      return json(route, currentManagement);
    }
    if (method === "POST" && path.endsWith("/sales")) {
      salePosts += 1;
      const body = request.postDataJSON() as {
        quantity: number;
        price_per_unit: string;
        executed_at?: string;
      };
      expect(body).not.toHaveProperty("provider");
      expect(body).not.toHaveProperty("broker");
      expect(body).not.toHaveProperty("exit_type");
      expect(body).not.toHaveProperty("realized_gross_pnl");

      if (salePosts === 1) {
        expect(body).toMatchObject({ quantity: 40, price_per_unit: "2.50" });
        currentPosition = position({
          open_quantity: 60,
          cost_basis: "120.00",
          realized_gross_pnl: "20.00",
          last_execution_at: now,
        });
      } else {
        expect(body).toMatchObject({ quantity: 60, price_per_unit: "2.40" });
        currentPosition = position({
          open_quantity: 0,
          cost_basis: "0",
          realized_gross_pnl: "44.00",
          closed_at: now,
          is_closed: true,
        });
      }
      return json(
        route,
        {
          execution: {
            id: `20000000-0000-4000-8000-00000000001${salePosts}`,
            trade_id: tradeId,
            product_id: productId,
            side: "SELL",
            quantity: body.quantity,
            price_per_unit: body.price_per_unit,
            gross_amount: String(Number(body.price_per_unit) * body.quantity),
            executed_at: now,
            recorded_at: now,
          },
          position: currentPosition,
        },
        201,
      );
    }
    if (method === "POST" && path.endsWith("/management/stop")) {
      stopPosts += 1;
      const body = request.postDataJSON() as { price: string };
      currentManagement = { ...currentManagement, stop_price: body.price };
      return json(route, {}, 201);
    }
    if (method === "POST" && path.endsWith("/management/target")) {
      targetPosts += 1;
      const body = request.postDataJSON() as { price: string };
      currentManagement = { ...currentManagement, target_price: body.price };
      return json(route, {}, 201);
    }
    if (method === "POST" && path.endsWith("/management/thesis")) {
      thesisPosts += 1;
      const body = request.postDataJSON() as { text: string };
      currentManagement = { ...currentManagement, thesis: body.text };
      return json(route, {}, 201);
    }
    if (method === "POST" && path.endsWith("/management/notes")) {
      notePosts += 1;
      const body = request.postDataJSON() as { text: string };
      currentManagement = {
        ...currentManagement,
        notes: [...currentManagement.notes, body.text],
      };
      return json(route, {}, 201);
    }
    return json(
      route,
      { code: "E2E_ROUTE_MISSING", message: `${method} ${path}` },
      500,
    );
  });

  await page.goto(`/trade-management?trade_id=${tradeId}`);
  await expect(page.getByRole("heading", { name: "OPEN" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /TR-10000000 · DAX Call 19000/ })).toBeVisible();
  await expect(page.getByText("TP-10000000")).toBeVisible();
  await expect(page.getByText("100 offen")).toBeVisible();

  await page.getByLabel("Verkaufsmenge").fill("40");
  await page.getByLabel("Verkaufspreis").fill("2.50");
  await page.getByRole("button", { name: "SELL speichern" }).click();
  await expect.poll(() => salePosts).toBe(1);
  await expect(page.getByText("60 offen")).toBeVisible();
  await expect(page.getByText("20", { exact: true })).toBeVisible();

  await page.getByLabel("Stop").fill("1.90");
  await page.getByRole("button", { name: "Stop speichern" }).click();
  await expect.poll(() => stopPosts).toBe(1);

  await page.getByLabel("Target").fill("3.00");
  await page.getByRole("button", { name: "Target speichern" }).click();
  await expect.poll(() => targetPosts).toBe(1);

  await page.getByLabel("Aktuelle These").fill("Thesis updated by user");
  await page.getByRole("button", { name: "These speichern" }).click();
  await expect.poll(() => thesisPosts).toBe(1);

  await page
    .getByLabel("Neue Management-Notiz")
    .fill("Observed volatility after partial exit");
  await page.getByRole("button", { name: "Notiz hinzufügen" }).click();
  await expect.poll(() => notePosts).toBe(1);
  await expect(
    page.getByText("Observed volatility after partial exit"),
  ).toBeVisible();

  await page.getByLabel("Verkaufsmenge").fill("60");
  await page.getByLabel("Verkaufspreis").fill("2.40");
  await page.getByRole("button", { name: "SELL speichern" }).click();
  await expect.poll(() => salePosts).toBe(2);
  await expect(page.getByRole("heading", { name: "CLOSED" })).toBeVisible();
  await expect(
    page.getByText(
      "Die Position ist geschlossen. Weitere SELL-Executions sind nicht verfügbar.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "SELL speichern" }),
  ).toHaveCount(0);
});
