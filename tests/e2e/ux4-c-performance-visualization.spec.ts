import { mkdir, writeFile } from "node:fs/promises";
import {
  chromium,
  expect,
  test,
  type Locator,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";
import type {
  ClosedTradeReport,
  RealizedGrossFilters,
  RealizedGrossReport,
} from "../../frontend/src/features/performance/types/api";
import {
  closedTradeItem,
  closedTradeReport,
  closedTradeStatistics,
  unavailableClosedTradeStatistics,
} from "../../frontend/src/test/closedTradesFixtures";
import {
  realizedGrossReport,
  reportItem,
  reportSource,
} from "../../frontend/src/test/realizedGrossFixtures";

test.use({ serviceWorkers: "block" });

type ReportKind = "realized-gross" | "closed-trades";
const filters: RealizedGrossFilters = {
  from_date: "2026-10-01",
  to_date: "2026-10-31",
  report_currency: "EUR",
  report_timezone: "Europe/Berlin",
};
const longRaw = "1.2345678901234567890123456789";
const originalDay = "2026-10-11";

function reportUrl(kind: ReportKind) {
  return `/performance/${kind}?${new URLSearchParams({
    report_context: kind,
    ...filters,
    report_view: "candidates",
    report_page: "1",
  })}`;
}

// These explicit backend-shaped examples qualify presentation only. Neither
// the browser nor this fixture derives a report total or statistics from rows.
function salesReport(): RealizedGrossReport {
  const items = Array.from({ length: 21 }, (_, index) =>
    reportItem(`synthetic-sell-${index + 1}`, {
      executed_at: "2026-10-12T10:00:00Z",
      realized_gross_pnl_delta: "0",
      realized_gross_pnl_delta_display: "0.00",
    }),
  );
  items[1] = reportItem("synthetic-sell-2", {
    status: "NOT_COMPUTABLE",
    period_status: "PERIOD_UNKNOWN",
    reasons: ["PERIOD_UNKNOWN", "CURRENCY_UNKNOWN"],
    time_precision: "UNKNOWN",
    executed_at: null,
    currency_code: null,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
  });
  items[2] = reportItem("synthetic-sell-3", {
    time_precision: "DATE_ONLY",
    executed_at: null,
    executed_on: originalDay,
    execution_timezone: "Asia/Tokyo",
    possible_start_at: "2026-10-10T15:00:00Z",
    possible_end_at: "2026-10-11T15:00:00Z",
    realized_gross_pnl_delta: "2.004",
    realized_gross_pnl_delta_display: "2.00",
  });
  items[3].realized_gross_pnl_delta = "7";
  items[3].realized_gross_pnl_delta_display = "7.00";
  items[4].realized_gross_pnl_delta = "-7";
  items[4].realized_gross_pnl_delta_display = "-7.00";
  items[5].realized_gross_pnl_delta = longRaw;
  items[5].realized_gross_pnl_delta_display = "1.23";
  items[6].realized_gross_pnl_delta = "0.004";
  items[7].realized_gross_pnl_delta = "-0.004";
  items[7].realized_gross_pnl_delta_display = "-0.00";
  items[20] = reportItem("synthetic-sell-21", {
    executed_at: "2026-10-20T10:00:00Z",
    status: "EXCLUDED",
    reasons: ["OTHER_CURRENCY", "CURRENCY_MIXED"],
    currency_code: "USD",
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
  });
  const report = realizedGrossReport({
    filters,
    interval_start_at: "2026-09-30T22:00:00Z",
    interval_end_at: "2026-10-31T23:00:00Z",
    items,
    summary: {
      status: "PARTIAL",
      total: null,
      total_display: null,
      subtotal: "3.2385678901234567890123456789",
      subtotal_display: "3.24",
      rounding_difference: "0.01",
      rounding_difference_display: "0.01",
    },
    counts: {
      examined: 21,
      in_period: 20,
      outside_period: 0,
      period_ambiguous: 0,
      period_unknown: 1,
      candidates: 20,
      usable: 19,
      unresolved: 1,
      excluded: 1,
      cancelled: 0,
    },
  });
  report.sources = [
    ...report.sources.filter((source) =>
      ["buy-august", "sell-august"].includes(source.execution_id),
    ),
    ...items.map((item) => {
      const source = reportSource(item.execution_id, {
        side: "SELL",
        quantity: item.quantity,
        price_per_unit: item.price_per_unit,
        time_precision: item.time_precision,
        executed_at: item.executed_at,
        executed_on: item.executed_on,
        execution_timezone: item.execution_timezone,
        possible_start_at: item.possible_start_at,
        possible_end_at: item.possible_end_at,
      });
      if (item.currency_code === null) {
        source.currency_confirmation = null;
        source.currency_history = [];
        source.currency_resolution = {
          currency_code: null,
          source: "UNKNOWN",
          source_execution_ids: [],
          confirmation_ids: [],
        };
      } else {
        source.currency_confirmation = {
          ...source.currency_confirmation!,
          currency_code: item.currency_code,
        };
        source.currency_history = [source.currency_confirmation];
        source.currency_resolution = {
          ...source.currency_resolution!,
          currency_code: item.currency_code,
        };
      }
      return source;
    }),
  ];
  return report;
}

function referenceClosedReport(): ClosedTradeReport {
  const report = closedTradeReport({
    filters,
    items: [
      closedTradeItem("synthetic-win-1", {
        realized_gross_pnl: "100",
        realized_gross_pnl_display: "100.00",
      }),
      closedTradeItem("synthetic-loss", {
        realized_gross_pnl: "-50",
        realized_gross_pnl_display: "-50.00",
        classification: "NEGATIVE",
      }),
      closedTradeItem("synthetic-neutral", {
        realized_gross_pnl: "0",
        realized_gross_pnl_display: "0.00",
        classification: "NEUTRAL",
      }),
      closedTradeItem("synthetic-win-2", {
        realized_gross_pnl: "200",
        realized_gross_pnl_display: "200.00",
      }),
    ],
    statistics: closedTradeStatistics({
      population: 4,
      win_rate: { raw: "50", display: "50.00", reason: null },
      average_gross_pnl: { raw: "62.5", display: "62.50", reason: null },
      median_gross_pnl: { raw: "50", display: "50.00", reason: null },
      gross_profit_factor: { raw: "6", display: "6.00", reason: null },
    }),
  });
  report.summary = { ...report.summary, total: "250", total_display: "250.00" };
  report.counts = {
    ...report.counts,
    examined: 4,
    qualified: 4,
    in_period: 4,
    positive: 2,
    negative: 1,
    neutral: 1,
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

async function installReports(page: Page, baseURL: string | undefined) {
  if (!baseURL) throw new Error("An explicit frontend baseURL is required.");
  const frontendOrigin = new URL(baseURL).origin;
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const apiBase = new URL(
    process.env.E2E_VITE_API_BASE_URL ??
      process.env.VITE_API_BASE_URL ??
      `http://localhost:${frontendPort || "8080"}/api`,
  );
  const apiPrefix = `${apiBase.pathname.replace(/\/$/, "")}/api/v1`;
  const reads: Array<{ kind: ReportKind; filters: Record<string, string> }> =
    [];
  const unexpected: string[] = [];
  const browserErrors: string[] = [];
  let sales = salesReport();
  let closed = referenceClosedReport();
  let unavailable = false;
  page.on("pageerror", (error) => browserErrors.push(error.message));
  // Match the existing workspace guard: every mutation/provider/unknown fetch
  // is intercepted before it could reach any actual service or user data.
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
    ) {
      return route.continue();
    }
    const kind = (["realized-gross", "closed-trades"] as const).find(
      (candidate) => url.pathname === `${apiPrefix}/performance/${candidate}`,
    );
    if (request.method() !== "GET" || url.origin !== apiBase.origin || !kind) {
      unexpected.push(`${request.method()} ${url}`);
      return json(
        route,
        { code: "UNEXPECTED_TEST_REQUEST", message: "Unexpected request" },
        500,
      );
    }
    const requestedFilters = {
      from_date: url.searchParams.get("from_date") ?? "",
      to_date: url.searchParams.get("to_date") ?? "",
      report_currency: url.searchParams.get("report_currency") ?? "",
      report_timezone: url.searchParams.get("report_timezone") ?? "",
    };
    reads.push({ kind, filters: requestedFilters });
    if (unavailable)
      return json(
        route,
        {
          code: "REPORT_READ_UNAVAILABLE",
          message: "Synthetischer Quellenlesefehler",
        },
        503,
      );
    return json(route, {
      ...(kind === "closed-trades" ? closed : sales),
      filters: requestedFilters,
    });
  });
  return {
    reads,
    unexpected,
    browserErrors,
    setSales: (report: RealizedGrossReport) => {
      sales = report;
    },
    setClosed: (report: ClosedTradeReport) => {
      closed = report;
    },
    setUnavailable: () => {
      unavailable = true;
    },
  };
}

