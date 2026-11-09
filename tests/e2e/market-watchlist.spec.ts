import { expect, test, type Page } from "@playwright/test";
import { chartCatalog } from "../../frontend/src/test/chartFixtures";
import {
  watchlistFixture,
  watchlistSeries,
} from "../../frontend/src/test/watchlistFixtures";
import {
  assertDocumentReflow,
  browserMeasurements,
  nativeScreenshot,
  nativeZoomBrowser,
} from "./support/ux4-native-zoom";

// Synthetic fixtures prove the UI contract, not live provider coverage on a PC.
async function installOverview(page: Page, enabled = true) {
  const calls = { writes: 0, series: 0, inflight: 0, maximum: 0 };
  let state = watchlistFixture(31, enabled);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== "GET") {
      expect(url.pathname).toBe("/api/api/v1/market-charts/watchlist/activate");
      expect(request.postDataJSON()).toEqual({
        catalog_version: state.catalog_version,
        confirmed: true,
      });
      calls.writes += 1;
      state = watchlistFixture(31, true);
      return route.fulfill({ json: state });
    }
    if (url.pathname.endsWith("/market-charts/watchlist"))
      return route.fulfill({ json: state });
    if (url.pathname.endsWith("/market-charts/catalog"))
      return route.fulfill({ json: chartCatalog() });
    if (url.pathname.endsWith("/market-charts/series")) {
      calls.series += 1;
      calls.inflight += 1;
      calls.maximum = Math.max(calls.maximum, calls.inflight);
      expect(url.searchParams.getAll("target")).toHaveLength(1);
      // Make concurrency observable instead of relying on immediate fixture responses.
      await new Promise((resolve) => setTimeout(resolve, 20));
      await route.fulfill({
        json: watchlistSeries(
          url.searchParams.get("target")!,
          url.searchParams.get("start_date"),
          url.searchParams.get("end_date")!,
          (url.searchParams.get("price_field") ?? "CLOSE") as
            | "CLOSE"
            | "ADJUSTED_CLOSE",
        ),
      });
      calls.inflight -= 1;
      return;
    }
    if (url.pathname.endsWith("/underlyings"))
      return route.fulfill({
        json: { items: [], total: 0, limit: 50, offset: 0 },
      });
    return route.fulfill({ json: [] });
  });
  return calls;
}

test("one activation persists all 31 charts; local controls keep the same reads", async ({
  page,
}) => {
  const calls = await installOverview(page, false);
  await page.goto("/market-charts");
  await expect(page.getByRole("article")).toHaveCount(31);
  expect(calls.series).toBe(0);
  await page
    .getByRole("button", { name: "Marktübersicht einrichten", exact: true })
    .click();
  await expect(page.locator('[data-testid^="watchlist-chart-"]')).toHaveCount(
    31,
  );
  await expect.poll(() => calls.series).toBe(31);
  expect(calls.writes).toBe(1);
  expect(calls.maximum).toBeLessThanOrEqual(4);
  const first = page.getByRole("article").first();
  await first
    .getByText("Werte, Quellen und Einrichtung", { exact: true })
    .click();
  await expect(first.getByRole("table")).toBeVisible();
  const source = first.getByRole("link", { name: "Indexquelle", exact: true });
  await source.focus();
  await expect(source).toBeFocused();
  await first
    .getByRole("checkbox", { name: "Für Vergleich vormerken" })
    .check();
  await page.getByLabel("Übersicht filtern").fill("ETF 30");
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.getByLabel("Übersicht filtern").clear();
  await page.getByLabel("Gruppe", { exact: true }).selectOption("Anleihen");
  await expect(page.getByRole("article")).toHaveCount(15);
  await page.getByLabel("Gruppe", { exact: true }).selectOption("");
  expect(calls.series).toBe(31);
  expect(calls.writes).toBe(1);
  await page.reload();
  await expect(page.locator('[data-testid^="watchlist-chart-"]')).toHaveCount(
    31,
  );
  await expect(
    page.getByRole("button", {
      name: "Marktübersicht einrichten",
      exact: true,
    }),
  ).toHaveCount(0);
  expect(calls.writes).toBe(1);
});

for (const width of [320, 390, 1280]) {
  test(`overview reflows at ${width}px with locally scrolling source tables`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await installOverview(page);
    await page.goto("/market-charts");
    await expect(page.locator('[data-testid^="watchlist-chart-"]')).toHaveCount(
      31,
    );
    await page
      .getByRole("article")
      .first()
      .getByText("Werte, Quellen und Einrichtung", { exact: true })
      .click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await testInfo.attach(`watchlist-${width}px`, {
      body: await page.screenshot({ fullPage: false }),
      contentType: "image/png",
    });
  });
}

for (const scale of [2, 4]) {
  test(`overview native Chromium zoom ${scale * 100}% retains reflow and keyboard sources`, async ({
    baseURL,
  }, testInfo) => {
    test.setTimeout(90_000);
    const { context, page, setZoom } = await nativeZoomBrowser(testInfo);
    try {
      const calls = await installOverview(page);
      await page.goto((baseURL ?? "http://127.0.0.1:8080") + "/market-charts");
      await expect(
        page.locator('[data-testid^="watchlist-chart-"]'),
      ).toHaveCount(31);
      await expect.poll(() => calls.series).toBe(31);
      const before = calls.series;
      const zoom = await setZoom(scale);
      const first = page.getByRole("article").first();
      await first
        .getByText("Werte, Quellen und Einrichtung", { exact: true })
        .click();
      await expect(first.getByRole("table")).toBeVisible();
      const source = first.getByRole("link", {
        name: "Indexquelle",
        exact: true,
      });
      await source.focus();
      await expect(source).toBeFocused();
      await assertDocumentReflow(page);
      expect(calls.series).toBe(before);
      expect(calls.writes).toBe(0);
      await testInfo.attach(`watchlist-native-zoom-${scale * 100}.json`, {
        body: Buffer.from(
          JSON.stringify(
            { ...zoom, ...(await browserMeasurements(page)) },
            null,
            2,
          ),
        ),
        contentType: "application/json",
      });
      await nativeScreenshot(
        context,
        page,
        testInfo,
        `watchlist-native-zoom-${scale * 100}`,
      );
    } finally {
      await context.close();
    }
  });
}
