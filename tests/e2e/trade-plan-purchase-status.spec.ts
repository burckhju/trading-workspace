import { expect, test } from "@playwright/test";

test("TradePlans: fixture purchase status, previous versions, filter, refresh and read-only links", async ({
  page,
}, testInfo) => {
  const trade = {
    trade_id: "original-trade",
    trade_plan_version_id: "v1",
    plan_version: 1,
    product_id: "original-product",
    product_name: "Gekaufter Optionsschein",
    product_isin: "DE000TEST1234",
    product_wkn: "TEST12",
    status: "OPEN",
    open_quantity: 5,
    purchased_on: "2026-08-17",
    purchased_at: "2026-08-16T22:00:00Z",
    closed_on: null,
    closed_at: null,
  };
  const base = {
    underlying_id: "stock",
    underlying_name: "Gemeinsamer Basiswert",
    origin_type: "MANUAL",
    created_at: "2026-09-13T10:00:00Z",
    latest_version_id: "v2",
    latest_version: 2,
    status: "APPROVED",
  };
  let writes = 0;
  let bought = false;
  await page.route("**/api/**", async (route) => {
    if (route.request().method() !== "GET") writes++;
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/trade-plans")) {
      const items = [
        {
          ...base,
          id: "unbought",
          underlying_name: "Plan ohne Kauf",
          execution: {
            status: bought ? "OPEN" : "NOT_STARTED",
            current_version_status: bought ? "OPEN" : "NOT_STARTED",
            trades: bought
              ? [
                  {
                    ...trade,
                    trade_id: "new-trade",
                    trade_plan_version_id: "v2",
                    plan_version: 2,
                  },
                ]
              : [],
          },
        },
        {
          ...base,
          id: "started",
          underlying_name: "Plan mit Kauf",
          execution: {
            status: "OPEN",
            current_version_status: "NOT_STARTED",
            trades: [trade],
          },
        },
        {
          ...base,
          id: "closed",
          underlying_name: "Abgeschlossener Plan",
          execution: {
            status: "CLOSED",
            current_version_status: "CLOSED",
            trades: [
              {
                ...trade,
                trade_id: "closed-trade",
                status: "CLOSED",
                open_quantity: 0,
                closed_on: "2026-09-10",
                closed_at: "2026-09-09T22:00:00Z",
              },
            ],
          },
        },
        {
          ...base,
          id: "cancelled",
          underlying_name: "Stornierter Plan",
          execution: {
            status: "CANCELLED",
            current_version_status: "CANCELLED",
            trades: [
              { ...trade, trade_id: "cancelled-trade", status: "CANCELLED" },
            ],
          },
        },
        { ...base, id: "legacy", underlying_name: "Status nicht verfügbar" },
      ];
      return route.fulfill({ json: items });
    }
    return route.fulfill({
      status: 404,
      json: { code: "NOT_FOUND", message: "Fixture navigation only" },
    });
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/trade-plans/overview");
  const unbought = page
    .locator("article")
    .filter({
      has: page.getByRole("heading", { name: "Plan ohne Kauf", exact: true }),
    });
  const started = page
    .locator("article")
    .filter({
      has: page.getByRole("heading", { name: "Plan mit Kauf", exact: true }),
    });
  await expect(
    unbought.getByText("Noch kein Kauf erfasst", { exact: true }),
  ).toBeVisible();
  await expect(
    started.getByText("Kauf erfasst · Position offen", { exact: true }),
  ).toHaveClass(/text-emerald-200/);
  await expect(started).toContainText(
    "Aktuelle Version 2: Noch kein Kauf erfasst",
  );
  await expect(started).toContainText("Kaufdatum: 17.08.2026");
  await expect(started).toContainText(
    "Gekaufter Optionsschein · Planversion 1",
  );
  await expect(
    started.getByRole("link", { name: "Trade verwalten / Nachkauf" }),
  ).toHaveAttribute("href", "/trade-management?trade_id=original-trade");
  await expect(
    page.getByText("Vollständig verkauft: 10.09.2026"),
  ).toBeVisible();
  await expect(
    page.getByText("Stornierte Fehleingabe; zählt nicht als offene Position."),
  ).toBeVisible();
  await expect(
    page.locator("article").filter({ hasText: "Status nicht verfügbar" }),
  ).toContainText("Kaufstatus ungeklärt");
  await page
    .getByRole("combobox", { name: "Nach Kaufstatus filtern" })
    .selectOption("NOT_STARTED");
  await expect(page.locator("article")).toHaveCount(1);
  await expect(page.getByRole("status")).toHaveText("1 von 5 TradePlans");
  bought = true;
  await page.getByRole("button", { name: "Übersicht aktualisieren" }).click();
  await expect(
    page.getByText("Keine TradePlans mit diesem Kaufstatus."),
  ).toBeVisible();
  await page.getByRole("combobox").selectOption("OPEN");
  await expect(page.locator("article")).toHaveCount(2);
  await testInfo.attach("TradePlan-Kaufstatus (synthetische Testdaten)", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  await started
    .getByRole("link", { name: "Trade verwalten / Nachkauf" })
    .click();
  await expect(page).toHaveURL(/trade-management\?trade_id=original-trade$/);
  await page.goto("/trade-plans/overview");
  await expect(
    unbought.getByText("Kauf erfasst · Position offen", { exact: true }),
  ).toBeVisible();
  expect(writes).toBe(0);
});
