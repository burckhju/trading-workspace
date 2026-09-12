import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Requires an explicitly disposable test stack",
);

test("backdated purchase, duplicate prevention, explicit additional purchase and cancellation", async ({
  page,
  request,
}) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `Trade safety ${randomUUID()}`,
      display_name: "Trade safety browser",
    },
  });
  expect(issuer.status()).toBe(201);
  const venues = (
    await (
      await request.get(`${root}/market-reference-data/trading-venues`)
    ).json()
  ).items;
  const underlying = await request.post(`${root}/underlyings`, {
    data: {
      name: "Trade safety stock",
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.find((v: { mic: string }) => v.mic === "XETR")
          .id,
        ticker: `TS${Date.now()}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: (await issuer.json()).id,
      underlying_id: (await underlying.json()).id,
      display_name: "Trade safety browser warrant",
      option_direction: "CALL",
      strike: "500",
      strike_currency_code: "USD",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  const productId = (await warrant.json()).id;
  const payload = {
    product_id: productId,
    quantity: 10,
    price_per_unit: "0.55",
    executed_on: "2026-08-17",
    execution_timezone: "Europe/Berlin",
    request_id: randomUUID(),
  };
  const initial = await request.post(
    `${root}/trade-position/purchases/external`,
    { data: payload },
  );
  expect(initial.status()).toBe(201);
  const tradeId = (await initial.json()).trade.id;
  const retry = await request.post(
    `${root}/trade-position/purchases/external`,
    { data: payload },
  );
  expect((await retry.json()).trade.id).toBe(tradeId);
  const duplicate = await request.post(
    `${root}/trade-position/purchases/external`,
    { data: { ...payload, request_id: randomUUID() } },
  );
  expect(duplicate.status()).toBe(409);
  expect((await duplicate.json()).code).toBe("OPEN_TRADE_EXISTS");
  await page.goto(`/trade-management?trade_id=${tradeId}`);
  await expect(
    page.getByRole("heading", { name: "Nachkauf erfassen" }),
  ).toBeVisible();
  await page.getByLabel("Nachkaufmenge").fill("5");
  await page.getByLabel("Nachkaufpreis").fill("0.5");
  await page.getByLabel("Nachkaufdatum", { exact: true }).fill("2026-08-18");
  await page.getByRole("button", { name: "Nachkauf speichern" }).click();
  await expect(
    page.getByText("Nachkauf beim bestehenden Trade erfasst."),
  ).toBeVisible();
  const position = await (
    await request.get(`${root}/trade-position/trades/${tradeId}/position`)
  ).json();
  expect(position.open_quantity).toBe(15);
  expect(position.opened_on).toBe("2026-08-17");
  await expect(page.getByLabel("Verkaufsdatum", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Stornierung prüfen" }).click();
  const confirm = page.getByRole("button", {
    name: "Fehleingabe verbindlich stornieren",
  });
  await expect(confirm).toBeDisabled();
  await page.getByLabel("Stornogrund").fill("Browser test entry mistake");
  await page
    .getByRole("checkbox", { name: /genau dieser Trade eine Fehleingabe/ })
    .check();
  await confirm.click();
  await expect(page.getByText(/STORNIERT am/)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Nachkauf erfassen" }),
  ).toHaveCount(0);
  const timeline = await (
    await request.get(`${root}/trade-position/trades/${tradeId}/timeline`)
  ).json();
  expect(
    timeline.filter((r: { kind: string }) => r.kind === "CANCELLATION"),
  ).toHaveLength(1);
  expect(
    timeline.filter(
      (r: { execution_side: string }) => r.execution_side === "SELL",
    ),
  ).toHaveLength(0);
  const workspace = await (
    await request.get(`${root}/operational-workspace/positions`)
  ).json();
  expect(
    workspace.positions.some(
      (p: { trade_id: string }) => p.trade_id === tradeId,
    ),
  ).toBe(false);
  // The old retry must not resurrect a cancelled trade; an explicit NEW request can open one.
  expect(
    (
      await request.post(`${root}/trade-position/purchases/external`, {
        data: payload,
      })
    ).status(),
  ).toBe(409);
  expect(
    (
      await request.post(`${root}/trade-position/purchases/external`, {
        data: { ...payload, request_id: randomUUID() },
      })
    ).status(),
  ).toBe(201);
});
