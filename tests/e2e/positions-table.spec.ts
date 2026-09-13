import { expect, test, type Page } from "@playwright/test";

async function setup(page: Page) {
  let writes = 0;
  const positions = Array.from({ length: 100 }, (_, i) => ({
    trade_id: `trade-${i}`,
    position_id: `position-${i}`,
    product_name: `Optionsschein ${String(i).padStart(3, "0")}`,
    product_wkn: `WK${String(i).padStart(4, "0")}`,
    product_isin: `DE000TEST${String(i).padStart(4, "0")}`,
    underlying_name: "Gemeinsamer Basiswert",
    underlying_symbol: "BASE",
    product_symbol: null,
    opened_at: "2026-09-08T09:00:00Z",
    opened_on: "2026-09-08",
    open_quantity: 100 + i,
    average_entry_price: "0.55",
    cost_basis: "55",
    realized_gross_pnl: "0",
    stop_price: "0.25",
    target_price: "0.9",
    market_value: i === 98 ? null : `${55 + i}`,
    unrealized_gross_pnl: i === 98 ? null : `${i - 50}`,
    valuation_currency: i % 2 ? "CHF" : "EUR",
    valuation_status: i === 98 ? "MISSING" : i % 3 ? "INDICATIVE" : "AVAILABLE",
    monitoring_status: "OK",
    analysis_warning: i % 3 ? "INDICATIVE" : null,
    quote_source: "FIXTURE",
    quote_observed_at: "2026-09-11T14:00:00Z",
    open_alert_count: i === 0 ? 1 : 0,
    open_alert_types: i === 0 ? ["STOP_REACHED"] : [],
    attention_state: i === 0 ? "ALERT" : "OK",
    target: `/trade-management?trade_id=trade-${i}`,
  }));
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    if (req.method() !== "GET") writes++;
    const path = new URL(req.url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/operational-workspace/actions"))
      body = { generated_at: "2026-09-13T09:00:00Z", actions: [] };
    if (path.endsWith("/operational-workspace/positions"))
      body = { generated_at: "2026-09-13T09:00:00Z", positions };
    if (path.endsWith("/alert-projection")) {
      const id = path.split("/").at(-2)!;
      body = {
        trade_id: id,
        position_id: id.replace("trade-", "position-"),
        quality_status: "AVAILABLE",
        alert_level: "NORMAL",
        attention_required: false,
        reason: "NO_POSITION_ATTENTION_REQUIRED",
        candidate_stop: null,
        latest_price: null,
        phase: null,
        policy_version: "V1",
        dynamic_stop_policy_version: "V1",
        analysis_run_id: null,
      };
    }
    // Navigation may open a management page, but must never record a trade.
    if (path.includes("/trade-position/trades/"))
      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Fixture navigation only",
          code: "NOT_FOUND",
        }),
      });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  return () => writes;
}

test("100 positions: global search, colored statuses, pagination, details and return context without writes", async ({
  page,
}, testInfo) => {
  const writes = await setup(page);
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Offene Positionen · 100" }),
  ).toBeVisible();
  await expect(page.locator("tbody > tr")).toHaveCount(25);
  await expect(
    page.getByText("! Kritischer Hinweis", { exact: true }),
  ).toHaveClass(/text-rose-200/);
  await page.getByRole("button", { name: "Nächste Seite" }).click();
  await expect(page.getByRole("status")).toContainText("Seite 2 von 4");
  const search = page.getByRole("searchbox");
  await search.fill("DE000TEST0099");
  await expect(page.locator("tbody > tr")).toHaveCount(1);
  await expect(
    page.getByText("Optionsschein 099", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Details", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Details Optionsschein 099" }),
  ).toContainText("Quelle: FIXTURE");
  await page
    .getByRole("link", { name: "Trade verwalten", exact: true })
    .click();
  await expect(page).toHaveURL(/trade-management\?trade_id=trade-99$/);
  await page.goBack();
  await expect(search).toHaveValue("DE000TEST0099");
  await page.getByRole("button", { name: "Ansicht zurücksetzen" }).click();
  await page.getByLabel("Zeilen pro Seite").selectOption("100");
  await expect(page.locator("tbody > tr")).toHaveCount(100);
  await page
    .getByRole("button", { name: "Fachliche Hinweise", exact: true })
    .click();
  await expect(page.locator("tbody > tr")).toHaveCount(1);
  await page.getByRole("button", { name: "Alle offenen Positionen" }).click();
  await page.getByRole("button", { name: /^Nicht realisierter G\/V/ }).click();
  await expect(
    page.getByRole("columnheader", { name: /Nicht realisierter G\/V/ }),
  ).toHaveAttribute("aria-sort", "ascending");
  await expect(page.locator("tbody > tr").last()).toContainText(
    "Optionsschein 098",
  );
  await page.getByLabel("Zeilen pro Seite").selectOption("25");
  await testInfo.attach("Positionsübersicht desktop (synthetische Testdaten)", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  expect(writes()).toBe(0);
});

test("narrow layout: bounded horizontal scroll and keyboard-accessible details and sale navigation", async ({
  page,
}, testInfo) => {
  const writes = await setup(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workspace");
  const search = page.getByRole("searchbox");
  await search.fill("WK0099");
  await expect(
    page.getByText("Optionsschein 099", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  const scroll = page.getByRole("region", {
    name: "Positionstabelle, horizontal und vertikal scrollbar",
  });
  expect(await scroll.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(
    true,
  );
  const details = page.getByRole("button", { name: "Details", exact: true });
  await details.focus();
  await page.keyboard.press("Enter");
  await expect(details).toHaveAttribute("aria-expanded", "true");
  await testInfo.attach("Positionsübersicht mobile (synthetische Testdaten)", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  await page
    .getByRole("link", { name: "Verkauf erfassen", exact: true })
    .click();
  await expect(page).toHaveURL(/trade_id=trade-99#sale-capture$/);
  expect(writes()).toBe(0);
});
