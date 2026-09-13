import { expect, test } from "@playwright/test";
import type { TradePlanOverviewItem } from "../../frontend/src/features/trade_plan/services/overviewClient";
import type { ProductSelectionRunDetailResponse } from "../../frontend/src/features/product_selection/types/api";

// Synthetic read-only API fixtures, not a browser-to-database booking test.
const selected = {
  run_id: "synthetic-run-alpha",
  product_evaluation_id: "synthetic-evaluation-alpha",
  warrant_id: "synthetic-warrant-alpha",
  display_name: "Synthetischer Call Alpha",
  isin: "DE000SYN0001",
  wkn: "SYN001",
};
const item: TradePlanOverviewItem = {
  id: "12345678-0000-4000-8000-000000000001",
  underlying_id: "synthetic-underlying",
  underlying_name: "Synthetischer gemeinsamer Basiswert",
  underlying_isin: "US000SYN0001",
  underlying_wkn: "BAS001",
  origin_type: "MANUAL",
  created_at: "2026-09-01T10:00:00Z",
  latest_version_id: "synthetic-version-2",
  latest_version: 2,
  status: "APPROVED",
  selected_product: selected,
  execution: {
    status: "OPEN",
    current_version_status: "NOT_STARTED",
    trades: [
      {
        trade_id: "synthetic-purchased-trade",
        trade_plan_version_id: "synthetic-version-1",
        plan_version: 1,
        product_id: "synthetic-purchased-warrant",
        product_name: "Tatsächlich gekaufter Call Beta",
        product_isin: "DE000SYN0002",
        product_wkn: "SYN002",
        status: "OPEN",
        open_quantity: 5,
        purchased_on: "2026-08-17",
        purchased_at: null,
        closed_on: null,
        closed_at: null,
      },
    ],
  },
};
const model = { model_id: "synthetic-model", model_version: "1" };
const run: ProductSelectionRunDetailResponse = {
  run: {
    id: selected.run_id,
    trade_plan_id: item.id,
    trade_plan_version_id: item.latest_version_id,
    trade_plan_version_status: "APPROVED",
    underlying_id: item.underlying_id,
    evaluated_at: "2026-09-01T10:00:00Z",
    universe_model: model,
    eligibility_model: model,
    evaluation_model: model,
    created_at: "2026-09-01T10:00:00Z",
    created_by: "synthetic-actor",
  },
  evaluations: [
    {
      id: selected.product_evaluation_id,
      run_id: selected.run_id,
      warrant_id: selected.warrant_id,
      warrant_terms_version_id: "synthetic-terms",
      warrant_listing_id: "synthetic-listing",
      evaluated_at: "2026-09-01T10:00:00Z",
      eligibility_model: model,
      evaluation_model: model,
      inputs: [],
      criteria: [],
      metrics: [],
      reasons: [],
      eligibility_status: "ELIGIBLE",
    },
  ],
  selection: {
    id: "synthetic-selection",
    run_id: selected.run_id,
    product_evaluation_id: selected.product_evaluation_id,
    selected_at: "2026-09-01T10:00:00Z",
    selected_by: "synthetic-actor",
    rationale: "Synthetic fixture only",
  },
  universe_omissions: [],
};

for (const width of [1280, 390]) {
  test(`TradePlan warrant identity and read-only selection handoff at ${width}px`, async ({
    page,
  }, testInfo) => {
    const requests: string[] = [];
    const writes: string[] = [];
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/**", async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      if (request.method() !== "GET") {
        writes.push(`${request.method()} ${pathname}`);
        return route.fulfill({
          status: 405,
          json: { message: "Fixture forbids writes" },
        });
      }
      requests.push(pathname);
      if (pathname.endsWith("/trade-plans")) {
        return route.fulfill({
          json: [
            item,
            {
              ...item,
              id: "87654321-0000-4000-8000-000000000002",
              selected_product: {
                ...selected,
                run_id: "synthetic-run-gamma",
                warrant_id: "synthetic-warrant-gamma",
                display_name: `Synthetischer Call Gamma ${"LangerProduktname".repeat(8)}`,
                isin: "DE000SYN0003",
                wkn: "SYN003",
              },
              execution: {
                status: "NOT_STARTED",
                current_version_status: "NOT_STARTED",
                trades: [],
              },
            },
          ],
        });
      }
      if (pathname.endsWith(`/product-selection-runs/${selected.run_id}`)) {
        return route.fulfill({ json: run });
      }
      if (pathname.endsWith("/product-selection-runs")) {
        return route.fulfill({ json: [run.run] });
      }
      if (pathname.endsWith("/warrants")) {
        return route.fulfill({
          json: [
            {
              id: selected.warrant_id,
              workspace_id: "synthetic-workspace",
              issuer_id: "synthetic-issuer",
              underlying_id: item.underlying_id,
              product_family: "WARRANT",
              display_name: selected.display_name,
              isin: selected.isin,
              wkn: selected.wkn,
              lifecycle_status: "ACTIVE",
              version: 1,
              created_at: "2026-09-01T10:00:00Z",
              updated_at: "2026-09-01T10:00:00Z",
            },
          ],
        });
      }
      return route.fulfill({
        status: 404,
        json: { message: "No synthetic fixture for this read" },
      });
    });
    await page.goto("/trade-plans/overview");
    const card = page.locator("article").filter({ hasText: "TP-12345678" });
    const selection = card.getByRole("region", {
      name: "Optionsschein-Auswahl",
    });
    await expect(
      selection.getByRole("heading", { name: selected.display_name }),
    ).toBeVisible();
    await expect(selection).toContainText("WKN SYN001 · ISIN DE000SYN0001");
    await expect(selection).toContainText("Version 2");
    await expect(selection).toContainText(
      "Eine Produktauswahl ist kein Kaufnachweis.",
    );
    await expect(selection).not.toContainText("BAS001");
    await expect(selection).not.toContainText("SYN002");
    await expect(card.getByText("Basiswert", { exact: true })).toBeVisible();
    await expect(
      card.getByRole("region", { name: "Kaufstatus" }),
    ).toContainText("Tatsächlich gekaufter Call Beta · Planversion 1");
    await expect(
      card.getByRole("region", { name: "Kaufstatus" }),
    ).toContainText("SYN002");
    const other = page.locator("article").filter({ hasText: "TP-87654321" });
    await expect(
      other.getByRole("region", { name: "Optionsschein-Auswahl" }),
    ).toContainText("SYN003");
    await expect(other).not.toContainText("SYN001");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    expect(
      requests.filter((path) => /warrants|product-selection-runs/.test(path)),
    ).toEqual([]);
    await testInfo.attach(
      `Optionsschein-Identität ${width}px (synthetische Daten)`,
      {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      },
    );
    const link = selection.getByRole("link", {
      name: "Ausgewählten Optionsschein prüfen",
    });
    await link.focus();
    await expect(link).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(
      /product-selection\?run_id=synthetic-run-alpha$/,
    );
    await expect(
      page.getByText(`Kauf für: ${selected.display_name}`, { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "BUY erfassen und Position eröffnen" }),
    ).toBeDisabled();
    expect(
      requests.some((path) =>
        path.endsWith(`/product-selection-runs/${selected.run_id}`),
      ),
    ).toBe(true);
    expect(writes).toEqual([]);
  });
}
