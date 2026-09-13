import { randomUUID } from "node:crypto";
import { expect, test, type Request } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080", timezoneId: "Europe/Berlin" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Requires an explicitly disposable test stack",
);

test("ambiguous purchase and sale times write nothing; explicit date-only capture remains available", async ({
  page,
  request,
}) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `DST capture ${randomUUID()}`,
      display_name: "Synthetic DST browser test",
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
      name: "Synthetic DST stock",
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.find((v: { mic: string }) => v.mic === "XETR")
          .id,
        ticker: `DST${randomUUID().slice(0, 8)}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: (await issuer.json()).id,
      underlying_id: (await underlying.json()).id,
      display_name: "Synthetic DST warrant",
      option_direction: "CALL",
      strike: "500",
      strike_currency_code: "USD",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  const initial = await request.post(
    `${root}/trade-position/purchases/external`,
    {
      data: {
        product_id: (await warrant.json()).id,
        quantity: 10,
        price_per_unit: "0.55",
        executed_on: "2025-10-25",
        execution_timezone: "Europe/Berlin",
        request_id: randomUUID(),
      },
    },
  );
  expect(initial.status()).toBe(201);
  const original = await initial.json();
  const tradeId = original.trade.id;
  const tradeUrl = `${root}/trade-position/trades/${tradeId}`;
  const executions = async () => {
    const response = await request.get(`${tradeUrl}/timeline`);
    expect(response.status()).toBe(200);
    return (await response.json()).filter(
      (row: { kind: string }) => row.kind === "EXECUTION",
    );
  };
  const originalExecutions = await executions();
  const captures: Request[] = [];
  page.on("request", (outgoing) => {
    if (
      outgoing.method() === "POST" &&
      outgoing.url().includes("/trade-position/")
    ) captures.push(outgoing);
  });
  await page.goto(`/trade-management?trade_id=${tradeId}`);
  await page.getByLabel("Nachkaufmenge").fill("5");
  await page.getByLabel("Nachkaufpreis").fill("0.5");
  await page.getByLabel("Nachkaufdatum", { exact: true }).fill("2025-10-26");
  await page.getByLabel("Nachkaufdatum Uhrzeit", { exact: true }).fill("02:30");
  await page.getByRole("button", { name: "Nachkauf speichern" }).click();
  await expect(page.getByText(/Die Uhrzeit ist wegen der Zeitumstellung/)).toBeVisible();
  expect(captures).toHaveLength(0);
  expect(await executions()).toEqual(originalExecutions);
  expect((await (await request.get(`${tradeUrl}/position`)).json()).open_quantity).toBe(10);
  await expect(page.getByLabel("Nachkaufmenge")).toHaveValue("5");
  await expect(page.getByLabel("Nachkaufdatum Uhrzeit", { exact: true })).toHaveValue("02:30");

  // Explicit user choice, never an automatic fallback after the rejected time.
  await page.getByLabel("Nachkaufdatum Uhrzeit", { exact: true }).fill("");
  await page.getByRole("button", { name: "Nachkauf speichern" }).click();
  await expect(page.getByText("Nachkauf beim bestehenden Trade erfasst.")).toBeVisible();
  expect(captures).toHaveLength(1);
  expect(captures[0].postDataJSON()).toMatchObject({
    quantity: 5,
    price_per_unit: "0.5",
    executed_on: "2025-10-26",
    execution_timezone: "Europe/Berlin",
  });
  expect(captures[0].postDataJSON()).not.toHaveProperty("executed_at");
  const afterPurchase = await executions();
  expect(afterPurchase).toHaveLength(2);
  expect(afterPurchase.find((row: { id: string }) => row.id === original.execution.id)).toEqual(
    originalExecutions[0],
  );
  expect((await (await request.get(`${tradeUrl}/position`)).json()).open_quantity).toBe(15);

  await page.getByLabel("Verkaufspreis", { exact: true }).fill("0.9");
  await page.getByLabel("Verkaufsdatum", { exact: true }).fill("2025-10-26");
  await page.getByLabel("Verkaufsdatum Uhrzeit", { exact: true }).fill("02:30");
  await page.getByRole("button", { name: "Position vollständig schließen" }).click();
  await expect(page.getByText(/Die Uhrzeit ist wegen der Zeitumstellung/)).toBeVisible();
  expect(captures).toHaveLength(1);
  expect(await executions()).toEqual(afterPurchase);
  expect((await (await request.get(`${tradeUrl}/position`)).json()).open_quantity).toBe(15);
  await expect(page.getByLabel("Verkaufsdatum Uhrzeit", { exact: true })).toHaveValue("02:30");

  await page.getByLabel("Verkaufsdatum Uhrzeit", { exact: true }).fill("");
  await page.getByRole("button", { name: "Position vollständig schließen" }).click();
  await expect(page.getByRole("heading", { name: "CLOSED", exact: true })).toBeVisible();
  expect(captures).toHaveLength(2);
  expect(captures[1].postDataJSON()).toMatchObject({
    quantity: 15,
    executed_on: "2025-10-26",
    execution_timezone: "Europe/Berlin",
  });
  expect(captures[1].postDataJSON()).not.toHaveProperty("executed_at");
  const closed = await (await request.get(`${tradeUrl}/position`)).json();
  expect(closed.open_quantity).toBe(0);
  expect(closed.closed_on).toBe("2025-10-26");
  expect(closed.is_closed).toBe(true);
  const history = await executions();
  expect(history).toHaveLength(3);
  const sale = history.find((row: { execution_side: string }) => row.execution_side === "SELL");
  expect(sale.executed_on).toBe("2025-10-26");
  expect(sale.execution_timezone).toBe("Europe/Berlin");
});
