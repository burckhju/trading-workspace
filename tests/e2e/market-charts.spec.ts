import { expect, test, type Page } from "@playwright/test";
import {
  chartCatalog,
  chartIdentity,
  chartSeries,
  comparison,
} from "../../frontend/src/test/chartFixtures";

async function installChartApi(page: Page) {
  const seriesCalls: string[][] = [];
  const writes: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET") writes.push(url.pathname);
    if (url.pathname.endsWith("/market-charts/catalog"))
      return route.fulfill({ json: chartCatalog() });
    if (url.pathname.endsWith("/market-charts/series")) {
      const keys = url.searchParams.getAll("target");
      seriesCalls.push(keys);
      const series = keys.map((key) =>
        chartSeries(
          key.startsWith("reference:")
            ? chartIdentity()
            : chartIdentity(key, `TEST ${key.split(":")[1]} ETF`, "ETF"),
        ),
      );
      return route.fulfill({
        json: {
          ...comparison(series),
          price_field: url.searchParams.get("price_field"),
        },
      });
    }
    if (url.pathname.includes("/market-charts/underlyings/"))
      return route.fulfill({
        json: {
          underlying_id: "stock",
          subject: chartIdentity("listing:stock", "TEST Stock", "STOCK"),
          market: chartIdentity(),
          sector: chartIdentity("listing:Energy", "TEST Energy ETF", "ETF"),
          issues: [],
          assignment_date: "2026-10-04",
        },
      });
    if (url.pathname.endsWith("/underlyings"))
      return route.fulfill({
        json: { items: [], total: 0, limit: 50, offset: 0 },
      });
    return route.fulfill({ json: [] });
  });
  return { seriesCalls, writes };
}

test("market to sectors and stock: backend values, keyboard tooltip, legend and accessible table", async ({
  page,
}, testInfo) => {
  const requests = await installChartApi(page);
  await page.goto("/market-charts?end=2026-10-04");
  await expect(
    page.getByRole("heading", { name: "Markt, Sektoren und Aktien" }),
  ).toBeVisible();
  await expect(page.locator(".recharts-line-curve")).toHaveCount(1);
  await expect(
    page.getByRole("rowheader", { name: /Industrials/ }),
  ).toBeVisible();
  await expect(page.getByText(/Sektorreferenz fehlt/)).toBeVisible();
  await page
    .getByRole("button", { name: "Vergleichen", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Vergleichen", exact: true })
    .nth(1)
    .click();
  await page.getByLabel("Darstellung").selectOption("normalized");
  await expect(page.locator(".recharts-line-curve")).toHaveCount(3);
  const before = requests.seriesCalls.length;
  await page.getByRole("checkbox", { name: "2. TEST Energy ETF" }).uncheck();
  await expect(page.locator(".recharts-line-curve")).toHaveCount(2);
  await page.getByRole("checkbox", { name: "2. TEST Energy ETF" }).check();
  const chart = page.locator('.recharts-surface[role="application"]');
  await chart.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText(/Quelle: EODHD/).first()).toBeVisible();
  await page.getByLabel("Darstellung").selectOption("change_percent");
  await page
    .getByText("Datentabelle und Quellen – zugängliche Alternative")
    .click();
  await expect(
    page.getByRole("columnheader", { name: "Quellenaktualisierung" }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "20", exact: true }),
  ).toBeVisible();
  expect(requests.seriesCalls).toHaveLength(before);
  expect(requests.writes).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("chart-desktop.png"),
    fullPage: true,
  });
  await page.goto("/market-charts?underlying=stock&end=2026-10-04");
  await page
    .getByRole("button", { name: /Mit zugeordnetem Sektor und Markt/ })
    .click();
  await expect
    .poll(() => requests.seriesCalls.at(-1))
    .toEqual(["listing:stock", "listing:Energy", "reference:sp500"]);
});

test("mobile chart fits the page; tables scroll within their regions", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installChartApi(page);
  await page.goto("/market-charts?end=2026-10-04");
  await expect(page.locator(".recharts-line-curve")).toHaveCount(1);
  await expect(page.getByTestId("time-series-chart")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: testInfo.outputPath("chart-mobile.png"),
    fullPage: true,
  });
});