function visual(page: Page) {
  return page.getByRole("region", {
    name: "Einzelne SELL-Beiträge",
    exact: true,
  });
}

function dataTable(page: Page) {
  return visual(page).getByRole("table", {
    name: "SELL-Beiträge und Originalwerte",
    exact: true,
  });
}

function row(page: Page, number: number) {
  return dataTable(page)
    .locator("tbody tr")
    .filter({
      has: page.getByText(`synthetic-sell-${number}`, { exact: true }),
    });
}

async function expectNoDocumentOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
}

async function expectVisibleFocus(target: Locator) {
  await expect(target).toBeFocused();
  expect(
    await target.evaluate((element) => {
      const style = getComputedStyle(element);
      return (
        element.matches(":focus-visible") &&
        ((style.outlineStyle !== "none" &&
          parseFloat(style.outlineWidth) >= 2) ||
          style.boxShadow !== "none")
      );
    }),
  ).toBe(true);
}

async function attachViewport(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(name + ".png");
  await page.screenshot({ path });
  await testInfo.attach(name, { path, contentType: "image/png" });
}

for (const width of [320, 390, 1280]) {
  test(`UX4-C SELL original values, local pages and keyboard sources at ${width}px`, async ({
    page,
    baseURL,
  }, testInfo) => {
    const api = await installReports(page, baseURL);
    await page.setViewportSize({ width, height: 900 });
    await page.goto(reportUrl("realized-gross"));
    const panel = visual(page);
    await expect(panel.getByTestId("sell-contribution-mark")).toHaveCount(19);
    await expect(
      panel.locator(".recharts-line-curve, .recharts-scatter-line"),
    ).toHaveCount(0);
    await expect(dataTable(page).locator("tbody tr")).toHaveCount(20);
    await expect(row(page, 1)).toContainText("0,00 EUR");
    await expect(row(page, 2)).toContainText("Nicht berechenbar");
    await expect(row(page, 2)).not.toContainText("0,00 EUR");
    await expect(row(page, 3)).toContainText(originalDay);
    await expect(row(page, 3)).toContainText("Uhrzeit unbekannt");
    await expect(row(page, 3)).toContainText("Asia/Tokyo");
    await expect(row(page, 3)).not.toContainText("00:00");
    await expect(row(page, 6)).toContainText(longRaw);
    await expect(row(page, 7)).toContainText("0.004");
    await expect(row(page, 8)).toContainText("-0.004");
    // Identical execution times remain independent observations and controls.
    for (const number of [1, 3, 4, 5, 7, 8]) {
      await expect(
        panel.locator(
          `[data-testid="sell-contribution-mark"][data-execution-id="synthetic-sell-${number}"]`,
        ),
      ).toHaveCount(1);
    }
    await expect(
      panel.locator(
        '[data-testid="sell-contribution-mark"][data-execution-id="synthetic-sell-2"]',
      ),
    ).toHaveCount(0);
    await expect(page.getByTestId("realized-gross-total")).toHaveText(
      "Nicht berechenbar",
    );
    await expect(page.getByTestId("realized-gross-subtotal")).toHaveText(
      "3,24 EUR",
    );
    await expectNoDocumentOverflow(page);
    const chartScreenshot = testInfo.outputPath(
      `ux4-c-sell-chart-${width}-synthetic.png`,
    );
    await panel.locator("figure").screenshot({ path: chartScreenshot });
    await testInfo.attach(`UX4-C synthetic SELL chart at ${width}px`, {
      path: chartScreenshot,
      contentType: "image/png",
    });

    const tableRegion = panel.getByRole("region", {
      name: "SELL-Datentabelle",
      exact: true,
    });
    await tableRegion.focus();
    await page.keyboard.press("ArrowRight");
    await expectVisibleFocus(tableRegion);
    if (width <= 390) {
      await expect
        .poll(() => tableRegion.evaluate((element) => element.scrollLeft))
        .toBeGreaterThan(0);
    }
    const next = panel.getByRole("button", {
      name: "Nächste Grafikseite",
      exact: true,
    });
    await next.focus();
    await page.keyboard.press("Enter");
    await expect(dataTable(page).locator("tbody tr")).toHaveCount(1);
    await expect(row(page, 21)).toContainText("synthetic-sell-21");
    await expect(row(page, 21)).toContainText("Ausgeschlossen");
    await expect(panel.getByTestId("sell-contribution-mark")).toHaveCount(0);
    await expect(page.getByTestId("realized-gross-subtotal")).toHaveText(
      "3,24 EUR",
    );
    const source = panel.getByRole("button", {
      name: "Originalquellen zu SELL 21",
      exact: true,
    });
    await source.focus();
    await expectVisibleFocus(source);
    await page.keyboard.press("Enter");
    const original = page.getByRole("article", {
      name: "Verkauf synthetic-sell-21",
      exact: true,
    });
    await expect(original).toBeFocused();
    await expect(
      original.getByRole("button", { name: "Quellen schließen", exact: true }),
    ).toHaveAttribute("aria-expanded", "true");
    await expect(original).toContainText("synthetic-sell-21");
    await expectNoDocumentOverflow(page);
    await testInfo.attach(`UX4-C ${width}px accessible SELL table`, {
      body: Buffer.from(await dataTable(page).ariaSnapshot()),
      contentType: "text/plain",
    });
    expect(api.reads).toHaveLength(1);
    expect(api.unexpected).toEqual([]);
    expect(api.browserErrors).toEqual([]);
  });
}

