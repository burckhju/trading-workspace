import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

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
  expect(initial.schema_revision).toBe("20261017_0047");
  expect(initial.postgresql).toMatch(/^PostgreSQL 17\./);
  expect(initial.tables.trades.count).toBe(0);
  expect(initial.tables.execution_records.count).toBe(0);
  const api = `${baseURL}/api/api/v1`;
  const failures: string[] = [];
  const financialReads: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (sent) => {
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
    await page.getByLabel("Berichtswährung", { exact: true }).fill("EUR");
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
  const reportPath = (kind: string, from: string, to: string) =>
    `/performance/${kind}?` +
    new URLSearchParams({
      from_date: from,
      to_date: to,
      report_currency: "EUR",
      report_timezone: "Europe/Berlin",
    });
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
      .getByRole("link", { name: "Verkäufe im Zeitraum", exact: true })
      .first(),
  ).toBeVisible();
  await select("2026-10-01", "2026-10-31");
  const emptyInitial = await read();
  expect(emptyInitial.summary).toMatchObject({
    status: "EMPTY",
    total: "0",
    subtotal: null,
  });

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
  const readsBeforeSources = financialReads.length;
  await t1Row
    .getByRole("button", { name: "Quellen und Gesamtverlauf", exact: true })
    .click();
  await expect(provenance).toBeVisible();
  expect(financialReads).toHaveLength(readsBeforeSources);
  expect(databaseState().fingerprint).toBe(beforeReads.fingerprint);

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
    page.getByText(/Der Quellenstand hat sich seit dem letzten Lesen/),
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
  expect(financialReads).toHaveLength(readsBeforePaging);
  expect(databaseState().fingerprint).toBe(beforePaging.fingerprint);

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
      { initial, beforeReads, beforePaging, finalState },
      null,
      2,
    ),
    contentType: "application/json",
  });
});
