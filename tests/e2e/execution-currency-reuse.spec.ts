import { randomUUID } from "node:crypto";
import { expect, test, type APIResponse, type Request } from "@playwright/test";

test.use({
  baseURL: process.env.TRADE_E2E_UI_URL ?? "http://localhost:8080",
  timezoneId: "Europe/Berlin",
});
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Requires an explicitly disposable test stack; never enable on a user depot",
);

async function body(response: APIResponse, status = 201) {
  expect(response.status(), await response.text()).toBe(status);
  return response.json();
}

test("historical currency is reused through an explicit initial BUY, additional BUY and partial SELL", async ({
  page,
  request,
}) => {
  const root = process.env.TRADE_E2E_API_URL ?? "http://127.0.0.1:8000/api/v1";
  const token = randomUUID().slice(0, 8);
  // Every fact in this journey is a synthetic, explicitly created test fixture.
  const issuer = await body(
    await request.post(`${root}/market-reference-data/issuers`, {
      data: {
        legal_name: `Synthetic UX1 ${randomUUID()}`,
        display_name: "Synthetic UX1",
      },
    }),
  );
  const venues = await body(
    await request.get(`${root}/market-reference-data/trading-venues`),
    200,
  );
  const venueId = venues.items.find(
    (venue: { mic: string }) => venue.mic === "XETR",
  ).id;
  const underlying = await body(
    await request.post(`${root}/underlyings`, {
      data: {
        name: `Synthetic UX1 stock ${token}`,
        type: "STOCK",
        primary_listing: {
          trading_venue_id: venueId,
          ticker: `UX${token}`,
          currency_code: "EUR",
        },
      },
    }),
  );
  const warrant = await body(
    await request.post(`${root}/warrants`, {
      data: {
        issuer_id: issuer.id,
        underlying_id: underlying.id,
        display_name: `Synthetic UX1 warrant ${token}`,
        option_direction: "CALL",
        strike: "100",
        strike_currency_code: "EUR",
        maturity_date: "2099-12-31",
        ratio: "0.1",
      },
    }),
  );
  await body(
    await request.post(`${root}/warrants/${warrant.id}/listings`, {
      data: {
        trading_venue_id: venueId,
        symbol: `UXL${token}`,
        quotation_currency_code: "EUR",
      },
    }),
  );
  const evidenceUrl = `${root}/warrants/${warrant.id}/currency-evidence`;
  const evidence = await body(
    await request.post(evidenceUrl, {
      data: {
        kind: "HISTORICAL_LISTINGS",
        request_id: randomUUID(),
        confirmation: "CONFIRM_SOURCE_REVIEW",
        source_reference: `Synthetic archived venue statement ${token}`,
        valid_from: "2026-08-01T00:00:00Z",
        valid_to: "2026-09-01T00:00:00Z",
        complete_listing_set: true,
        listings: [{ trading_venue_id: venueId, currency_code: "EUR" }],
      },
    }),
  );
  const plan = await body(
    await request.post(`${root}/trade-plans`, {
      data: {
        origin_type: "MANUAL",
        underlying_id: underlying.id,
        thesis: "Synthetic UX1 workflow",
        entry: { type: "PRICE", currency: "EUR", price: "100" },
        invalidation: { stop_price: "95" },
        targets: [{ sequence: 1, price: "110" }],
        risk_assumptions: { thesis_risk: "Synthetic test risk" },
      },
    }),
  );
  const versionUrl = `${root}/trade-plans/${plan.plan.id}/versions/${plan.latest_version.id}`;
  await body(await request.post(`${versionUrl}/submit-review`), 200);
  await body(await request.post(`${versionUrl}/approve`), 200);
  const started = await body(
    await request.post(`${root}/product-selection-runs`, {
      data: {
        trade_plan_id: plan.plan.id,
        trade_plan_version_id: plan.latest_version.id,
      },
    }),
  );
  expect(started.evaluations).toHaveLength(1);
  const selected = await body(
    await request.post(
      `${root}/product-selection-runs/${started.run.id}/selection`,
      {
        data: {
          product_evaluation_id: started.evaluations[0].id,
          rationale:
            "Explicit synthetic selection; no quote is treated as an execution.",
        },
      },
    ),
  );
  const writes: Request[] = [];
  page.on("request", (outgoing) => {
    if (
      ["POST", "PUT", "PATCH", "DELETE"].includes(outgoing.method()) &&
      outgoing.url().includes("/api/v1/")
    )
      writes.push(outgoing);
  });
  await page.goto(`/product-selection?run_id=${started.run.id}`);
  await page.getByLabel("Kaufdatum", { exact: true }).fill("2026-08-17");
  await expect(
    page.getByText(/Vorhandene Währung: EUR · automatisch aus historischen/),
  ).toBeVisible();
  await expect(page.getByLabel("Ausführungswährung (Code)")).toHaveCount(0);
  await expect(page.getByLabel("Kaufmenge")).toHaveValue("");
  await expect(page.getByLabel("Kaufpreis")).toHaveValue("");
  expect(writes).toHaveLength(0);
  await page.getByText("Verwendete Währungsherkunft", { exact: true }).click();
  await expect(
    page.getByText(`Quelle: Synthetic archived venue statement ${token}`, {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Kaufmenge").fill("10");
  await page.getByLabel("Kaufpreis").fill("2,35");
  const captureResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/purchases/from-selection"),
  );
  await page
    .getByRole("button", { name: "BUY erfassen und Position eröffnen" })
    .click();
  const capturedResponse = await captureResponse;
  expect(capturedResponse.status()).toBe(201);
  const captured = await capturedResponse.json();
  await expect(page.getByText(/Kauf wurde als BUY erfasst/)).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(captured.trade).toMatchObject({
    product_id: warrant.id,
    trade_plan_id: plan.plan.id,
    trade_plan_version_id: plan.latest_version.id,
    product_selection_id: selected.selection.id,
  });
  expect(captured.execution.currency_confirmation).toBeNull();
  expect(captured.execution.currency_resolution).toMatchObject({
    currency_code: "EUR",
    source: "HISTORICAL_LISTINGS",
    confirmation_ids: [],
    evidence_ids: [evidence.id],
  });
  await page
    .getByRole("link", { name: "Position verwalten und Monitoring öffnen" })
    .click();
  const additional = page.getByRole("form", { name: "Nachkauf erfassen" });
  await additional
    .getByLabel("Nachkaufdatum", { exact: true })
    .fill("2026-08-18");
  await expect(
    additional.getByText(
      /Vorhandene Währung: EUR · automatisch aus historischen/,
    ),
  ).toBeVisible();
  await expect(additional.getByLabel("Ausführungswährung (Code)")).toHaveCount(
    0,
  );
  expect(writes).toHaveLength(1);
  await additional.getByLabel("Nachkaufmenge").fill("5");
  await additional.getByLabel("Nachkaufpreis").fill("2");
  const additionalResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`/trades/${captured.trade.id}/purchases`),
  );
  await additional.getByRole("button", { name: "Nachkauf speichern" }).click();
  const boughtResponse = await additionalResponse;
  expect(boughtResponse.status()).toBe(201);
  const bought = await boughtResponse.json();
  expect(bought.execution.currency_confirmation).toBeNull();
  expect(bought.execution.currency_resolution).toMatchObject({
    currency_code: "EUR",
    source: "HISTORICAL_LISTINGS",
    confirmation_ids: [],
  });
  await expect(
    additional.getByText("Nachkauf beim bestehenden Trade erfasst."),
  ).toBeVisible();
  const sale = page.getByRole("form", { name: "Verkauf erfassen" });
  await sale.getByLabel("Verkaufsdatum", { exact: true }).fill("2026-08-19");
  await expect(
    sale.getByText(/Vorhandene Währung: EUR · automatisch aus historischen/),
  ).toBeVisible();
  await expect(sale.getByLabel("Ausführungswährung (Code)")).toHaveCount(0);
  await expect(sale.getByLabel("Verkaufsmenge")).toHaveValue("");
  await expect(sale.getByLabel("Verkaufspreis")).toHaveValue("");
  expect(writes).toHaveLength(2);
  await sale.getByLabel("Verkaufsmenge").fill("4");
  await sale.getByLabel("Verkaufspreis").fill("2.5");
  const saleResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`/trades/${captured.trade.id}/sales`),
  );
  await sale.getByRole("button", { name: "Teilverkauf erfassen" }).click();
  const soldResponse = await saleResponse;
  expect(soldResponse.status()).toBe(201);
  const sold = await soldResponse.json();
  expect(sold.position.open_quantity).toBe(11);
  expect(sold.execution.currency_confirmation).toBeNull();
  expect(sold.execution.currency_resolution).toMatchObject({
    currency_code: "EUR",
    source: "HISTORICAL_LISTINGS",
    confirmation_ids: [],
  });
  expect(writes).toHaveLength(3);
  expect(
    writes.every(
      (write) => write.postDataJSON().currency_confirmation === undefined,
    ),
  ).toBe(true);
  const timeline = await body(
    await request.get(
      `${root}/trade-position/trades/${captured.trade.id}/timeline`,
    ),
    200,
  );
  expect(
    timeline.filter((entry: { kind: string }) => entry.kind === "EXECUTION"),
  ).toHaveLength(3);
  expect(timeline.map((entry: { id: string }) => entry.id).sort()).toEqual(
    [captured.execution.id, bought.execution.id, sold.execution.id].sort(),
  );
  expect((await body(await request.get(evidenceUrl), 200)).history).toEqual([
    evidence,
  ]);
});
