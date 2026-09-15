import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test("held warrant quote sources are visible from workspace without extra writes or invented coverage", async ({
  page,
  request,
}) => {
  test.skip(
    process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
    "Synthetic capture only in disposable CI database",
  );
  const root = "http://127.0.0.1:8000/api/v1";
  const marker = randomUUID();
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `Synthetic coverage ${marker}`,
      display_name: "Synthetic coverage issuer",
    },
  });
  expect(issuer.status()).toBe(201);
  const venues = await (
    await request.get(`${root}/market-reference-data/trading-venues`)
  ).json();
  const underlying = await request.post(`${root}/underlyings`, {
    data: {
      name: `Synthetic coverage ${marker}`,
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.items.find(
          (v: { mic: string }) => v.mic === "XETR",
        ).id,
        ticker: `Q${marker.slice(0, 8)}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const name = `Synthetic coverage warrant ${marker}`;
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: (await issuer.json()).id,
      underlying_id: (await underlying.json()).id,
      display_name: name,
      option_direction: "CALL",
      strike: "100",
      strike_currency_code: "EUR",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  const buy = await request.post(`${root}/trade-position/purchases/external`, {
    data: {
      product_id: (await warrant.json()).id,
      quantity: 10,
      price_per_unit: "1.00",
      executed_on: "2026-08-17",
      execution_timezone: "Europe/Berlin",
      request_id: randomUUID(),
    },
  });
  expect(buy.status()).toBe(201);
  const trade = (await buy.json()).trade;
  const before = await (
    await request.get(`${root}/trade-position/trades/${trade.id}/timeline`)
  ).json();
  const writes: string[] = [];
  page.on("request", (req) => {
    if (req.method() !== "GET") writes.push(req.url());
  });
  await page.goto("/workspace");
  await page.getByText("Automatischer Kursabruf", { exact: true }).click();
  const panel = page.getByRole("region", {
    name: "Kursquellen im Depot",
    exact: true,
  });
  await panel
    .getByRole("button", { name: "Kursquellen im Depot prüfen", exact: true })
    .click();
  const row = panel.getByRole("row").filter({ hasText: name });
  await expect(row).toBeVisible();
  await expect(
    row.getByText("Keine nutzbare Kurszuordnung", { exact: true }),
  ).toBeVisible();
  await row.getByText("Kurswege (0)", { exact: true }).click();
  await expect(
    row.getByText(/Keine passende gespeicherte Notierung/),
  ).toBeVisible();
  await panel.getByLabel("Nur Prüfbedarf", { exact: true }).check();
  await expect(row).toBeVisible();
  await expect(panel.getByText(/keine Orderfreigabe/)).toBeVisible();
  expect(writes).toEqual([]);
  expect(
    await (
      await request.get(`${root}/trade-position/trades/${trade.id}/timeline`)
    ).json(),
  ).toEqual(before);
});
