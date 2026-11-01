import { expect, test, type Page, type Route } from "@playwright/test";
import {
  realizedGrossReport,
  reportFilters,
  reportItem,
  reportSource,
} from "../../frontend/src/test/realizedGrossFixtures";

test.use({ serviceWorkers: "block" });

const tradeId = "6b39ab21-3c1d-48cd-a853-43c3828d11d1";
const productId = "1e49ef64-7878-4bf8-933f-f957e1627ffd";
const buyId = "70000000-0000-4000-8000-000000000001";
const saleId = "70000000-0000-4000-8000-000000000005";
const title = "Währungsherkunft dieses Beitrags ungeklärt";
const actionName = "Buchungen und Währungsbestätigungen im Trade prüfen";
const longReference = `https://archive.example/original/${"source".repeat(100)}`;

function pilotReport() {
  const sale = reportItem(saleId, {
    trade_id: tradeId,
    product_id: productId,
    product_name:
      "Synthetischer Optionsschein mit ausführlicher deutscher Produktbezeichnung und langer Quellenreferenz für den schmalen Arbeitsbereich",
    status: "NOT_COMPUTABLE",
    reasons: ["CURRENCY_UNKNOWN"],
    currency_code: null,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
    cost_basis_execution_ids: [buyId],
    currency_confirmation_ids: [`currency-${saleId}`],
    open_quantity_before: 100,
    open_quantity_after: 70,
  });
  const buy = reportSource(buyId, {
    trade_id: tradeId,
    product_id: productId,
    currency_confirmation: null,
    currency_history: [],
    currency_resolution: {
      currency_code: null,
      source: "UNKNOWN",
      source_execution_ids: [],
      confirmation_ids: [],
      reason: "NO_HISTORICAL_EVIDENCE",
    },
  });
  const current = reportSource(saleId, {
    trade_id: tradeId,
    product_id: productId,
    side: "SELL",
    quantity: sale.quantity,
    price_per_unit: sale.price_per_unit,
    executed_at: sale.executed_at,
  });
  current.currency_confirmation = {
    ...current.currency_confirmation!,
    trade_id: tradeId,
    note: `Synthetische Originalabrechnung mit ausführlicher Referenz: bestätigte Verkaufswährung bleibt von der unbekannten Kaufherkunft getrennt. ${longReference}`,
  };
  current.currency_history = [current.currency_confirmation];
  const report = realizedGrossReport({
    items: [sale],
    sources: [buy, current],
  });
  report.summary = {
    status: "NOT_COMPUTABLE",
    total: null,
    total_display: null,
    subtotal: null,
    subtotal_display: null,
    rounding_difference: null,
    rounding_difference_display: null,
  };
  report.counts = {
    ...report.counts,
    examined: 1,
    in_period: 1,
    candidates: 1,
    usable: 0,
    unresolved: 1,
  };
  return report;
}

async function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

// The pilot consumes one already-read report. All other API/provider requests
// and every mutation fail here before they can reach a real service.
async function installReport(page: Page, baseURL: string | undefined) {
  if (!baseURL) throw new Error("An explicit frontend baseURL is required.");
  const frontendOrigin = new URL(baseURL).origin;
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const apiBase = new URL(
    process.env.E2E_VITE_API_BASE_URL ??
      process.env.VITE_API_BASE_URL ??
      `http://localhost:${frontendPort || "8080"}/api`,
  );
  const apiPath = `${apiBase.pathname.replace(/\/$/, "")}/api/v1/performance/realized-gross`;
  const reads: string[] = [];
  const unexpected: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      request.method() === "GET" &&
      url.origin === frontendOrigin &&
      !url.pathname.includes("/api/") &&
      ([
        "document",
        "script",
        "stylesheet",
        "image",
        "font",
        "manifest",
      ].includes(request.resourceType()) ||
        url.pathname === "/favicon.ico")
    )
      return route.continue();
    if (
      request.method() !== "GET" ||
      url.origin !== apiBase.origin ||
      url.pathname !== apiPath
    ) {
      unexpected.push(`${request.method()} ${url}`);
      return json(
        route,
        {
          code: "UNEXPECTED_TEST_REQUEST",
          message: "Unexpected pilot request",
        },
        500,
      );
    }
    reads.push(url.toString());
    return json(route, pilotReport());
  });
  return { reads, unexpected, errors };
}