test("UX4-C display limits preserve exact decimal originals without zero replacement", async ({
  page,
  baseURL,
}) => {
  const api = await installReports(page, baseURL);
  const large = "1" + "0".repeat(120);
  const tiny = "0." + "0".repeat(120) + "1";
  const report = realizedGrossReport({
    filters,
    interval_start_at: "2026-09-30T22:00:00Z",
    interval_end_at: "2026-10-31T23:00:00Z",
    items: [
      reportItem("synthetic-large-positive", {
        executed_at: "2026-10-12T10:00:00Z",
        realized_gross_pnl_delta: large,
        realized_gross_pnl_delta_display: large + ".00",
      }),
      reportItem("synthetic-large-negative", {
        executed_at: "2026-10-12T10:00:00Z",
        realized_gross_pnl_delta: "-" + large,
        realized_gross_pnl_delta_display: "-" + large + ".00",
      }),
      reportItem("synthetic-tiny-positive", {
        executed_at: "2026-10-12T10:00:00Z",
        realized_gross_pnl_delta: tiny,
        realized_gross_pnl_delta_display: "0.00",
      }),
      reportItem("synthetic-tiny-negative", {
        executed_at: "2026-10-12T10:00:00Z",
        realized_gross_pnl_delta: "-" + tiny,
        realized_gross_pnl_delta_display: "-0.00",
      }),
      reportItem("synthetic-exact-zero", {
        executed_at: "2026-10-12T10:00:00Z",
        realized_gross_pnl_delta: "0",
        realized_gross_pnl_delta_display: "0.00",
      }),
    ],
  });
  report.summary = { ...report.summary, total: "0", total_display: "0.00" };
  report.counts = {
    ...report.counts,
    examined: 5,
    candidates: 5,
    in_period: 5,
    usable: 5,
  };
  api.setSales(report);
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto(reportUrl("realized-gross"));
  await expect(visual(page).getByTestId("sell-contribution-mark")).toHaveCount(
    1,
  );
  await expect(
    visual(page).getByTestId("sell-contribution-mark"),
  ).toHaveAttribute("data-execution-id", "synthetic-exact-zero");
  await expect(dataTable(page)).toContainText(large);
  await expect(dataTable(page)).toContainText("-" + large);
  await expect(dataTable(page)).toContainText(tiny);
  await expect(dataTable(page)).toContainText("-" + tiny);
  for (const id of [
    "large-positive",
    "large-negative",
    "tiny-positive",
    "tiny-negative",
  ]) {
    const entry = dataTable(page)
      .locator("tbody tr")
      .filter({ hasText: `synthetic-${id}` });
    await expect(entry).toContainText("grafischen Zahlendarstellung");
  }
  await expectNoDocumentOverflow(page);
  expect(api.reads).toHaveLength(1);
  expect(api.unexpected).toEqual([]);
  expect(api.browserErrors).toEqual([]);
});

