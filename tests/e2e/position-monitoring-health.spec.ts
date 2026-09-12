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

for (const valuationStatus of ["STALE", "LAST_AVAILABLE"] as const) {
  test(`shows ${valuationStatus} product analysis with warning separately from stale underlying alerts`, async ({
    page,
  }) => {
    const mutations: string[] = [];
    await page.route(/\/api\/api\/v1\/.*/, async (route) => {
      if (route.request().method() !== "GET") {
        mutations.push(route.request().url());
        return json(route, { message: "Analysis must be read-only" }, 405);
      }
      const path = new URL(route.request().url()).pathname;

      if (path.endsWith(`/trade-position/trades/${tradeId}`)) {
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
      if (
        path.endsWith(
          `/position-monitoring/trades/${tradeId}/product-valuation`,
        )
      ) {
        return json(route, {
          trade_id: tradeId,
          position_id: positionId,
          status: valuationStatus,
          reason:
            valuationStatus === "STALE"
              ? "WARRANT_QUOTE_STALE"
              : "MARKET_CLOSED_LAST_AVAILABLE_QUOTE",
          warrant_listing_id: "10000000-0000-4000-8000-000000000017",
          symbol: null,
          bid: "2.50",
          ask: "2.55",
          currency: "EUR",
          quote_observed_at: "2026-09-04T19:59:13Z",
          quote_age_seconds: 136847,
          max_quote_age_seconds: 3600,
          market_value: valuationStatus === "STALE" ? null : "250.00",
          unrealized_gross_pnl: valuationStatus === "STALE" ? null : "50.00",
          selected_source: "VONTOBEL_MARKETS",
          valuation_usable: valuationStatus === "LAST_AVAILABLE",
          execution_usable: false,
          analysis_usable: true,
          analysis_warning: "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY",
          analysis_market_value: "250.00",
          analysis_unrealized_gross_pnl: "50.00",
          source_attempts: [],
        });
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

    await expect(
      page.getByText("Daten veraltet", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("STALE", { exact: true })).toBeVisible();
    await expect(page.getByText("DAX.INDX", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/Daraus wird kein Stop-\/Target-Alert abgeleitet/i),
    ).toBeVisible();
    await expect(
      page.getByText("Für diesen Trade liegen noch keine Alerts vor."),
    ).toBeVisible();
    await expect(
      page.getByText("Kursdaten veraltet – nur indikative Analyse"),
    ).toBeVisible();
    await expect(page.getByText(/Kursstand:/)).toContainText("2280 Min.");
    await expect(
      page.getByText("Indikativer Wert (letzter Bid)"),
    ).toBeVisible();
    await expect(page.getByText("250 EUR", { exact: true })).toBeVisible();
    await expect(page.getByText("50 EUR", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/keine Freigabe zur Orderausführung/),
    ).toBeVisible();
    expect(mutations).toEqual([]);
  });
}
