import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080", timezoneId: "Europe/Berlin" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Disposable test database required",
);

test("correct existing BUY and SELL dates through UI, preserving quantities and original history", async ({
  page,
  request,
}) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `Date test ${randomUUID()}`,
      display_name: "Date UI test",
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
      name: "Date correction stock",
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.find((v: { mic: string }) => v.mic === "XETR")
          .id,
        ticker: `D${randomUUID().slice(0, 8)}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: (await issuer.json()).id,
      underlying_id: (await underlying.json()).id,
      display_name: "Date correction warrant",
      option_direction: "CALL",
      strike: "500",
      strike_currency_code: "USD",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  // Seed an already-recorded execution. The date CORRECTION must go through the actual UI.
  const purchase = await request.post(
    `${root}/trade-position/purchases/external`,
    {
      data: {
        product_id: (await warrant.json()).id,
        quantity: 10,
        price_per_unit: "0.55",
        executed_at: "2026-08-17T08:30:01.123456Z",
        request_id: randomUUID(),
      },
    },
  );
  expect(purchase.status()).toBe(201);
  const original = await purchase.json();
  const tid = original.trade.id;
  const tradeUrl = `${root}/trade-position/trades/${tid}`;
  await page.goto(`/trade-management?trade_id=${tid}`);
  const panel = page.getByRole("region", { name: "Kauf- und Verkaufsdaten" });
  await panel.getByRole("button", { name: "Kaufdatum korrigieren" }).click();
  const form = panel.getByRole("form", {
    name: "Ausführungsdatum korrigieren",
  });
  await expect(
    form.getByLabel("Kaufdatum korrigieren", { exact: true }),
  ).toHaveValue("2026-08-17");
  await form
    .getByLabel("Kaufdatum korrigieren", { exact: true })
    .fill("2026-08-16");
  await expect(
    form.getByRole("checkbox", { name: /Bisherige Uhrzeit beibehalten/ }),
  ).toBeChecked();
  await form
    .getByRole("checkbox", {
      name: /Ich bestätige das tatsächliche Ausführungsdatum/,
    })
    .check();
  await form.getByRole("button", { name: "Datumsänderung speichern" }).click();
  await expect(panel.getByRole("status")).toHaveText(/Datum korrigiert/);
  const opened = await (await request.get(`${tradeUrl}/position`)).json();
  expect(opened.trade_id).toBe(tid);
  expect(opened.open_quantity).toBe(10);
  expect(opened.opened_at).toBe("2026-08-16T08:30:01.123456Z");
  expect(Number(opened.cost_basis)).toBe(5.5);

  // A NEW sale uses its entered date, not the capture date. Exercise the real sale form.
  await page.getByLabel("Verkaufspreis", { exact: true }).fill("0.9");
  await page.getByLabel("Verkaufsdatum", { exact: true }).fill("2026-08-22");
  await page
    .getByRole("button", { name: "Position vollständig schließen" })
    .click();
  await expect(
    page.getByRole("heading", { name: "CLOSED", exact: true }),
  ).toBeVisible();
  let closed = await (await request.get(`${tradeUrl}/position`)).json();
  expect(closed.closed_on).toBe("2026-08-22");
  expect(closed.is_closed).toBe(true);
  const before = await (await request.get(`${tradeUrl}/timeline`)).json();
  const initialSale = before.find(
    (row: { execution_side: string }) => row.execution_side === "SELL",
  );

  // A closed position must still offer correction of its historical sale date.
  await panel
    .getByRole("button", { name: "Verkaufsdatum korrigieren" })
    .click();
  await form
    .getByLabel("Verkaufsdatum korrigieren", { exact: true })
    .fill("2026-08-23");
  await form
    .getByRole("checkbox", {
      name: /Ich bestätige das tatsächliche Ausführungsdatum/,
    })
    .check();
  await form.getByRole("button", { name: "Datumsänderung speichern" }).click();
  await expect(panel.getByRole("status")).toHaveText(/Datum korrigiert/);
  closed = await (await request.get(`${tradeUrl}/position`)).json();
  expect(closed.closed_on).toBe("2026-08-23");
  expect(closed.open_quantity).toBe(0);
  expect(Number(closed.realized_gross_pnl)).toBe(3.5);
  const after = await (await request.get(`${tradeUrl}/timeline`)).json();
  const executions = after.filter(
    (row: { kind: string }) => row.kind === "EXECUTION",
  );
  expect(executions).toHaveLength(4);
  const oldBuy = executions.find(
    (row: { id: string }) => row.id === original.execution.id,
  );
  expect(oldBuy.recorded_at).toBe(original.execution.recorded_at);
  expect(oldBuy.occurred_at).toBe(original.execution.executed_at);
  expect(
    executions.find((row: { id: string }) => row.id === initialSale.id),
  ).toEqual(initialSale);
  expect(
    executions.filter(
      (row: { supersedes_id: string | null }) => row.supersedes_id,
    ),
  ).toHaveLength(2);
  await page.reload();
  await expect(panel.getByText(/Ausgeführt: 2026-08-23/)).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Verkaufsdatum korrigieren" }),
  ).toHaveCount(1);
});