for (const width of [320, 390, 1280]) {
  test(`currency notice: keyboard, report-bound action and no extra requests at ${width}px`, async ({
    page,
    baseURL,
  }, testInfo) => {
    const observed = await installReport(page, baseURL);
    await page.setViewportSize({ width, height: 900 });
    const query = new URLSearchParams({
      report_context: "realized-gross",
      ...reportFilters,
      report_view: "all",
      report_page: "1",
      report_basis: "a".repeat(64),
    });
    await page.goto(`/performance/realized-gross?${query}`);
    const sourceButton = page.getByRole("button", {
      name: "Quellen und Berechnung",
      exact: true,
    });
    await expect(sourceButton).toBeVisible();
    expect(observed.reads).toHaveLength(1);
    await sourceButton.focus();
    await page.keyboard.press("Enter");
    const card = page.getByRole("region", { name: title, exact: true });
    await expect(card).toBeVisible();
    await expect(card.getByText("Warnung", { exact: true })).toBeVisible();
    await expect(card).toContainText(
      "Der Bericht kann den Bruttobeitrag dieses Verkaufs derzeit nicht berechnen.",
    );
    const primary = await card.evaluate((element) => {
      const copy = element.cloneNode(true) as HTMLElement;
      copy.querySelectorAll("details").forEach((details) => details.remove());
      return copy.textContent ?? "";
    });
    expect(primary).not.toMatch(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
    );
    const summary = card
      .locator("summary")
      .filter({ hasText: "Ursache und Quellen" });
    await expect(
      page.getByRole("button", { name: "Quellen schließen", exact: true }),
    ).toBeFocused();
    // Exercise native keyboard focus, including summary; jsdom does not model
    // this browser behavior and the production renderer needs no key handler.
    for (let step = 0; step < 3; step += 1) {
      await page.keyboard.press("Tab");
      if (
        await summary.evaluate((element) => element === document.activeElement)
      )
        break;
    }
    await expect(summary).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(card.locator("details")).toHaveAttribute("open", "");
    await expect(card.locator("details")).toContainText(buyId);
    await page.keyboard.press("Space");
    await expect(card.locator("details")).not.toHaveAttribute("open", "");
    await expect(summary).toBeFocused();
    const action = card.getByRole("link", { name: actionName, exact: true });
    const actionFollows = await summary.evaluate((element) => {
      const link = element.closest("section")!.querySelector("a")!;
      return Boolean(
        element.compareDocumentPosition(link) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      );
    });
    await page.keyboard.press(actionFollows ? "Tab" : "Shift+Tab");
    await expect(action).toBeFocused();
    expect(
      await action.evaluate((element) => {
        const style = getComputedStyle(element);
        return (
          style.boxShadow !== "none" ||
          (style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0)
        );
      }),
    ).toBe(true);
    const target = new URL((await action.getAttribute("href"))!, page.url());
    expect(target.pathname).toBe("/trade-management");
    expect(target.hash).toBe("#execution-dates");
    expect(Object.fromEntries(target.searchParams)).toEqual({
      ...Object.fromEntries(query),
      trade_id: tradeId,
    });
    const prefix = page.getByRole("list", {
      name: "Kostenbasispräfix und Verkauf",
      exact: true,
    });
    const saleSource = prefix.getByRole("listitem", {
      name: `Buchungsquelle ${saleId}`,
      exact: true,
    });
    const provenance = saleSource
      .locator("summary")
      .filter({ hasText: "Verwendete Währungsherkunft" });
    await provenance.focus();
    await page.keyboard.press("Enter");
    await expect(
      saleSource
        .getByText(
          /Synthetische Originalabrechnung mit ausführlicher Referenz:/,
        )
        .first(),
    ).toBeVisible();
    await expect(
      saleSource.getByText(/Währung EUR ausdrücklich vom Nutzer bestätigt/),
    ).toBeVisible();
    await expect(
      saleSource.getByText(longReference, { exact: false }).first(),
    ).toBeVisible();
    await expect(saleSource.getByRole("link")).toHaveCount(0);
    await expect
      .poll(() =>
        saleSource.evaluate(
          (element) => element.scrollWidth <= element.clientWidth,
        ),
      )
      .toBe(true);
    const history = page
      .locator("summary")
      .filter({ hasText: "Gesamte gelesene Trade-Historie" });
    await history.focus();
    await page.keyboard.press("Space");
    await expect(
      page.getByRole("list", { name: "Gesamte Trade-Historie", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: title, exact: true }),
    ).toHaveCount(1);
    await expect(
      page.getByRole("link", { name: actionName, exact: true }),
    ).toHaveCount(1);
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(card.locator('[role="status"], [aria-live]')).toHaveCount(0);
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      )
      .toBe(true);
    await expect
      .poll(() =>
        card.evaluate((element) => element.scrollWidth <= element.clientWidth),
      )
      .toBe(true);
    expect(observed.reads).toHaveLength(1);
    expect(observed.unexpected).toEqual([]);
    expect(observed.errors).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`ux3-currency-notice-${width}.png`),
      fullPage: true,
    });
    await testInfo.attach("ux3-notice-requests", {
      body: JSON.stringify(observed, null, 2),
      contentType: "application/json",
    });
  });
}