for (const failure of ["load", "render"] as const) {
  test(`UX4-C optional chart ${failure} failure preserves the complete keyboard evidence`, async ({
    page,
    baseURL,
  }) => {
    const api = await installReports(page, baseURL);
    let replaced = 0;
    await page.route(
      /\/assets\/RealizedGrossPlot-[^/]+\.js(?:\?.*)?$/,
      async (route) => {
        replaced += 1;
        if (failure === "load") return route.abort("failed");
        return route.fulfill({
          contentType: "application/javascript",
          body: 'export function RealizedGrossPlot() { throw new Error("Synthetic UX4-C chart render failure"); }',
        });
      },
    );
    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto(reportUrl("realized-gross"));
    const panel = visual(page);
    const message = panel.getByText(/^Das Diagramm konnte nicht/);
    await expect(message).toHaveCount(1);
    await expect(message).toContainText(
      `Das Diagramm konnte nicht ${failure === "load" ? "geladen" : "dargestellt"} werden.`,
    );
    await expect(panel.getByRole("alert")).toHaveCount(0);
    expect(replaced).toBeGreaterThan(0);
    await expect(panel.getByTestId("sell-contribution-mark")).toHaveCount(0);
    await expect(dataTable(page).locator("tbody tr")).toHaveCount(20);
    await expect(row(page, 2)).toContainText("Nicht berechenbar");
    await expect(row(page, 3)).toContainText("Uhrzeit unbekannt");
    const region = panel.getByRole("region", {
      name: "SELL-Datentabelle",
      exact: true,
    });
    await region.focus();
    await page.keyboard.press("ArrowRight");
    await expectVisibleFocus(region);
    await expect
      .poll(() => region.evaluate((element) => element.scrollLeft))
      .toBeGreaterThan(0);
    const next = panel.getByRole("button", {
      name: "Nächste Grafikseite",
      exact: true,
    });
    await next.focus();
    await page.keyboard.press("Enter");
    await expect(row(page, 21)).toBeVisible();
    const source = panel.getByRole("button", {
      name: "Originalquellen zu SELL 21",
      exact: true,
    });
    await source.focus();
    await page.keyboard.press("Space");
    const original = page.getByRole("article", {
      name: "Verkauf synthetic-sell-21",
      exact: true,
    });
    await expect(original).toBeFocused();
    await expect(
      original.getByRole("button", { name: "Quellen schließen", exact: true }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);
    expect(api.reads).toHaveLength(1);
    expect(api.unexpected).toEqual([]);
    expect(api.browserErrors).toEqual([]);
  });
}

test("UX4-C keeps SELLs and full trades separate and discards replaced or failed report views", async ({
  page,
  baseURL,
}) => {
  const api = await installReports(page, baseURL);
  await page.goto(reportUrl("realized-gross"));
  await expect(visual(page).getByTestId("sell-contribution-mark")).toHaveCount(
    19,
  );
  await visual(page)
    .getByRole("button", { name: "Nächste Grafikseite", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Trades mit Vollabschluss im Zeitraum",
      exact: true,
    })
    .click();
  await expect(visual(page)).toHaveCount(0);
  await expect(
    page.getByTestId("closed-trades-statistics-population"),
  ).toContainText("Population N = 4");
  await expect(page.getByTestId("closed-trades-total")).toHaveText(
    "250,00 EUR",
  );
  await page
    .getByRole("button", { name: "Verkäufe im Zeitraum", exact: true })
    .click();
  await expect(visual(page).getByTestId("sell-contribution-mark")).toHaveCount(
    19,
  );
  await expect(row(page, 1)).toBeVisible();
  await expect(page.getByTestId("closed-trades-total")).toHaveCount(0);
  expect(api.reads.map((read) => read.kind)).toEqual([
    "realized-gross",
    "closed-trades",
    "realized-gross",
  ]);
  const empty = realizedGrossReport({
    filters,
    interval_start_at: "2026-09-30T22:00:00Z",
    interval_end_at: "2026-10-31T23:00:00Z",
    items: [],
    sources: [],
  });
  empty.basis.id = "c".repeat(64);
  empty.summary = {
    ...empty.summary,
    status: "EMPTY",
    total: "0",
    total_display: "0.00",
    rounding_difference: null,
    rounding_difference_display: null,
  };
  empty.counts = {
    ...empty.counts,
    examined: 0,
    in_period: 0,
    candidates: 0,
    usable: 0,
  };
  api.setSales(empty);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(page.getByTestId("realized-gross-total")).toHaveText("0,00 EUR");
  await expect(visual(page).getByTestId("sell-contribution-mark")).toHaveCount(
    0,
  );
  await expect(visual(page)).not.toContainText("synthetic-sell-1");
  api.setUnavailable();
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(visual(page)).toHaveCount(0);
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  expect(api.reads).toHaveLength(5);
  expect(api.unexpected).toEqual([]);
  expect(api.browserErrors).toEqual([]);
});

test("UX4-C explains the backend four-trade reference and preserves unavailable statistics", async ({
  page,
  baseURL,
}, testInfo) => {
  const api = await installReports(page, baseURL);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(reportUrl("closed-trades"));
  const statistics = page.getByRole("region", {
    name: "Basisstatistiken des Abschlussberichts",
    exact: true,
  });
  await expect(
    page.getByTestId("closed-trades-statistics-population"),
  ).toContainText("Population N = 4");
  const metrics = [
    ["win-rate", "50,00 %"],
    ["average-gross-pnl", "62,50 EUR"],
    ["median-gross-pnl", "50,00 EUR"],
    ["gross-profit-factor", "6,00"],
  ];
  for (const [id, value] of metrics) {
    await expect(page.getByTestId(`closed-trades-${id}`)).toHaveText(value);
    const card = page.getByTestId(`closed-trades-${id}`).locator("..");
    await expect(card).toContainText("Grundgesamtheit:");
    await expect(card).toContainText("N = 4");
    await expect(card).toContainText("2026-10-01");
    await expect(card).toContainText("2026-10-31");
    await expect(card).toContainText("Europe/Berlin");
    await expect(card).toContainText("Kohortenwährung: EUR");
  }
  await expect(statistics).toContainText("2026-10-01");
  await expect(statistics).toContainText("2026-10-31");
  await expect(statistics).toContainText("Europe/Berlin");
  await expect(statistics).toContainText("EUR");
  await expect(statistics).toContainText(/Neutrale Trades/);
  const precise = statistics.getByText("Präzise Kennzahlen und Herkunft", {
    exact: true,
  });
  await precise.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  const tableRegion = statistics.getByRole("region", {
    name: "Kennzahlentabelle, bei Bedarf horizontal scrollbar",
    exact: true,
  });
  await expectVisibleFocus(tableRegion);
  await page.keyboard.press("ArrowRight");
  await expect
    .poll(() => tableRegion.evaluate((element) => element.scrollLeft))
    .toBeGreaterThan(0);
  const table = tableRegion.getByRole("table", {
    name: "Kennzahlen des Abschlussberichts · Anzeige und unveränderte Rohwerte",
    exact: true,
  });
  await expect(table.getByRole("row")).toHaveCount(5);
  await expect(statistics.getByText("62.5", { exact: true })).toBeVisible();
  await expect(statistics).toContainText("closed-trade-statistics-v1");
  await expectNoDocumentOverflow(page);
  await statistics.scrollIntoViewIfNeeded();
  await attachViewport(page, testInfo, "ux4-c-closed-statistics-390-synthetic");
  const partial = referenceClosedReport();
  partial.basis.id = "d".repeat(64);
  partial.summary = {
    ...partial.summary,
    status: "PARTIAL",
    total: null,
    total_display: null,
    subtotal: "250",
    subtotal_display: "250.00",
  };
  partial.statistics = {
    ...unavailableClosedTradeStatistics("PARTIAL"),
    report_basis_id: partial.basis.id,
  };
  partial.items.push(
    closedTradeItem("synthetic-unresolved-trade", {
      group: "MONETARY_UNRESOLVED",
      status: "NOT_COMPUTABLE",
      reasons: ["CURRENCY_UNKNOWN"],
      realized_gross_pnl: null,
      realized_gross_pnl_display: null,
      classification: null,
    }),
  );
  partial.counts = {
    ...partial.counts,
    examined: 5,
    in_period: 5,
    monetary_unresolved: 1,
    unresolved: 1,
  };
  api.setClosed(partial);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(
    page.getByTestId("closed-trades-statistics-population"),
  ).toContainText("nicht bestimmt");
  for (const [id] of metrics) {
    await expect(page.getByTestId(`closed-trades-${id}`)).toHaveText(
      "Berichtsgrundlage unvollständig",
    );
  }
  await expect(statistics).not.toContainText("62,50 EUR");
  await page.setViewportSize({ width: 320, height: 900 });
  await expectNoDocumentOverflow(page);
  const losses = closedTradeReport({
    filters,
    items: [
      closedTradeItem("synthetic-only-loss", {
        realized_gross_pnl: "-50",
        realized_gross_pnl_display: "-50.00",
        classification: "NEGATIVE",
      }),
    ],
    statistics: closedTradeStatistics({
      report_basis_id: "e".repeat(64),
      win_rate: { raw: "0", display: "0.00", reason: null },
      average_gross_pnl: { raw: "-50", display: "-50.00", reason: null },
      median_gross_pnl: { raw: "-50", display: "-50.00", reason: null },
      gross_profit_factor: { raw: "0", display: "0.00", reason: null },
    }),
  });
  losses.basis.id = "e".repeat(64);
  losses.summary = { ...losses.summary, total: "-50", total_display: "-50.00" };
  losses.counts = { ...losses.counts, positive: 0, negative: 1 };
  api.setClosed(losses);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(
    page.getByTestId("closed-trades-gross-profit-factor"),
  ).toHaveText("0,00");
  const noLoss = closedTradeReport({ filters });
  noLoss.basis.id = "f".repeat(64);
  noLoss.statistics.report_basis_id = noLoss.basis.id;
  api.setClosed(noLoss);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(
    page.getByTestId("closed-trades-gross-profit-factor"),
  ).toHaveText("Nicht definiert: keine Verlusttrades");
  await expectNoDocumentOverflow(page);
  expect(api.reads).toHaveLength(4);
  expect(api.unexpected).toEqual([]);
  expect(api.browserErrors).toEqual([]);
});

test("UX4-C native 200 and 400 percent zoom retains keyboard tables and original sources", async ({
  baseURL,
}, testInfo) => {
  test.setTimeout(90000);
  const extension = testInfo.outputPath("synthetic-ux4-c-zoom-extension");
  await mkdir(extension, { recursive: true });
  await writeFile(
    extension + "/manifest.json",
    JSON.stringify({
      manifest_version: 3,
      name: "Synthetic UX4-C native browser zoom test",
      version: "1.0",
      permissions: ["tabs"],
      background: { service_worker: "worker.js" },
    }),
  );
  await writeFile(
    extension + "/worker.js",
    "chrome.runtime.onInstalled.addListener(() => {});\n",
  );
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const context = await chromium.launchPersistentContext(
    testInfo.outputPath("synthetic-ux4-c-zoom-profile"),
    {
      ...(executablePath ? { executablePath } : {}),
      headless: false,
      viewport: { width: 1280, height: 900 },
      args: [
        "--headless=new",
        "--disable-extensions-except=" + extension,
        "--load-extension=" + extension,
      ],
    },
  );
  try {
    const worker =
      context.serviceWorkers()[0] ??
      (await context.waitForEvent("serviceworker"));
    const page = context.pages()[0] ?? (await context.newPage());
    await page.bringToFront();
    const api = await installReports(page, baseURL);
    await page.goto(new URL(reportUrl("realized-gross"), baseURL).href);
    await expect(
      visual(page).getByTestId("sell-contribution-mark"),
    ).toHaveCount(19);
    const before = await page.evaluate(() => ({
      width: innerWidth,
      ratio: devicePixelRatio,
    }));
    const measurements: unknown[] = [];
    for (const factor of [2, 4]) {
      const actual = await worker.evaluate(
        async ({ origin, factor }) => {
          const tabs = (
            globalThis as unknown as {
              chrome: {
                tabs: {
                  query: (query: {
                    url: string;
                  }) => Promise<Array<{ id: number }>>;
                  setZoom: (id: number, factor: number) => Promise<void>;
                  getZoom: (id: number) => Promise<number>;
                };
              };
            }
          ).chrome.tabs;
          const matches = await tabs.query({ url: origin + "/*" });
          if (matches.length !== 1)
            throw new Error("Expected one synthetic application tab");
          await tabs.setZoom(matches[0].id, factor);
          return tabs.getZoom(matches[0].id);
        },
        { origin: new URL(page.url()).origin, factor },
      );
      expect(actual).toBeCloseTo(factor, 12);
      await expect
        .poll(() => page.evaluate(() => innerWidth))
        .toBe(before.width / factor);
      await expect
        .poll(() => page.evaluate(() => devicePixelRatio))
        .toBeCloseTo(before.ratio * factor, 12);
      const panel = visual(page);
      const region = panel.getByRole("region", {
        name: "SELL-Datentabelle",
        exact: true,
      });
      await region.focus();
      await page.keyboard.press("ArrowRight");
      await expectVisibleFocus(region);
      await expect(row(page, 2)).toContainText("Nicht berechenbar");
      await expect(row(page, 3)).toContainText("Uhrzeit unbekannt");
      await expect(row(page, 3)).toContainText("Asia/Tokyo");
      const source = panel.getByRole("button", {
        name: "Originalquellen zu SELL 3",
        exact: true,
      });
      await source.focus();
      await expectVisibleFocus(source);
      await page.keyboard.press("Enter");
      const original = page.getByRole("article", {
        name: "Verkauf synthetic-sell-3",
        exact: true,
      });
      await expect(original).toBeFocused();
      await expect(original).toContainText("Uhrzeit unbekannt");
      await expect(original).toContainText("Asia/Tokyo");
      await expectNoDocumentOverflow(page);
      await original.evaluate((element) =>
        element.scrollIntoView({ block: "center" }),
      );
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
          ),
      );
      const session = await context.newCDPSession(page);
      const capture = await session.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: false,
        captureBeyondViewport: false,
      });
      await session.detach();
      const screenshot = testInfo.outputPath(
        `ux4-c-native-${factor * 100}-percent-synthetic.png`,
      );
      await writeFile(screenshot, Buffer.from(capture.data, "base64"));
      await testInfo.attach(`UX4-C native ${factor * 100}% original evidence`, {
        path: screenshot,
        contentType: "image/png",
      });
      measurements.push({
        requested: factor,
        actual,
        after: await page.evaluate(() => ({
          width: innerWidth,
          ratio: devicePixelRatio,
          documentWidth: document.documentElement.scrollWidth,
        })),
      });
    }
    const measurementsPath = testInfo.outputPath(
      "ux4-c-native-zoom-measurements.json",
    );
    await writeFile(
      measurementsPath,
      JSON.stringify({ before, measurements }, null, 2),
    );
    await testInfo.attach("UX4-C native zoom measurements", {
      path: measurementsPath,
      contentType: "application/json",
    });
    expect(api.reads).toHaveLength(1);
    expect(api.unexpected).toEqual([]);
    expect(api.browserErrors).toEqual([]);
  } finally {
    await context.close();
  }
});
