import { expect, test } from "@playwright/test";

const tradeId = "dd8338bd-a092-42c0-94c0-c068a9094f77";

for (const [kind, refreshError] of [
  ["LAST_TRADE", null], ["PREVIOUS_CLOSE", null],
  ["LAST_TRADE", "FRANKFURT_HTTP_503"], ["PREVIOUS_CLOSE", "FRANKFURT_REQUEST_THROTTLED"],
] as const) {
  test(`shows Frankfurt ${kind} ${refreshError ?? "success"} analysis and provenance without permitting an order`, async ({
    page,
  }) => {
    let writes = 0;
    await page.route("**/api/**", async (route) => {
      const request = route.request();
      if (request.method() !== "GET") writes += 1;
      const path = new URL(request.url()).pathname;
      let body: unknown = {};
      if (path.includes("/alerts/") || path.endsWith("/timeline")) {
        body = [];
      } else if (path.endsWith("/position")) {
        body = {
          id: "9f1e7034-3977-4600-a37c-de119d7e8d8c",
          trade_id: tradeId,
          open_quantity: 2000,
          cost_basis: "1020",
          average_entry_price: "0.51",
          realized_gross_pnl: "0",
          is_closed: false,
          closed_at: null,
        };
      } else if (path.endsWith("/product-valuation")) {
        body = {
          trade_id: tradeId,
          status: "INDICATIVE",
          reason: refreshError ? "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED" : "REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS",
          bid: null,
          ask: null,
          currency: "EUR",
          quote_observed_at: null,
          quote_age_seconds: null,
          reference_price: "0.231",
          reference_price_type: kind,
          market_value: null,
          unrealized_gross_pnl: null,
          analysis_market_value: "462.000",
          analysis_unrealized_gross_pnl: "-558.000",
          analysis_usable: true,
          monitoring_usable: true,
          valuation_usable: false,
          execution_usable: false,
          analysis_warning: refreshError ? "QUOTE_REFRESH_FAILED_INDICATIVE_ANALYSIS_ONLY" : "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
          quote_refresh_error: refreshError,
          selected_source: "FRANKFURT_QUOTES",
          provider_identity: "DE000VH2LU21",
          provider_exchange_code: "XSC",
          quote_venue_mic: "XFRA",
          quote_delay_seconds: null,
          quote_retrieved_at: "2026-09-12T10:00:00Z",
          source_attempts: [],
        };
      } else if (path.endsWith(`/trades/${tradeId}`)) {
        body = {
          id: tradeId,
          product_id: "8ee5ab84-86ce-491e-b4b0-d98a0379d0c3",
          origin: "WORKSPACE_SELECTION",
        };
      } else if (path.includes("/warrants/")) {
        body = {
          id: "8ee5ab84-86ce-491e-b4b0-d98a0379d0c3",
          display_name: "UnitedHealth Call",
          isin: "DE000VH2LU21",
          wkn: "VH2LU2",
        };
      } else if (path.endsWith("/management")) {
        body = {
          trade_id: tradeId,
          stop_price: null,
          target_price: null,
          thesis: null,
          notes: [],
        };
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });
    await page.goto(`/trade-management?trade_id=${tradeId}`);
    const panel = page.locator("section").filter({
      has: page.getByRole("heading", {
        name: "Produktbewertung",
        exact: true,
      }),
    });
    await expect(
      panel.getByText("Indikative Auswertung", { exact: true }),
    ).toBeVisible();
    await expect(panel.getByText("462 EUR", { exact: true })).toBeVisible();
    await expect(panel.getByText("-558 EUR", { exact: true })).toBeVisible();
    await expect(panel.getByRole("status")).toContainText(
      refreshError ? "letzter erfolgreicher Abruf" : "Kurszeitpunkt unbekannt",
    );
    await expect(panel.getByText(/Bewertungsquelle:/)).toContainText(
      "DE000VH2LU21",
    );
    await expect(panel.getByText(/Handelsplatz:/)).toContainText("XFRA");
    await expect(panel.getByText(/Handelsplatz:/)).toContainText(
      "Feed-Verzögerung: unbekannt",
    );
    await expect(
      panel.getByText("Marktwert (Bid)", { exact: true }),
    ).toHaveCount(0);
    await expect(
      panel.getByText(/keine Freigabe zur Orderausführung/),
    ).toBeVisible();
    if (refreshError) await expect(panel.getByRole("status")).toContainText(refreshError);
    expect(writes).toBe(0);
  });
}
