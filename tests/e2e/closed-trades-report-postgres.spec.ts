import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { assertSourceExitNavigation } from "./support/trade_source_journey";

test.use({ serviceWorkers: "block", trace: "on" });

// A separate runner invocation supplies a fresh marked database for this case.
// All financial rows are owner commands; no route mock or SQL execution fixture.
test("real PostgreSQL: full-close cohort, lifetime result, gaps and current correction", async ({
  page,
  request,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.REPORT_E2E_WRITES_ALLOWED !== "1",
    "Requires the separately created and marked disposable report PostgreSQL stack",
  );
  test.setTimeout(180_000);
  expect(baseURL).toBe("http://127.0.0.1:38080");
  const root = resolve(process.cwd(), "..");
  const databaseState = () =>
    JSON.parse(
      execFileSync(
        process.env.REPORT_E2E_PYTHON ?? "python",
        [resolve(root, "tests/e2e/support/realized_gross_database_guard.py")],
        {
          cwd: root,
          env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
          encoding: "utf8",
        },
      ),
    );
  const initial = databaseState();
  expect(initial.schema_revision).toBe("20261028_0048");
  expect(initial.postgresql).toMatch(/^PostgreSQL 17\./);
  expect(initial.tables.trades.count).toBe(0);
  expect(initial.tables.execution_records.count).toBe(0);
  const api = `${baseURL}/api/api/v1`;
  const failures: string[] = [];
  const financialReads: string[] = [];
  let integrationReadWindow = false;
  const integrationRequests: Array<{ method: string; url: string }> = [];
  const integrationWindows: Array<{
    before: unknown;
    after: unknown;
    entry: string;
  }> = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (sent) => {
    if (integrationReadWindow && sent.url().startsWith(api))
      integrationRequests.push({ method: sent.method(), url: sent.url() });
    if (sent.method() === "GET" && sent.url().startsWith(api + "/performance/"))
      financialReads.push(sent.url());
  });
  await page.route("**/*", (route) => {
    if (new URL(route.request().url()).origin === baseURL)
      return route.continue();
    failures.push(
      `Unexpected external browser request: ${route.request().url()}`,
    );
    return route.abort();
  });
  const address = (path: string) => {
    const url = new URL(api + path);
    expect(url.origin).toBe(baseURL);
    expect(url.pathname.startsWith("/api/api/v1/")).toBe(true);
    return url.href;
  };
  const post = async (path: string, data: object) => {
    databaseState(); // verify the isolated marked target before every synthetic write
    const response = await request.post(address(path), {
      data,
      maxRedirects: 0,
    });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  };
  const get = async (path: string) => {
    const response = await request.get(address(path), { maxRedirects: 0 });
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const declaration = (currency: string) => ({
    currency_code: currency,
    source: "USER_CONFIRMED",
    note: "Synthetic full-close report evidence in the isolated qualification",
  });
  const capture = (
    quantity: number,
    price: string,
    day: string,
    currency?: string,
  ) => ({
    quantity,
    price_per_unit: price,
    executed_on: day,
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
    ...(currency ? { currency_confirmation: declaration(currency) } : {}),
  });
  const suffix = crypto.randomUUID();
  const issuer = await post("/market-reference-data/issuers", {
    legal_name: `Closed report qualification ${suffix}`,
    display_name: "Synthetic cohort issuer",
  });
  const venues = await get("/market-reference-data/trading-venues");
  const venue = venues.items.find(
    (entry: { mic: string }) => entry.mic === "XETR",
  );
  const underlying = await post("/underlyings", {
    name: `Synthetic full-close source ${suffix}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venue.id,
      ticker: `C${suffix.slice(0, 7)}`,
      currency_code: "EUR",
    },
  });
  const createProduct = (name: string, strike: string) =>
    post("/warrants", {
      issuer_id: issuer.id,
      underlying_id: underlying.id,
      display_name: name,
      option_direction: "CALL",
      strike,
      strike_currency_code: "USD",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    });
  const product = await createProduct(
    "Gleiches Produkt · getrennte Trade-Identitäten",
    "500",
  );
  const buy = async (
    quantity: number,
    price: string,
    day: string,
    currency?: string,
    productId = product.id,
  ) =>
    post("/trade-position/purchases/external", {
      product_id: productId,
      ...capture(quantity, price, day, currency),
    });
  const simple = async (
    price: string,
    currency?: string,
    quantity = 10,
    day = "2026-10-04",
    productId = product.id,
  ) => {
    const bought = await buy(10, "5.00", "2026-06-01", currency, productId);
    const sold = await post(
      `/trade-position/trades/${bought.trade.id}/sales`,
      capture(quantity, price, day),
    );
    return { bought, sold, id: bought.trade.id };
  };
  const select = async (from: string, to: string) => {
    await page.getByLabel("Von (einschließlich)").fill(from);
    await page.getByLabel("Bis (einschließlich)").fill(to);
    const currency = page.getByLabel("Berichtswährung", { exact: true });
    await expect(currency).toHaveValue("EUR");
    await expect(currency).not.toBeEditable();
    await page.getByLabel("Berichtszeitzone (IANA)").fill("Europe/Berlin");
  };
  const read = async () => {
    const pending = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().startsWith(api + "/performance/closed-trades?"),
    );
    await page
      .getByRole("button", { name: "Bericht lesen", exact: true })
      .click();
    const response = await pending;
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const switchReport = async (kind: "realized-gross" | "closed-trades") => {
    const before = financialReads.length;
    const pending = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().startsWith(api + `/performance/${kind}?`),
    );
    const button = page.getByRole("button", {
      name:
        kind === "closed-trades"
          ? "Trades mit Vollabschluss im Zeitraum"
          : "Verkäufe im Zeitraum",
      exact: true,
    });
    await button.focus();
    await expect(button).toBeFocused();
    await button.press("Enter");
    const response = await pending;
    expect(response.status(), await response.text()).toBe(200);
    const body = await response.json();
    await expect(
      page.getByTestId(
        kind === "closed-trades"
          ? "closed-trades-total"
          : "realized-gross-total",
      ),
    ).toBeVisible();
    expect(financialReads.slice(before)).toEqual([response.url()]);
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("form")).toHaveCount(1);
    await expect(
      page.getByRole("region", {
        name: "Ergebnis und Datenabdeckung",
        exact: true,
      }),
    ).toHaveCount(1);
    const query = new URL(page.url()).searchParams;
    expect(query.get("report_context")).toBe(kind);
    expect(query.get("report_view")).toBe("candidates");
    expect(query.get("report_page")).toBe("1");
    expect(query.has("report_basis")).toBe(false);
    return body;
  };
  const reportPath = (kind: string, from: string, to: string) =>
    `/performance/${kind}?` +
    new URLSearchParams({
      from_date: from,
      to_date: to,
      report_currency: "EUR",
      report_timezone: "Europe/Berlin",
    });
  const noLosses = {
    raw: null,
    display: null,
    reason: "Nicht definiert: keine Verlusttrades",
  };
  const unavailableStatistics = (population: number | null, reason: string) => {
    const unavailable = { raw: null, display: null, reason };
    return {
      population,
      win_rate: unavailable,
      average_gross_pnl: unavailable,
      median_gross_pnl: unavailable,
      gross_profit_factor: unavailable,
    };
  };
  const incompleteStatistics = unavailableStatistics(
    null,
    "Berichtsgrundlage unvollständig",
  );
  const emptyStatistics = unavailableStatistics(
    0,
    "Keine abgeschlossenen Trades in der Auswahl",
  );
  const expectStatisticsDisplay = async (
    winRate: string,
    average: string,
    median: string,
    profitFactor: string,
  ) => {
    const statistics = page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    });
    await expect(statistics.getByTestId("closed-trades-win-rate")).toHaveText(
      winRate,
    );
    await expect(
      statistics.getByTestId("closed-trades-average-gross-pnl"),
    ).toHaveText(average);
    await expect(
      statistics.getByTestId("closed-trades-median-gross-pnl"),
    ).toHaveText(median);
    await expect(
      statistics.getByTestId("closed-trades-gross-profit-factor"),
    ).toHaveText(profitFactor);
  };
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto("/performance/closed-trades");
  await expect(
    page.getByRole("heading", {
      name: "Trades mit Vollabschluss im Zeitraum",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Hauptnavigation", exact: true })
      .getByRole("link", { name: "Performance", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: "Verkäufe im Zeitraum",
      exact: true,
    }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(
    page.getByRole("form", {
      name: "Performance-Zeitraum auswählen",
      exact: true,
    }),
  ).toHaveCount(1);
  expect(financialReads).toHaveLength(0);
  await select("2026-10-01", "2026-10-31");
  const emptyInitial = await read();
  expect(emptyInitial.summary).toMatchObject({
    status: "EMPTY",
    total: "0",
    subtotal: null,
  });
  expect(emptyInitial.statistics).toMatchObject(emptyStatistics);
  await expectStatisticsDisplay(
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
  );

  const t1 = await buy(100, "2.00", "2026-08-05", "EUR");
  const tradePath = `/trade-position/trades/${t1.trade.id}`;
  const august = await post(
    tradePath + "/sales",
    capture(20, "2.50", "2026-08-12"),
  );
  const septemberFirst = await post(
    tradePath + "/sales",
    capture(30, "3.00", "2026-09-02"),
  );
  const added = await post(
    tradePath + "/purchases",
    capture(50, "4.00", "2026-09-06"),
  );
  const septemberLast = await post(
    tradePath + "/sales",
    capture(40, "2.50", "2026-09-12"),
  );
  expect(septemberLast.position.open_quantity).toBe(60);
  await select("2026-09-01", "2026-09-30");
  const stillOpen = await read();
  expect(stillOpen.summary.status).toBe("EMPTY");
  expect(stillOpen.counts.open).toBe(1);
  expect(stillOpen.statistics).toMatchObject(emptyStatistics);
  expect(
    (await get(reportPath("realized-gross", "2026-09-01", "2026-09-30")))
      .summary.total_display,
  ).toBe("10.00");
  const october = await post(
    tradePath + "/sales",
    capture(60, "3.50", "2026-10-03"),
  );
  expect(october.position.is_closed).toBe(true);
  const september = await read();
  expect(september.summary.status).toBe("EMPTY");
  expect(september.counts.outside_period).toBe(1);
  expect(september.statistics).toMatchObject(emptyStatistics);
  await select("2026-10-01", "2026-10-31");
  const original = await read();
  expect(original.definition_version).toBe("closed-trade-gross-v1");
  expect(original.summary).toMatchObject({
    status: "COMPLETE",
    total_display: "50.00",
    subtotal: null,
  });
  expect(original.counts).toMatchObject({
    examined: 1,
    qualified: 1,
    positive: 1,
    negative: 0,
    neutral: 0,
    unresolved: 0,
  });
  // Independently declared native goldens: lifetime T1 = 10 + 30 - 20 + 30 = 50.
  expect(original.statistics).toMatchObject({
    population: 1,
    win_rate: { raw: "100", display: "100.00", reason: null },
    average_gross_pnl: {
      raw: expect.stringMatching(/^50(?:\.0+)?$/),
      display: "50.00",
      reason: null,
    },
    median_gross_pnl: {
      raw: expect.stringMatching(/^50(?:\.0+)?$/),
      display: "50.00",
      reason: null,
    },
    gross_profit_factor: noLosses,
  });
  await expectStatisticsDisplay(
    "100,00 %",
    "50,00 EUR",
    "50,00 EUR",
    noLosses.reason,
  );
  expect(original.items[0]).toMatchObject({
    trade_id: t1.trade.id,
    closing_execution_id: october.execution.id,
    closing_time: {
      time_precision: "DATE_ONLY",
      executed_at: null,
      executed_on: "2026-10-03",
    },
    classification: "POSITIVE",
  });
  expect(
    original.items[0].sell_contributions.map(
      (entry: { realized_gross_pnl_delta_display: string }) =>
        entry.realized_gross_pnl_delta_display,
    ),
  ).toEqual(["10.00", "30.00", "-20.00", "30.00"]);
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");

  // The same native October context has two different, independently read
  // financial meanings: SELL contribution 30, complete trade result 50.
  const beforeSwitches = databaseState();
  const originalContextUrl = page.url();
  integrationReadWindow = true;
  const readsBeforeView = financialReads.length;
  await page.getByLabel("Zeilen anzeigen").selectOption("qualified");
  await expect(page).toHaveURL(/report_view=qualified/);
  expect(financialReads).toHaveLength(readsBeforeView);
  const octoberSales = await switchReport("realized-gross");
  expect(octoberSales.definition_version).toBe("realized-gross-sell-v2");
  expect(octoberSales.filters).toEqual(original.filters);
  expect(octoberSales.summary.total_display).toBe("30.00");
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "30,00 EUR",
  );
  await expect(page.getByTestId("closed-trades-total")).toHaveCount(0);
  await expect(
    page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    }),
  ).toHaveCount(0);
  const octoberClosedAgain = await switchReport("closed-trades");
  expect(octoberClosedAgain.filters).toEqual(original.filters);
  expect(octoberClosedAgain.summary).toEqual(original.summary);
  expect(octoberClosedAgain.statistics).toEqual(original.statistics);
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  await expectStatisticsDisplay(
    "100,00 %",
    "50,00 EUR",
    "50,00 EUR",
    noLosses.reason,
  );
  const afterSwitches = databaseState();
  expect(afterSwitches.fingerprint).toBe(beforeSwitches.fingerprint);
  integrationReadWindow = false;
  integrationWindows.push({
    before: beforeSwitches,
    after: afterSwitches,
    entry: originalContextUrl,
  });
  await testInfo.attach("performance-workspace-independent-october-reports", {
    body: JSON.stringify({ octoberSales, octoberClosedAgain }, null, 2),
    contentType: "application/json",
  });

  const t1Row = page.getByRole("article", {
    name: `Trade ${t1.trade.id}`,
    exact: true,
  });
  const sourceButton = t1Row.getByRole("button", {
    name: "Quellen und Gesamtverlauf",
    exact: true,
  });
  await sourceButton.focus();
  await expect(sourceButton).toBeFocused();
  await sourceButton.press("Enter");
  await expect(
    t1Row.getByRole("button", { name: "Quellen schließen", exact: true }),
  ).toHaveAttribute("aria-expanded", "true");
  const provenance = page.getByRole("region", {
    name: `Herkunft Trade ${t1.trade.id}`,
    exact: true,
  });
  for (const executionId of [
    t1.execution.id,
    august.execution.id,
    septemberFirst.execution.id,
    added.execution.id,
    septemberLast.execution.id,
    october.execution.id,
  ]) {
    await expect(
      provenance
        .getByRole("listitem", {
          name: `Buchungsquelle ${executionId}`,
          exact: true,
        })
        .first(),
    ).toBeVisible();
  }
  await expect(provenance).toContainText(t1.execution.currency_confirmation.id);
  await page.screenshot({
    path: testInfo.outputPath("closed-complete-desktop.png"),
    fullPage: true,
  });

  const resultRegion = () =>
    page.getByRole("region", {
      name: "Wirtschaftliches Gesamtergebnis",
      exact: true,
    });
  const returnLink = () =>
    page.getByRole("link", {
      name: "Zur ursprünglichen Abschlussauswahl",
      exact: true,
    });
  const firstEntry = (await page
    .getByRole("link", { name: `Trade ${t1.trade.id} prüfen`, exact: true })
    .getAttribute("href"))!;
  const beforeEntry = databaseState();
  integrationReadWindow = true;
  await page
    .getByRole("link", { name: `Trade ${t1.trade.id} prüfen`, exact: true })
    .press("Enter");
  await expect(
    resultRegion().getByText("50,00 EUR", { exact: true }),
  ).toBeVisible();
  await expect(resultRegion()).toContainText("Berichtsgrundlage stimmt");
  await expect(
    page.getByRole("region", { name: "Journal", exact: true }),
  ).toContainText("Journal nicht dokumentiert");
  await expect(
    page.getByRole("region", {
      name: "Dokumentierte Exit-Bewertung",
      exact: true,
    }),
  ).toContainText("Exit-Bewertung nicht dokumentiert");
  await expect(page.getByRole("form")).toHaveCount(0);
  await assertSourceExitNavigation(page);
  await page.screenshot({
    path: testInfo.outputPath("closed-source-reference-50-desktop.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(
    resultRegion().getByText("50,00 EUR", { exact: true }),
  ).toBeVisible();
  await returnLink().click();
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  await expect(page.getByLabel("Von (einschließlich)")).toHaveValue(
    "2026-10-01",
  );
  await expect(page.getByLabel("Bis (einschließlich)")).toHaveValue(
    "2026-10-31",
  );
  const afterEntry = databaseState();
  expect(afterEntry.fingerprint).toBe(beforeEntry.fingerprint);
  integrationReadWindow = false;
  integrationWindows.push({
    before: beforeEntry,
    after: afterEntry,
    entry: firstEntry,
  });

  const t2 = await simple("4.00", "EUR");
  const t3 = await simple("5.00", "EUR");
  const complete = await read();
  expect(complete.summary).toMatchObject({
    status: "COMPLETE",
    total_display: "40.00",
  });
  expect(complete.counts).toMatchObject({
    examined: 3,
    qualified: 3,
    positive: 1,
    negative: 1,
    neutral: 1,
  });
  // T1/T2/T3 = [50, -10, 0]: one win among all three, total 40, median zero.
  expect(complete.statistics).toMatchObject({
    population: 3,
    win_rate: {
      raw: "33.33333333333333333333333333",
      display: "33.33",
      reason: null,
    },
    average_gross_pnl: {
      raw: "13.33333333333333333333333333",
      display: "13.33",
      reason: null,
    },
    median_gross_pnl: {
      raw: expect.stringMatching(/^0(?:\.0+)?$/),
      display: "0.00",
      reason: null,
    },
    gross_profit_factor: { raw: "5", display: "5.00", reason: null },
  });
  await expectStatisticsDisplay("33,33 %", "13,33 EUR", "0,00 EUR", "5,00");
  await expect(
    page.getByTestId("closed-trades-statistics-population"),
  ).toContainText("Population N = 3");
  await page.screenshot({
    path: testInfo.outputPath("closed-statistics-complete-desktop.png"),
    fullPage: true,
  });
  expect(
    new Set(
      complete.items.map((entry: { trade_id: string }) => entry.trade_id),
    ),
  ).toEqual(new Set([t1.trade.id, t2.id, t3.id]));
  expect(
    new Set(
      complete.items.map((entry: { product_id: string }) => entry.product_id),
    ),
  ).toEqual(new Set([product.id]));
  const t4 = await simple("6.00");
  const t5 = await simple("6.00", "USD");
  const t6 = await simple("7.00", "EUR", 5);
  const partial = await read();
  expect(partial.summary).toMatchObject({
    status: "PARTIAL",
    total: null,
    subtotal_display: "40.00",
  });
  expect(partial.counts).toMatchObject({
    examined: 6,
    open: 1,
    other_currency: 1,
    monetary_unresolved: 1,
    qualified: 3,
    positive: 1,
    negative: 1,
    neutral: 1,
  });
  expect(partial.statistics).toMatchObject(incompleteStatistics);
  await expectStatisticsDisplay(
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
  );
  const byTrade = new Map(
    partial.items.map(
      (entry: {
        trade_id: string;
        group: string;
        classification: string | null;
        realized_gross_pnl: string | null;
      }) => [entry.trade_id, entry],
    ),
  );
  expect(byTrade.get(t4.id)).toMatchObject({
    group: "MONETARY_UNRESOLVED",
    classification: null,
    realized_gross_pnl: null,
  });
  expect(byTrade.get(t5.id)).toMatchObject({ group: "OTHER_CURRENCY" });
  expect(byTrade.get(t6.id)).toMatchObject({ group: "OPEN" });
  await expect(page.getByTestId("closed-trades-subtotal")).toHaveText(
    "40,00 EUR",
  );
  await expect(
    page.getByRole("article", { name: `Trade ${t4.id}`, exact: true }),
  ).toBeVisible();
  const beforeReads = databaseState();
  expect(beforeReads.tables.execution_currency_confirmations.count).toBe(5);
  const repeat = await read();
  expect(repeat.basis.id).toBe(partial.basis.id);
  expect(repeat.statistics).toEqual(partial.statistics);
  const readsBeforeSources = financialReads.length;
  await t1Row
    .getByRole("button", { name: "Quellen und Gesamtverlauf", exact: true })
    .click();
  await expect(provenance).toBeVisible();
  expect(financialReads).toHaveLength(readsBeforeSources);
  expect(databaseState().fingerprint).toBe(beforeReads.fingerprint);

  const staleEntry = (await page
    .getByRole("link", { name: `Trade ${t1.trade.id} prüfen`, exact: true })
    .getAttribute("href"))!;
  const corrected = await post(
    tradePath + `/executions/${septemberLast.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 40,
      price_per_unit: "3.00",
      executed_on: "2026-09-12",
      execution_timezone: "Europe/Berlin",
    },
  );
  expect(corrected.position.realized_gross_pnl).toBe("70.0000000000");
  const changed = await read();
  expect(changed.summary).toMatchObject({
    status: "PARTIAL",
    total: null,
    subtotal_display: "60.00",
  });
  expect(changed.counts).toEqual(partial.counts);
  expect(changed.basis.id).not.toBe(partial.basis.id);
  // Corrected T1 = 70; the unresolved T4 still prevents all cohort statistics.
  expect(changed.statistics).toMatchObject(incompleteStatistics);
  expect(
    changed.sources.find(
      (entry: { execution_id: string }) =>
        entry.execution_id === septemberLast.execution.id,
    ),
  ).toMatchObject({
    is_effective: false,
    superseded_by_execution_id: corrected.execution.id,
  });
  expect(
    changed.items.find(
      (entry: { trade_id: string }) => entry.trade_id === t1.trade.id,
    ),
  ).toMatchObject({
    realized_gross_pnl_display: "70.00",
    closing_execution_id: october.execution.id,
  });
  await expect(page.getByTestId("closed-trades-subtotal")).toHaveText(
    "60,00 EUR",
  );
  await expect(
    page.getByText(
      "Der Quellenstand hat sich gegenüber dem mitgegebenen oder zuletzt gelesenen Stand dieser Auswahl geändert. " +
        "Ergebnis, Zähler, Zeilen, Herkunft und gegebenenfalls Abschlusskennzahlen wurden gemeinsam durch den neu gelesenen Stand ersetzt.",
      { exact: true },
    ),
  ).toBeVisible();
  expect(
    (await get(reportPath("realized-gross", "2026-09-01", "2026-09-30")))
      .summary.total_display,
  ).toBe("30.00");
  await t1Row
    .getByRole("button", { name: "Quellen und Gesamtverlauf", exact: true })
    .click();
  await provenance
    .getByText(/Gesamte gelesene Historie einschließlich ersetzter Buchungen/)
    .click();
  await expect(
    provenance
      .getByRole("list", { name: "Gesamte Trade-Historie", exact: true })
      .getByRole("listitem", {
        name: `Buchungsquelle ${septemberLast.execution.id}`,
        exact: true,
      }),
  ).toBeVisible();
  await expect(provenance).toContainText(septemberLast.execution.id);
  await expect(provenance).toContainText(corrected.execution.id);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: testInfo.outputPath("closed-partial-corrected-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);

  const beforeChangedEntry = databaseState();
  integrationReadWindow = true;
  await page.goto(staleEntry);
  await expect(
    resultRegion().getByText("70,00 EUR", { exact: true }),
  ).toBeVisible();
  await expect(resultRegion()).toContainText("Berichtsgrundlage hat sich");
  await expect(resultRegion()).toContainText("auch andere Trades");
  await expect(
    page.getByRole("article", {
      name: `Quelle ${septemberLast.execution.id}`,
      exact: true,
    }),
  ).toContainText("Historisch ersetzt");
  await assertSourceExitNavigation(page);
  await page.screenshot({
    path: testInfo.outputPath("closed-source-reference-70-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await returnLink().click();
  await expect(page.getByTestId("closed-trades-subtotal")).toHaveText(
    "60,00 EUR",
  );
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("candidates");
  await expect(
    page.getByText(
      "Der Quellenstand hat sich gegenüber dem mitgegebenen oder zuletzt gelesenen Stand dieser Auswahl geändert. " +
        "Ergebnis, Zähler, Zeilen, Herkunft und gegebenenfalls Abschlusskennzahlen wurden gemeinsam durch den neu gelesenen Stand ersetzt.",
      { exact: true },
    ),
  ).toBeVisible();
  const afterChangedEntry = databaseState();
  expect(afterChangedEntry.fingerprint).toBe(beforeChangedEntry.fingerprint);
  integrationReadWindow = false;
  integrationWindows.push({
    before: beforeChangedEntry,
    after: afterChangedEntry,
    entry: staleEntry,
  });

  // Local pagination across stable IDs neither rereads nor writes the source.
  for (let index = 0; index < 21; index += 1) {
    // The capture owner permits one open trade per product. These independent
    // open rows therefore use independently created synthetic products.
    const pageProduct = await createProduct(
      `Synthetische Seitenquelle ${index + 1}`,
      String(501 + index),
    );
    await buy(1, "1.00", "2026-06-01", "EUR", pageProduct.id);
  }
  const paged = await read();
  expect(paged.counts).toMatchObject({
    examined: 27,
    open: 22,
    qualified: 3,
    unresolved: 1,
  });
  expect(paged.summary.subtotal_display).toBe("60.00");
  expect(paged.statistics).toMatchObject(incompleteStatistics);
  const beforePaging = databaseState();
  const readsBeforePaging = financialReads.length;
  await page.getByLabel("Zeilen anzeigen").selectOption("all");
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(20);
  const nextPage = page.getByRole("button", {
    name: "Nächste Seite",
    exact: true,
  });
  await nextPage.focus();
  await expect(nextPage).toBeFocused();
  await nextPage.press("Enter");
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(7);
  await expect(
    page.getByRole("navigation", { name: "Berichtsseiten", exact: true }),
  ).toContainText("Seite 2 von 2");
  await expect(page.getByTestId("closed-trades-subtotal")).toHaveText(
    "60,00 EUR",
  );
  await page
    .getByRole("button", { name: "Vorherige Seite", exact: true })
    .click();
  await page.getByLabel("Zeilen anzeigen").selectOption("unresolved");
  await expect(
    page.getByRole("article", { name: `Trade ${t4.id}`, exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(1);
  await expectStatisticsDisplay(
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
  );
  expect(financialReads).toHaveLength(readsBeforePaging);
  expect(databaseState().fingerprint).toBe(beforePaging.fingerprint);

  // The actual drill-down may reread; returning restores the supported local view/page.
  const beforeReturn = databaseState();
  integrationReadWindow = true;
  await page.getByLabel("Zeilen anzeigen").selectOption("all");
  await nextPage.click();
  // Observe the local router render before reading the source link, as above.
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(7);
  await expect(
    page.getByRole("navigation", { name: "Berichtsseiten", exact: true }),
  ).toContainText("Seite 2 von 2");
  const pageTwoLink = page
    .getByRole("link", { name: /^Trade .* prüfen$/ })
    .first();
  const pageTwoEntry = (await pageTwoLink.getAttribute("href"))!;
  expect(new URL(pageTwoEntry, baseURL).searchParams.get("report_page")).toBe(
    "2",
  );
  await pageTwoLink.focus();
  await page.keyboard.press("Enter");
  await expect(resultRegion()).toContainText(
    "Vollständiges Tradeergebnis und Buchungshistorie",
  );
  await returnLink().click();
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("all");
  await expect(
    page.getByRole("navigation", { name: "Berichtsseiten", exact: true }),
  ).toContainText("Seite 2 von 2");
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(7);
  await page.reload();
  await expect(
    page.getByRole("navigation", { name: "Berichtsseiten", exact: true }),
  ).toContainText("Seite 2 von 2");
  await expect(page.getByLabel("Berichtswährung", { exact: true })).toHaveValue(
    "EUR",
  );
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Europe/Berlin",
  );
  const fullPageTwoUrl = page.url();
  expect(new URL(fullPageTwoUrl).searchParams.get("report_basis")).toBe(
    paged.basis.id,
  );
  await switchReport("realized-gross");
  const readsBeforeHistory = financialReads.length;
  await page.goBack();
  await expect(page).toHaveURL(fullPageTwoUrl);
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("all");
  await expect(
    page.getByRole("navigation", {
      name: "Berichtsseiten",
      exact: true,
    }),
  ).toContainText("Seite 2 von 2");
  await expect(page.getByTestId("closed-trades-subtotal")).toHaveText(
    "60,00 EUR",
  );
  expect(financialReads.slice(readsBeforeHistory)).toHaveLength(1);
  expect(financialReads.at(-1)).toContain("/performance/closed-trades?");
  await expect(page.getByRole("form")).toHaveCount(1);
  await expect(
    page.getByRole("region", {
      name: "Ergebnis und Datenabdeckung",
      exact: true,
    }),
  ).toHaveCount(1);
  const afterReturn = databaseState();
  expect(afterReturn.fingerprint).toBe(beforeReturn.fingerprint);
  integrationReadWindow = false;
  integrationWindows.push({
    before: beforeReturn,
    after: afterReturn,
    entry: pageTwoEntry,
  });
  expect(integrationRequests.length).toBeGreaterThan(20);
  expect(integrationRequests.every((r) => r.method === "GET")).toBe(true);
  await testInfo.attach("closed-source-integration-read-windows", {
    body: JSON.stringify({ integrationWindows, integrationRequests }, null, 2),
    contentType: "application/json",
  });

  // The full 27-row snapshot is COMPLETE on 3 October: only corrected T1 closes
  // that day. All 4 October closures (including unknown-currency T4) are safely
  // outside the period. Local pages and exclusions must keep N=1 and all values.
  const beforeCompletePaging = databaseState();
  await select("2026-10-03", "2026-10-03");
  const completeAfterCorrection = await read();
  expect(completeAfterCorrection.summary).toMatchObject({
    status: "COMPLETE",
    total_display: "70.00",
    subtotal: null,
  });
  expect(completeAfterCorrection.counts).toMatchObject({
    examined: 27,
    open: 22,
    outside_period: 4,
    qualified: 1,
    unresolved: 0,
  });
  expect(completeAfterCorrection.statistics).toMatchObject({
    population: 1,
    win_rate: { raw: "100", display: "100.00", reason: null },
    average_gross_pnl: {
      raw: expect.stringMatching(/^70(?:\.0+)?$/),
      display: "70.00",
      reason: null,
    },
    median_gross_pnl: {
      raw: expect.stringMatching(/^70(?:\.0+)?$/),
      display: "70.00",
      reason: null,
    },
    gross_profit_factor: noLosses,
  });
  const completeRepeat = await read();
  expect(completeRepeat.basis.id).toBe(completeAfterCorrection.basis.id);
  expect(completeRepeat.statistics).toEqual(completeAfterCorrection.statistics);
  const readsBeforeCompletePaging = financialReads.length;
  await page.getByLabel("Zeilen anzeigen").selectOption("all");
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(20);
  await nextPage.click();
  await expect(page.getByRole("article", { name: /^Trade / })).toHaveCount(7);
  await expectStatisticsDisplay(
    "100,00 %",
    "70,00 EUR",
    "70,00 EUR",
    noLosses.reason,
  );
  for (const view of ["qualified", "excluded", "unresolved"]) {
    await page.getByLabel("Zeilen anzeigen").selectOption(view);
    await expectStatisticsDisplay(
      "100,00 %",
      "70,00 EUR",
      "70,00 EUR",
      noLosses.reason,
    );
    await expect(
      page.getByTestId("closed-trades-statistics-population"),
    ).toContainText("Population N = 1");
  }
  expect(financialReads).toHaveLength(readsBeforeCompletePaging);
  const afterCompletePaging = databaseState();
  expect(afterCompletePaging.fingerprint).toBe(
    beforeCompletePaging.fingerprint,
  );
  await page.screenshot({
    path: testInfo.outputPath("closed-statistics-corrected-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);

  // Separate periods distinguish genuine exact zero, unknown, and empty.
  const stateProduct = await createProduct(
    "Synthetische Null- und Lückenauswahl",
    "550",
  );
  await simple("5.00", "EUR", 10, "2026-06-02", stateProduct.id);
  await simple("6.00", undefined, 10, "2026-07-02", stateProduct.id);
  await select("2026-06-01", "2026-06-30");
  const zero = await read();
  expect(zero.summary).toMatchObject({
    status: "COMPLETE",
    total_display: "0.00",
    subtotal: null,
  });
  expect(zero.counts).toMatchObject({
    qualified: 1,
    neutral: 1,
    unresolved: 0,
  });
  expect(zero.statistics).toMatchObject({
    population: 1,
    win_rate: { raw: "0", display: "0.00", reason: null },
    average_gross_pnl: {
      raw: expect.stringMatching(/^0(?:\.0+)?$/),
      display: "0.00",
      reason: null,
    },
    median_gross_pnl: {
      raw: expect.stringMatching(/^0(?:\.0+)?$/),
      display: "0.00",
      reason: null,
    },
    gross_profit_factor: noLosses,
  });
  await expectStatisticsDisplay(
    "0,00 %",
    "0,00 EUR",
    "0,00 EUR",
    noLosses.reason,
  );
  await expect(page.getByTestId("closed-trades-total")).toHaveText("0,00 EUR");
  await select("2026-07-01", "2026-07-31");
  const unknown = await read();
  expect(unknown.summary).toMatchObject({
    status: "NOT_COMPUTABLE",
    total: null,
    subtotal: null,
  });
  expect(unknown.counts).toMatchObject({
    qualified: 0,
    monetary_unresolved: 1,
  });
  expect(unknown.statistics).toMatchObject(incompleteStatistics);
  await expectStatisticsDisplay(
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
    "Berichtsgrundlage unvollständig",
  );
  await expect(page.getByTestId("closed-trades-total")).toHaveText(
    "Nicht berechenbar",
  );
  await select("2026-05-01", "2026-05-31");
  const empty = await read();
  expect(empty.summary).toMatchObject({
    status: "EMPTY",
    total: "0",
    subtotal: null,
  });
  expect(empty.statistics).toMatchObject(emptyStatistics);
  await expectStatisticsDisplay(
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
    "Keine abgeschlossenen Trades in der Auswahl",
  );
  for (const report of [
    emptyInitial,
    stillOpen,
    september,
    original,
    complete,
    partial,
    repeat,
    changed,
    paged,
    completeAfterCorrection,
    completeRepeat,
    zero,
    unknown,
    empty,
  ]) {
    expect(report.statistics).toMatchObject({
      definition_version: "closed-trade-statistics-v1",
      report_basis_id: report.basis.id,
      report_status: report.summary.status,
    });
  }
  expect(failures).toEqual([]);
  const finalState = databaseState();
  await read();
  expect(databaseState().fingerprint).toBe(finalState.fingerprint);
  await testInfo.attach("actual-closed-trade-owner-api-reports", {
    body: JSON.stringify(
      {
        emptyInitial,
        stillOpen,
        september,
        original,
        complete,
        partial,
        changed,
        paged,
        completeAfterCorrection,
        completeRepeat,
        zero,
        unknown,
        empty,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
  await testInfo.attach("postgres-closed-report-read-only-proof", {
    body: JSON.stringify(
      {
        initial,
        beforeReads,
        beforePaging,
        beforeCompletePaging,
        afterCompletePaging,
        finalState,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
});
