import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

// Explicit qualification only: the marked disposable PostgreSQL database is
// independently verified before the first owner write. No HTTP result fixtures.
test("real PostgreSQL: period SELL contributions, sources, correction and currency confirmation", async ({
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
  expect(initial.schema_revision).toBe("20261017_0047");
  expect(initial.postgresql).toMatch(/^PostgreSQL 17\./);
  expect(initial.tables.execution_records.count).toBe(0);
  const api = `${baseURL}/api/api/v1`;
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.route("**/*", (route) => {
    if (new URL(route.request().url()).origin === baseURL)
      return route.continue();
    failures.push(
      `Unexpected external browser request: ${route.request().url()}`,
    );
    return route.abort();
  });
  const post = async (path: string, data?: object) => {
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
    strike_currency_code: "EUR",
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
  const buy = await post("/trade-position/purchases/external", {
    product_id: product.id,
    ...capture(100, "2.00", "2026-08-05"),
  });
  const tid = buy.trade.id;
  const tradePath = `/trade-position/trades/${tid}`;
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
  expect(septemberLast.position.cost_basis).toBe("180.0000000000");
  const october = await post(
    tradePath + "/sales",
    capture(60, "3.50", "2026-10-03"),
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
    await page.getByLabel("Berichtswährung", { exact: true }).fill("EUR");
    await page.getByLabel("Berichtszeitzone (IANA)").fill("Europe/Berlin");
  };
  const beforeRead = databaseState();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/performance/realized-gross");
  await select("2026-09-01", "2026-09-30");
  const original = await read();
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
  await page.screenshot({
    path: testInfo.outputPath("september-desktop.png"),
    fullPage: true,
  });
  expect(databaseState().fingerprint).toBe(beforeRead.fingerprint);

  const replacement = await post(
    tradePath + `/executions/${septemberLast.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 40,
      price_per_unit: "3.00",
      executed_on: "2026-09-12",
      execution_timezone: "Europe/Berlin",
      currency_confirmation: confirmed,
    },
  );
  expect(replacement.position.realized_gross_pnl).toBe("70.0000000000");
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
    page.getByText(/Der Quellenstand hat sich seit dem letzten Lesen/),
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

  // A compatible capture with no declaration remains unknown until this user's
  // explicit owner action. Product/listing/report EUR must not fill it silently.
  const unknownBuy = await post("/trade-position/purchases/external", {
    product_id: product.id,
    ...capture(1, "2.00", "2026-07-01"),
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
    name: `Buchung ${unknownSell.execution.id}`,
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
  await form
    .getByRole("checkbox", {
      name: /Ich bestätige EUR als tatsächliche Währung/,
    })
    .check();
  const confirmedWrite = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response
        .url()
        .endsWith(
          `/executions/${unknownSell.execution.id}/currency-confirmations`,
        ),
  );
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
