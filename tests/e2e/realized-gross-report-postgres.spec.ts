import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { qualifyTradeSources } from "./support/trade_source_journey";

// Explicit qualification only: the marked disposable PostgreSQL database is
// independently verified before the first owner write. No HTTP result fixtures.
test("real PostgreSQL: purchase currency once, inherited sales, sources and correction", async ({
  page,
  request,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.REPORT_E2E_WRITES_ALLOWED !== "1",
    "Requires the separately created and marked disposable report PostgreSQL stack",
  );
  test.setTimeout(120_000);
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
  expect(initial.tables.execution_records.count).toBe(0);
  const api = `${baseURL}/api/api/v1`;
  const failures: string[] = [];
  const financialReads: string[] = [];
  let reportReadWindow = false;
  const reportRequests: Array<{ method: string; url: string }> = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (sent) => {
    if (reportReadWindow && sent.url().startsWith(api))
      reportRequests.push({ method: sent.method(), url: sent.url() });
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
  const post = async (path: string, data?: object) => {
    databaseState();
    const response = await request.post(api + path, { data });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  };
  const confirmed = {
    currency_code: "EUR",
    source: "USER_CONFIRMED",
    note: "Synthetic EUR execution evidence for this isolated test",
  };
  const suffix = crypto.randomUUID();
  const issuer = await post("/market-reference-data/issuers", {
    legal_name: `Report qualification ${suffix}`,
    display_name: "Synthetic report issuer",
  });
  const venues = await (
    await request.get(api + "/market-reference-data/trading-venues")
  ).json();
  const venue = venues.items.find(
    (item: { mic: string }) => item.mic === "XETR",
  );
  const underlying = await post("/underlyings", {
    name: `Synthetic period source ${suffix}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venue.id,
      ticker: `R${suffix.slice(0, 7)}`,
      currency_code: "EUR",
    },
  });
  const product = await post("/warrants", {
    issuer_id: issuer.id,
    underlying_id: underlying.id,
    display_name: "Synthetischer Referenztrade · Bruttoergebnis",
    option_direction: "CALL",
    strike: "500",
    strike_currency_code: "USD",
    maturity_date: "2099-12-31",
    ratio: "0.1",
  });
  const capture = (
    quantity: number,
    price: string,
    day: string,
    currency = true,
  ) => ({
    quantity,
    price_per_unit: price,
    executed_on: day,
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
    ...(currency ? { currency_confirmation: confirmed } : {}),
  });
  // Prepare a real workspace selection through its owners. Its USD listing and
  // strike do not supply the explicitly entered EUR execution currency.
  await post(`/warrants/${product.id}/listings`, {
    trading_venue_id: venue.id,
    quotation_currency_code: "USD",
  });
  const plan = await post("/trade-plans", {
    origin_type: "MANUAL",
    underlying_id: underlying.id,
    thesis: "Synthetic currency reuse qualification",
    entry: { type: "PRICE", currency: "EUR", price: "100" },
    invalidation: { stop_price: "95" },
    targets: [{ sequence: 1, price: "110" }],
    risk_assumptions: {
      thesis_risk: "Synthetic test, not a trading recommendation",
    },
  });
  const versionPath = `/trade-plans/${plan.plan.id}/versions/${plan.latest_version.id}`;
  await post(versionPath + "/submit-review");
  await post(versionPath + "/approve");
  const selection = await post("/product-selection-runs", {
    trade_plan_id: plan.plan.id,
    trade_plan_version_id: plan.latest_version.id,
  });
  expect(selection.evaluations).toHaveLength(1);
  await post(`/product-selection-runs/${selection.run.id}/selection`, {
    product_evaluation_id: selection.evaluations[0].id,
    rationale:
      "Synthetic actual execution; missing market quotes remain missing.",
  });
  await page.goto(`/product-selection?run_id=${selection.run.id}`);
  await page.getByLabel("Kaufmenge", { exact: true }).fill("100");
  await page.getByLabel("Kaufpreis", { exact: true }).fill("2.00");
  await page.getByLabel("Kaufdatum", { exact: true }).fill("2026-08-05");
  await page
    .getByLabel("Ausführungswährung (Code)", { exact: true })
    .fill("EUR");
  await expect(
    page.getByRole("checkbox", {
      name: /Ich bestätige EUR als tatsächliche Währung/,
    }),
  ).toHaveCount(0);
  const purchaseWrite = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/purchases/from-selection"),
  );
  databaseState();
  await page
    .getByRole("button", {
      name: "BUY erfassen und Position eröffnen",
      exact: true,
    })
    .click();
  const purchaseResponse = await purchaseWrite;
  expect(purchaseResponse.status(), await purchaseResponse.text()).toBe(201);
  const buy = await purchaseResponse.json();
  expect(buy.trade.origin).toBe("WORKSPACE_SELECTION");
  expect(buy.execution.currency_confirmation.currency_code).toBe("EUR");
  const tid = buy.trade.id;
  const tradePath = `/trade-position/trades/${tid}`;
  const august = await post(
    tradePath + "/sales",
    capture(20, "2.50", "2026-08-12", false),
  );
  await page.goto(`/trade-management?trade_id=${tid}#sale-capture`);
  const saleForm = page.getByRole("form", {
    name: "Verkauf erfassen",
    exact: true,
  });
  await saleForm.getByLabel("Verkaufsmenge", { exact: true }).fill("30");
  await saleForm.getByLabel("Verkaufspreis", { exact: true }).fill("3.00");
  await saleForm
    .getByLabel("Verkaufsdatum", { exact: true })
    .fill("2026-09-02");
  await expect(
    saleForm.getByLabel("Ausführungswährung (Code)"),
  ).not.toBeVisible();
  const saleWrite = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(tradePath + "/sales"),
  );
  databaseState();
  await saleForm
    .getByRole("button", { name: "Teilverkauf erfassen", exact: true })
    .click();
  const saleResponse = await saleWrite;
  expect(saleResponse.status(), await saleResponse.text()).toBe(201);
  expect(saleResponse.request().postDataJSON()).not.toHaveProperty(
    "currency_confirmation",
  );
  const septemberFirst = await saleResponse.json();
  expect(septemberFirst.execution.currency_confirmation).toBeNull();
  expect(septemberFirst.execution.currency_resolution).toMatchObject({
    currency_code: "EUR",
    source: "PRIOR_BUYS",
    source_execution_ids: [buy.execution.id],
    confirmation_ids: [buy.execution.currency_confirmation.id],
  });
  const added = await post(
    tradePath + "/purchases",
    capture(50, "4.00", "2026-09-06", false),
  );
  const septemberLast = await post(
    tradePath + "/sales",
    capture(40, "2.50", "2026-09-12", false),
  );
  expect(septemberLast.position.open_quantity).toBe(60);
  expect(septemberLast.position.cost_basis).toBe("180.0000000000");
  const october = await post(
    tradePath + "/sales",
    capture(60, "3.50", "2026-10-03", false),
  );
  expect(october.position.is_closed).toBe(true);
  expect(october.position.realized_gross_pnl).toBe("50.0000000000");
  const reportUrl = (from: string, to: string) =>
    api +
    "/performance/realized-gross?" +
    new URLSearchParams({
      from_date: from,
      to_date: to,
      report_currency: "EUR",
      report_timezone: "Europe/Berlin",
    });
  const read = async () => {
    const pending = page.waitForResponse((response) =>
      response.url().startsWith(api + "/performance/realized-gross?"),
    );
    await page
      .getByRole("button", { name: "Bericht lesen", exact: true })
      .click();
    const response = await pending;
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const select = async (from: string, to: string) => {
    await page.getByLabel("Von (einschließlich)").fill(from);
    await page.getByLabel("Bis (einschließlich)").fill(to);
    const currency = page.getByLabel("Berichtswährung", { exact: true });
    await expect(currency).toHaveValue("EUR");
    await expect(currency).not.toBeEditable();
    await page.getByLabel("Berichtszeitzone (IANA)").fill("Europe/Berlin");
  };
  const beforeRead = databaseState();
  expect(beforeRead.tables.execution_currency_confirmations.count).toBe(1);
  reportReadWindow = true;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/performance/realized-gross");
  await expect(page.getByRole("form")).toHaveCount(1);
  await expect(
    page.getByRole("form", {
      name: "Performance-Zeitraum auswählen",
      exact: true,
    }),
  ).toBeVisible();
  expect(financialReads).toHaveLength(0);
  await select("2026-09-01", "2026-09-30");
  const original = await read();
  expect(original.definition_version).toBe("realized-gross-sell-v2");
  expect(original.summary.status).toBe("COMPLETE");
  expect(original.summary.total).toBe("10.0000000000");
  expect(original.counts).toMatchObject({
    examined: 4,
    in_period: 2,
    usable: 2,
    excluded: 2,
    unresolved: 0,
  });
  expect(
    original.items
      .filter((item: { status: string }) => item.status === "USABLE")
      .map(
        (item: { realized_gross_pnl_delta: string }) =>
          item.realized_gross_pnl_delta,
      ),
  ).toEqual(["30.0000000000", "-20.0000000000"]);
  expect(
    original.sources.every(
      (source: { time_precision: string; executed_at: unknown }) =>
        source.time_precision === "DATE_ONLY" && source.executed_at === null,
    ),
  ).toBe(true);
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  await expect(
    page.getByRole("article", {
      name: `Verkauf ${septemberFirst.execution.id}`,
      exact: true,
    }),
  ).toContainText("30,00 EUR");
  const secondRow = page.getByRole("article", {
    name: `Verkauf ${septemberLast.execution.id}`,
    exact: true,
  });
  await expect(secondRow).toContainText("-20,00 EUR");
  await secondRow
    .getByRole("button", { name: "Quellen und Berechnung", exact: true })
    .click();
  const provenance = page.getByRole("region", {
    name: `Herkunft SELL ${septemberLast.execution.id}`,
    exact: true,
  });
  for (const executionId of [
    buy.execution.id,
    august.execution.id,
    septemberFirst.execution.id,
    added.execution.id,
    septemberLast.execution.id,
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
  expect(
    original.items.find(
      (item: { execution_id: string }) =>
        item.execution_id === septemberLast.execution.id,
    ).cost_basis_execution_ids,
  ).toEqual([
    buy.execution.id,
    august.execution.id,
    septemberFirst.execution.id,
    added.execution.id,
  ]);
  await expect(provenance).toContainText("3.0000000000");
  await expect(provenance).toContainText("180.0000000000");
  const saleSource = original.sources.find(
    (source: { execution_id: string }) =>
      source.execution_id === septemberLast.execution.id,
  );
  expect(saleSource.currency_confirmation).toBeNull();
  expect(saleSource.currency_resolution).toMatchObject({
    currency_code: "EUR",
    source: "PRIOR_BUYS",
    confirmation_ids: [buy.execution.currency_confirmation.id],
  });
  await expect(provenance).toContainText(
    buy.execution.currency_confirmation.id,
  );
  await page.screenshot({
    path: testInfo.outputPath("september-desktop.png"),
    fullPage: true,
  });
  expect(databaseState().fingerprint).toBe(beforeRead.fingerprint);

  // UI8 retains the same native facts while changing report perspective. Local
  // row selection is part of this report URL, never a new financial read.
  const readsBeforeView = financialReads.length;
  await page.getByLabel("Zeilen anzeigen").selectOption("usable");
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("usable");
  await expect(page).toHaveURL(/report_view=usable/);
  expect(financialReads).toHaveLength(readsBeforeView);
  const salesContextUrl = page.url();
  const switchTo = async (kind: "realized-gross" | "closed-trades") => {
    const before = financialReads.length;
    const pending = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().startsWith(api + `/performance/${kind}?`),
    );
    await page
      .getByRole("button", {
        name:
          kind === "closed-trades"
            ? "Trades mit Vollabschluss im Zeitraum"
            : "Verkäufe im Zeitraum",
        exact: true,
      })
      .click();
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
  const samePeriodClosed = await switchTo("closed-trades");
  expect(samePeriodClosed.definition_version).toBe("closed-trade-gross-v1");
  expect(samePeriodClosed.filters).toEqual(original.filters);
  expect(samePeriodClosed.summary.status).toBe("EMPTY");
  expect(samePeriodClosed.counts.outside_period).toBe(1);
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  await expect(
    page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    }),
  ).toHaveCount(1);
  const closedContextUrl = page.url();
  const beforeBack = financialReads.length;
  await page.goBack();
  await expect(page).toHaveURL(salesContextUrl);
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("usable");
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  expect(financialReads.slice(beforeBack)).toHaveLength(1);
  expect(financialReads.at(-1)).toContain("/performance/realized-gross?");
  const beforeForward = financialReads.length;
  await page.goForward();
  await expect(page).toHaveURL(closedContextUrl);
  await expect(page.getByTestId("closed-trades-total")).toBeVisible();
  expect(financialReads.slice(beforeForward)).toHaveLength(1);
  expect(financialReads.at(-1)).toContain("/performance/closed-trades?");
  const samePeriodSales = await switchTo("realized-gross");
  expect(samePeriodSales.filters).toEqual(original.filters);
  expect(samePeriodSales.summary.total).toBe("10.0000000000");
  await expect(
    page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    }),
  ).toHaveCount(0);
  const beforeReload = financialReads.length;
  await page.reload();
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  await expect(page.getByLabel("Von (einschließlich)")).toHaveValue(
    "2026-09-01",
  );
  await expect(page.getByLabel("Bis (einschließlich)")).toHaveValue(
    "2026-09-30",
  );
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Europe/Berlin",
  );
  expect(financialReads.slice(beforeReload)).toHaveLength(1);
  expect(
    reportRequests.every(
      (sent) =>
        sent.method === "GET" && sent.url.startsWith(api + "/performance/"),
    ),
  ).toBe(true);
  expect(databaseState().fingerprint).toBe(beforeRead.fingerprint);
  reportReadWindow = false;
  await testInfo.attach("performance-workspace-read-only-switches", {
    body: JSON.stringify(
      { samePeriodClosed, samePeriodSales, reportRequests },
      null,
      2,
    ),
    contentType: "application/json",
  });

  const replacement = await post(
    tradePath + `/executions/${septemberLast.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 40,
      price_per_unit: "3.00",
      executed_on: "2026-09-12",
      execution_timezone: "Europe/Berlin",
    },
  );
  expect(replacement.position.realized_gross_pnl).toBe("70.0000000000");
  expect(replacement.execution.currency_confirmation).toBeNull();
  expect(replacement.execution.currency_resolution.currency_code).toBe("EUR");
  expect(databaseState().tables.execution_currency_confirmations.count).toBe(1);
  const corrected = await read();
  expect(corrected.summary.total).toBe("30.0000000000");
  expect(corrected.basis.id).not.toBe(original.basis.id);
  expect(
    corrected.items.map((item: { execution_id: string }) => item.execution_id),
  ).not.toContain(septemberLast.execution.id);
  expect(
    corrected.sources.find(
      (source: { execution_id: string }) =>
        source.execution_id === septemberLast.execution.id,
    ),
  ).toMatchObject({
    is_effective: false,
    superseded_by_execution_id: replacement.execution.id,
  });
  await expect(
    page.getByText(
      "Der Quellenstand hat sich gegenüber dem mitgegebenen oder zuletzt gelesenen Stand dieser Auswahl geändert. " +
        "Ergebnis, Zähler, Zeilen, Herkunft und gegebenenfalls Abschlusskennzahlen wurden gemeinsam durch den neu gelesenen Stand ersetzt.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "30,00 EUR",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: testInfo.outputPath("september-corrected-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const all = await (
    await request.get(reportUrl("2026-08-01", "2026-10-31"))
  ).json();
  expect(all.summary.total).toBe("70.0000000000");

  // A compatible BUY with no evidence remains unknown. One explicit purchase
  // confirmation then qualifies its SELL; no sale confirmation is written.
  const unknownBuy = await post("/trade-position/purchases/external", {
    product_id: product.id,
    ...capture(1, "2.00", "2026-07-01", false),
  });
  const unknownSell = await post(
    `/trade-position/trades/${unknownBuy.trade.id}/sales`,
    capture(1, "2.00", "2026-07-02", false),
  );
  await select("2026-07-01", "2026-07-31");
  const unknown = await read();
  expect(unknown.summary).toMatchObject({
    status: "NOT_COMPUTABLE",
    total: null,
    subtotal: null,
  });
  await expect(
    page.getByRole("heading", {
      name: "Auswahl nicht berechenbar",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "Nicht berechenbar",
  );
  await page.goto(
    `/trade-management?trade_id=${unknownBuy.trade.id}#execution-dates`,
  );
  const booking = page.getByRole("article", {
    name: `Buchung ${unknownBuy.execution.id}`,
    exact: true,
  });
  await booking
    .getByRole("button", { name: "Währung prüfen / bestätigen", exact: true })
    .click();
  const form = booking.getByRole("form", {
    name: "Ausführungswährung bestätigen",
    exact: true,
  });
  await form.getByLabel("Ausführungswährung (Code)").fill("EUR");
  await expect(form.getByRole("checkbox")).toHaveCount(0);
  const confirmedWrite = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response
        .url()
        .endsWith(
          `/executions/${unknownBuy.execution.id}/currency-confirmations`,
        ),
  );
  databaseState();
  await form
    .getByRole("button", { name: "Währungsbestätigung speichern", exact: true })
    .click();
  expect((await confirmedWrite).status()).toBe(201);
  await expect(
    booking.getByText(/Währung bestätigt\. Eine erneute Auswertung/),
  ).toBeVisible();
  await page.goto("/performance/realized-gross");
  await select("2026-07-01", "2026-07-31");
  const measuredZero = await read();
  expect(measuredZero.summary).toMatchObject({
    status: "COMPLETE",
    total: "0.0000000000",
  });
  expect(
    measuredZero.sources.find(
      (source: { execution_id: string }) =>
        source.execution_id === unknownSell.execution.id,
    ),
  ).toMatchObject({
    currency_confirmation: null,
    currency_resolution: { currency_code: "EUR", source: "PRIOR_BUYS" },
  });
  expect(databaseState().tables.execution_currency_confirmations.count).toBe(2);
  await expect(page.getByTestId("realized-gross-total")).toHaveText("0,00 EUR");
  await expect(
    page.getByRole("heading", {
      name: "Vollständig auswertbare Auswahl",
      exact: true,
    }),
  ).toBeVisible();
  await select("2026-06-01", "2026-06-30");
  const empty = await read();
  expect(empty.summary).toMatchObject({ status: "EMPTY", total: "0" });
  await expect(
    page.getByRole("heading", {
      name: "Keine wirksamen Verkäufe in dieser Auswahl",
      exact: true,
    }),
  ).toBeVisible();
  await qualifyTradeSources(page, request, testInfo, {
    api,
    root,
    tradeId: tid,
    productId: product.id,
    planId: plan.plan.id,
    planVersionId: plan.latest_version.id,
    replacedExecutionId: septemberLast.execution.id,
    replacementExecutionId: replacement.execution.id,
    databaseState,
  });
  expect(failures).toEqual([]);
  await testInfo.attach("actual-owner-api-reports", {
    body: JSON.stringify(
      { original, corrected, unknown, measuredZero, empty },
      null,
      2,
    ),
    contentType: "application/json",
  });
  await testInfo.attach("postgres-read-only-proof", {
    body: JSON.stringify(beforeRead, null, 2),
    contentType: "application/json",
  });
});
