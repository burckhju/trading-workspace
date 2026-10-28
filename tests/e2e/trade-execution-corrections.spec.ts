import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

import type {
  ExecutionResponse,
  PositionResponse,
  TradeTimelineEntryResponse,
} from "../../frontend/src/features/trade/types/api";

test.use({ baseURL: "http://localhost:8080", timezoneId: "Europe/Berlin" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Only the existing disposable E2E database may receive these synthetic facts",
);

// Only recorded facts are immutable. Currency resolution is a fresh owner read
// and may legitimately change when an effective BUY predecessor is replaced.
function recordedFacts(entry: TradeTimelineEntryResponse) {
  const { currency_resolution: resolution, ...facts } = entry;
  void resolution;
  return facts;
}

test("real BUY and SELL amount corrections retain history, reopen the position, and reject a historical oversell atomically", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(90_000);
  const root = "http://127.0.0.1:8000/api/v1";
  const marker = randomUUID();
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `UI7 synthetic issuer ${marker}`,
      display_name: "UI7 synthetic issuer",
    },
  });
  expect(issuer.status()).toBe(201);
  const venuesResponse = await request.get(
    `${root}/market-reference-data/trading-venues`,
  );
  expect(venuesResponse.status()).toBe(200);
  const venues = (await venuesResponse.json()).items;
  const underlying = await request.post(`${root}/underlyings`, {
    data: {
      name: `UI7 synthetic underlying ${marker}`,
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.find(
          (item: { mic: string }) => item.mic === "XETR",
        ).id,
        ticker: `U${marker.slice(0, 8)}`,
        currency_code: "USD",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: (await issuer.json()).id,
      underlying_id: (await underlying.json()).id,
      display_name: `UI7 synthetic warrant ${marker}`,
      option_direction: "CALL",
      strike: "500",
      strike_currency_code: "USD",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  const productId = (await warrant.json()).id;
  const purchase = await request.post(
    `${root}/trade-position/purchases/external`,
    {
      data: {
        product_id: productId,
        quantity: 10,
        price_per_unit: "2.0000000000",
        executed_at: "2026-08-17T08:30:01.123456Z",
        request_id: randomUUID(),
        currency_confirmation: {
          currency_code: "EUR",
          source: "USER_CONFIRMED",
          note: "UI7 synthetic original receipt",
        },
      },
    },
  );
  expect(purchase.status()).toBe(201);
  const original = await purchase.json();
  const tradeId = original.trade.id;
  const url = `${root}/trade-position/trades/${tradeId}`;
  const sale = await request.post(`${url}/sales`, {
    data: {
      quantity: 10,
      price_per_unit: "3.0000000000",
      executed_on: "2026-08-22",
      execution_timezone: "Europe/Berlin",
      request_id: randomUUID(),
    },
  });
  expect(sale.status()).toBe(201);
  const initialSale: ExecutionResponse = (await sale.json()).execution;

  async function timeline(): Promise<TradeTimelineEntryResponse[]> {
    const response = await request.get(`${url}/timeline`);
    expect(response.status()).toBe(200);
    return response.json();
  }
  async function position(): Promise<PositionResponse> {
    const response = await request.get(`${url}/position`);
    expect(response.status()).toBe(200);
    return response.json();
  }
  const initialHistory = await timeline();
  const originalBuy = initialHistory.find(
    (entry) => entry.id === original.execution.id,
  )!;
  const originalSell = initialHistory.find(
    (entry) => entry.id === initialSale.id,
  )!;
  const confirmationId = originalBuy.currency_confirmation!.id;
  expect(originalBuy.currency_resolution?.source).toBe("USER_CONFIRMED");
  expect(originalSell.currency_confirmation).toBeNull();
  expect(originalSell.currency_resolution).toEqual({
    currency_code: "EUR",
    source: "PRIOR_BUYS",
    source_execution_ids: [originalBuy.id],
    confirmation_ids: [confirmationId],
    evidence_ids: [],
    evidence: [],
    reason: null,
    resolver_version: "execution-currency-v3",
  });

  const writes: Array<{ path: string; body: Record<string, unknown> }> = [];
  // Observe real browser traffic. No API routing, fulfillment or mocks are used.
  // Capturing every API write also detects accidental management/learning writes.
  page.on("request", (req) => {
    if (req.method() === "POST" && req.url().includes("/api/")) {
      writes.push({
        path: new URL(req.url()).pathname,
        body: req.postDataJSON(),
      });
    }
  });
  const evidence: Array<{
    stage: string;
    history: TradeTimelineEntryResponse[];
    position: PositionResponse;
  }> = [];
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/trade-management?trade_id=${tradeId}#execution-dates`);
  const panel = page.getByRole("region", { name: "Kauf- und Verkaufsdaten" });
  const form = panel.getByRole("form", { name: "Buchung korrigieren" });
  const quantity = form.getByLabel("Menge", { exact: true });
  const price = form.getByLabel("Preis je Einheit", { exact: true });
  const save = form.getByRole("button", { name: "Korrektur speichern" });
  const confirmation = form.getByRole("checkbox", {
    name: /Ich bestätige die geänderten Buchungsdaten/,
  });

  async function expectPosition(
    stage: string,
    open: number,
    cost: RegExp,
    gross: RegExp,
    uiCost: string,
    uiGross: string,
  ) {
    const readback = await position();
    expect(readback).toMatchObject({
      trade_id: tradeId,
      product_id: productId,
      open_quantity: open,
      is_closed: open === 0,
      opened_at: originalBuy.occurred_at,
      last_execution_on: "2026-08-22",
    });
    expect(readback.cost_basis).toMatch(cost);
    expect(readback.realized_gross_pnl).toMatch(gross);
    expect(readback.average_entry_price).toMatch(
      stage === "initial" ? /^2(?:\.0+)?$/ : /^2\.50*$/,
    );
    expect(readback.closed_on).toBe(open === 0 ? "2026-08-22" : null);
    if (open !== 0) expect(readback.closed_at).toBeNull();
    await expect(
      page.getByRole("heading", {
        name: open === 0 ? "CLOSED" : "OPEN",
        exact: true,
      }),
    ).toHaveCount(1);
    for (const [label, expected] of [
      ["Offene Menge", String(open)],
      ["Cost Basis", uiCost],
      ["Realized gross P&L", uiGross],
    ]) {
      const name = page.getByText(label, { exact: true });
      await expect(name).toHaveCount(1);
      await expect(name.locator("..").locator("dd")).toHaveText(expected);
    }
    evidence.push({ stage, history: await timeline(), position: readback });
    return readback;
  }
  async function open(entry: TradeTimelineEntryResponse) {
    const row = panel.getByRole("article", {
      name: `Buchung ${entry.id}`,
      exact: true,
    });
    const button = row.getByRole("button", {
      name:
        entry.execution_side === "BUY"
          ? "Kauf korrigieren"
          : "Verkauf korrigieren",
      exact: true,
    });
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(form).toHaveCount(1);
    await expect(quantity).toHaveValue(String(entry.quantity));
    await expect(price).toHaveValue(entry.price_per_unit!);
    await expect(row.getByText(/^Ausgeführt:/)).toHaveCount(0);
    await expect(row).toContainText(entry.id);
    await expect(form).toContainText("EUR");
    await expect(save).toBeDisabled();
    return row;
  }
  async function correct(
    entry: TradeTimelineEntryResponse,
    field: "Menge" | "Preis je Einheit",
    value: string,
    expectedBody: Record<string, unknown>,
  ) {
    const before = await timeline();
    await open(entry);
    await form.getByLabel(field, { exact: true }).fill(value);
    const changes = form.getByRole("table", {
      name: "Geänderte Buchungsdaten",
    });
    await expect(changes.getByRole("row")).toHaveCount(2);
    await expect(
      changes.getByRole("rowheader", { name: field, exact: true }),
    ).toBeVisible();
    await expect(changes.getByRole("cell").nth(0)).toHaveText(
      field === "Menge" ? String(entry.quantity) : entry.price_per_unit!,
    );
    await expect(changes.getByRole("cell").nth(1)).toHaveText(
      String(
        field === "Menge" ? expectedBody.quantity : expectedBody.price_per_unit,
      ),
    );
    await confirmation.check();
    const responsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/executions/${entry.id}/corrections`),
    );
    await save.click();
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    const receipt = await response.json();
    expect(receipt.execution).toMatchObject({
      trade_id: tradeId,
      product_id: productId,
      side: entry.execution_side,
    });
    expect(receipt.execution.id).not.toBe(entry.id);
    expect(writes.at(-1)!.path).toContain(
      `/executions/${entry.id}/corrections`,
    );
    expect(writes.at(-1)!.body).toEqual(expectedBody);
    await expect(panel.getByRole("status")).toContainText("Buchung korrigiert");
    await expect(form).toHaveCount(0);
    const after = await timeline();
    expect(after).toHaveLength(before.length + 1);
    for (const previous of before) {
      expect(
        recordedFacts(after.find((item) => item.id === previous.id)!),
      ).toEqual(recordedFacts(previous));
    }
    const replacement = after.find(
      (entry) => entry.id === receipt.execution.id,
    )!;
    expect(replacement).toMatchObject({
      kind: "EXECUTION",
      trade_id: tradeId,
      execution_side: entry.execution_side,
      supersedes_id: entry.id,
      occurred_at: entry.occurred_at,
      executed_on: entry.executed_on,
      execution_timezone: entry.execution_timezone,
      currency_confirmation: null,
    });
    expect(replacement.currency_resolution).toMatchObject({
      currency_code: "EUR",
      source:
        entry.execution_side === "BUY" ? "REPLACED_EXECUTION" : "PRIOR_BUYS",
      confirmation_ids: [confirmationId],
    });
    expect(after.filter((entry) => entry.currency_confirmation)).toHaveLength(
      1,
    );
    await expect(panel.getByRole("article")).toHaveCount(2);
    await expect(
      panel.getByRole("article", { name: `Buchung ${entry.id}`, exact: true }),
    ).toHaveCount(0);
    await expect(
      panel.getByRole("article", {
        name: `Buchung ${replacement.id}`,
        exact: true,
      }),
    ).toBeVisible();
    return replacement;
  }

  await expectPosition(
    "initial",
    0,
    /^0(?:\.0+)?(?:e[+-]?\d+)?$/i,
    /^10(?:\.0+)?$/,
    "0",
    "10",
  );
  await expect(panel.getByRole("article")).toHaveCount(2);
  await open(originalBuy);
  await quantity.fill("10.5");
  await expect(quantity).toHaveAttribute("aria-invalid", "true");
  await expect(form.getByRole("alert")).toContainText("positive ganze Menge");
  await expect(save).toBeDisabled();
  await quantity.fill("10");
  await price.fill("2.00000000001");
  await expect(price).toHaveAttribute("aria-invalid", "true");
  await expect(form.getByRole("alert")).toContainText("nicht gerundet");
  await expect(save).toBeDisabled();
  // Equivalent decimal spelling is not a correction and cannot produce a POST.
  await price.fill("2,0000000000");
  await confirmation.check();
  await expect(save).toBeDisabled();
  expect(writes).toEqual([]);
  await price.fill(originalBuy.price_per_unit!);
  await form.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(form).toHaveCount(0);

  // Keep management drafts open while real corrections refresh the page.
  await page.getByLabel("Stop", { exact: true }).fill("1.75");
  await page
    .getByLabel("Instrument für Stop", { exact: true })
    .selectOption("WARRANT");
  await page.getByLabel("Währung für Stop", { exact: true }).fill("EUR");
  await page.getByLabel("Target", { exact: true }).fill("4.5");
  await page
    .getByLabel("Instrument für Target", { exact: true })
    .selectOption("WARRANT");
  await page.getByLabel("Währung für Target", { exact: true }).fill("EUR");
  await page
    .getByLabel("Aktuelle These", { exact: true })
    .fill("UI7 unsaved thesis");

  const buyPrice = await correct(originalBuy, "Preis je Einheit", "2,50", {
    side: "BUY",
    quantity: 10,
    price_per_unit: "2.5",
    executed_at: originalBuy.occurred_at,
  });
  await expectPosition(
    "buy-price",
    0,
    /^0(?:\.0+)?(?:e[+-]?\d+)?$/i,
    /^5(?:\.0+)?$/,
    "0",
    "5",
  );
  const buyQuantity = await correct(buyPrice, "Menge", "12", {
    side: "BUY",
    quantity: 12,
    price_per_unit: buyPrice.price_per_unit,
    executed_at: originalBuy.occurred_at,
  });
  await expectPosition(
    "buy-quantity",
    2,
    /^5(?:\.0+)?$/,
    /^5(?:\.0+)?$/,
    "5",
    "5",
  );
  // Read the dependent SELL again after its effective BUY source changed.
  const rereadSell = (await timeline()).find(
    (entry) => entry.id === originalSell.id,
  )!;
  expect(rereadSell.currency_resolution?.source_execution_ids).toContain(
    buyQuantity.id,
  );
  const sellQuantity = await correct(rereadSell, "Menge", "8", {
    side: "SELL",
    quantity: 8,
    price_per_unit: originalSell.price_per_unit,
    executed_on: "2026-08-22",
    execution_timezone: "Europe/Berlin",
  });
  await expectPosition(
    "sell-quantity",
    4,
    /^10(?:\.0+)?$/,
    /^4(?:\.0+)?$/,
    "10",
    "4",
  );
  const sellPrice = await correct(sellQuantity, "Preis je Einheit", "3,50", {
    side: "SELL",
    quantity: 8,
    price_per_unit: "3.5",
    executed_on: "2026-08-22",
    execution_timezone: "Europe/Berlin",
  });
  const finalPosition = await expectPosition(
    "sell-price",
    4,
    /^10(?:\.0+)?$/,
    /^8(?:\.0+)?$/,
    "10",
    "8",
  );
  const beforeRejected = await timeline();

  await open(buyQuantity);
  await quantity.fill("7");
  await confirmation.check();
  const rejectedPromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`/executions/${buyQuantity.id}/corrections`),
  );
  await save.click();
  const rejected = await rejectedPromise;
  expect(rejected.status()).toBe(422);
  await expect(panel.getByText(/Korrektur nicht bestätigt:/)).toContainText(
    "SELL quantity exceeds current open quantity",
  );
  await expect(quantity).toHaveValue("7");
  await expect(confirmation).not.toBeChecked();
  await expect(panel.getByText(/Buchung korrigiert/)).toHaveCount(0);
  expect(await timeline()).toEqual(beforeRejected);
  expect(await position()).toEqual(finalPosition);
  expect(writes).toHaveLength(5);
  expect(writes[4].body).toEqual({
    side: "BUY",
    quantity: 7,
    price_per_unit: buyQuantity.price_per_unit,
    executed_at: originalBuy.occurred_at,
  });
  expect(writes.every((write) => write.path.endsWith("/corrections"))).toBe(
    true,
  );

  for (const [label, expected] of [
    ["Stop", "1.75"],
    ["Target", "4.5"],
    ["Aktuelle These", "UI7 unsaved thesis"],
    ["Währung für Stop", "EUR"],
    ["Währung für Target", "EUR"],
    ["Instrument für Stop", "WARRANT"],
    ["Instrument für Target", "WARRANT"],
  ]) {
    await expect(page.getByLabel(label, { exact: true })).toHaveValue(expected);
  }
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await testInfo.attach("ui7-narrow-correction", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  await panel.getByRole("tab", { name: "Historie", exact: true }).click();
  const discard = page.getByRole("alertdialog", {
    name: "Ungespeicherte Änderungen",
  });
  await expect(
    discard.getByRole("button", { name: "Hier bleiben" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(quantity).toHaveValue("7");
  await panel.getByRole("tab", { name: "Historie", exact: true }).click();
  await discard
    .getByRole("button", { name: "Eingaben verwerfen und wechseln" })
    .click();
  await expect(form).toHaveCount(0);
  await expect(panel.getByRole("article")).toHaveCount(0);
  for (const version of [
    originalBuy,
    originalSell,
    buyPrice,
    buyQuantity,
    sellQuantity,
    sellPrice,
  ]) {
    await expect(
      panel.getByText(version.id, { exact: false }).first(),
    ).toBeVisible();
  }
  expect(writes).toHaveLength(5);
  await testInfo.attach("ui7-real-correction-readbacks", {
    body: JSON.stringify(
      {
        tradeId,
        productId,
        writes,
        stages: evidence,
        rejectedHistory: await timeline(),
        rejectedPosition: await position(),
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
});
