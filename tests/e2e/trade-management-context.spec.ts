import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080", timezoneId: "Europe/Berlin" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "This regression writes synthetic executions only in the disposable CI database",
);

test("failed trade switch cannot reuse another position; retry and history preserve exact booking context", async ({
  page,
  request,
}) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const marker = randomUUID();
  const issuerResponse = await request.post(
    `${root}/market-reference-data/issuers`,
    {
      data: {
        legal_name: `Context regression ${marker}`,
        display_name: "Synthetic context issuer",
      },
    },
  );
  expect(issuerResponse.status()).toBe(201);
  const issuer = await issuerResponse.json();
  const venues = await (
    await request.get(`${root}/market-reference-data/trading-venues`)
  ).json();
  const underlyingResponse = await request.post(`${root}/underlyings`, {
    data: {
      name: `Synthetic context stock ${marker}`,
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.items.find(
          (venue: { mic: string }) => venue.mic === "XETR",
        ).id,
        ticker: `C${marker.slice(0, 8)}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlyingResponse.status()).toBe(201);
  const underlying = await underlyingResponse.json();

  // Real owner APIs create two different synthetic warrants on the same underlying.
  // Neither test identity nor any response is derived from the user's holdings.
  async function capture(label: string, quantity: number) {
    const warrantResponse = await request.post(`${root}/warrants`, {
      data: {
        issuer_id: issuer.id,
        underlying_id: underlying.id,
        display_name: `Synthetic context warrant ${label} ${marker}`,
        option_direction: "CALL",
        strike: "100",
        strike_currency_code: "EUR",
        maturity_date: "2099-12-31",
        ratio: "0.1",
      },
    });
    expect(warrantResponse.status()).toBe(201);
    const warrant = await warrantResponse.json();
    const buy = await request.post(
      `${root}/trade-position/purchases/external`,
      {
        data: {
          product_id: warrant.id,
          quantity,
          price_per_unit: "2.00",
          executed_on: "2026-08-17",
          execution_timezone: "Europe/Berlin",
          request_id: randomUUID(),
        },
      },
    );
    expect(buy.status()).toBe(201);
    return { warrant, ...(await buy.json()) };
  }
  const a = await capture("A", 10);
  const b = await capture("B", 20);
  const aUrl = `${root}/trade-position/trades/${a.trade.id}`;
  const bUrl = `${root}/trade-position/trades/${b.trade.id}`;
  const originalAHistory = await (await request.get(`${aUrl}/timeline`)).json();

  const writes: Array<{ path: string; data: unknown }> = [];
  page.on("request", (req) => {
    if (
      req.method() !== "GET" &&
      new URL(req.url()).pathname.includes("/trade-position/")
    ) {
      writes.push({
        path: new URL(req.url()).pathname,
        data: req.postDataJSON(),
      });
    }
  });
  let blockB = true;
  // Only one read is deliberately failed; all trades, writes and verification
  // go through the real backend and disposable PostgreSQL database.
  await page.route(
    `**/api/api/v1/trade-position/trades/${b.trade.id}/position`,
    (route) =>
      blockB
        ? route.fulfill({
            status: 503,
            contentType: "application/json",
            body: JSON.stringify({
              code: "SYNTHETIC_POSITION_READ_FAILURE",
              message: "Test: Position B nicht verfügbar.",
              details: [],
              timestamp: "2026-08-20T09:00:00Z",
            }),
          })
        : route.continue(),
  );

  await page.goto(`/trade-management?trade_id=${a.trade.id}`);
  await expect(
    page.getByRole("heading", { name: new RegExp(a.warrant.display_name) }),
  ).toBeVisible();
  await page.getByLabel("Verkaufsmenge", { exact: true }).fill("3");
  await page.getByLabel("Verkaufspreis", { exact: true }).fill("2.50");
  await page
    .getByLabel("Neue Management-Notiz", { exact: true })
    .fill("Draft belongs to A");
  await page.getByLabel("Trade-ID", { exact: true }).fill(b.trade.id);
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  // The separate product-valuation panel may report the same failed read.
  // Assert the management page's status, not a duplicate text anywhere on the page.
  await expect(
    page.getByRole("status").filter({ hasText: "Test: Position B nicht verfügbar." }),
  ).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`trade_id=${b.trade.id}$`));
  await expect(
    page.getByRole("heading", { name: new RegExp(a.warrant.display_name) }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("form", { name: "Verkauf erfassen", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Stop speichern", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Kauf- und Verkaufsdaten" }),
  ).toHaveCount(0);
  expect(writes).toEqual([]);

  blockB = false;
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: new RegExp(b.warrant.display_name) }),
  ).toBeVisible();
  await expect(page.getByLabel("Verkaufsmenge", { exact: true })).toHaveValue(
    "",
  );
  await expect(page.getByLabel("Verkaufspreis", { exact: true })).toHaveValue(
    "",
  );
  await expect(
    page.getByLabel("Neue Management-Notiz", { exact: true }),
  ).toHaveValue("");
  expect(writes).toEqual([]);

  // Deliberate new inputs on the correctly identified B: never replay A's draft.
  await page.getByLabel("Verkaufsmenge", { exact: true }).fill("2");
  await page.getByLabel("Verkaufspreis", { exact: true }).fill("3.25");
  await page.getByLabel("Verkaufsdatum", { exact: true }).fill("2026-08-20");
  await page
    .getByRole("button", { name: "Teilverkauf erfassen", exact: true })
    .click();
  await expect(
    page.getByText(
      "Teilverkauf wurde erfasst und die Position neu projiziert.",
      { exact: true },
    ),
  ).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0]).toEqual({
    path: `/api/api/v1/trade-position/trades/${b.trade.id}/sales`,
    data: {
      quantity: 2,
      price_per_unit: "3.25",
      executed_on: "2026-08-20",
      execution_timezone: "Europe/Berlin",
      request_id: expect.any(String),
    },
  });
  const remainingB = await (await request.get(`${bUrl}/position`)).json();
  expect(remainingB.trade_id).toBe(b.trade.id);
  expect(remainingB.product_id).toBe(b.warrant.id);
  expect(remainingB.open_quantity).toBe(18);
  expect(Number(remainingB.realized_gross_pnl)).toBe(2.5);
  expect(await (await request.get(`${aUrl}/position`)).json()).toEqual(
    a.position,
  );
  expect(await (await request.get(`${aUrl}/timeline`)).json()).toEqual(
    originalAHistory,
  );

  // Query-only history navigation must load the actual URL trade, not stale local state.
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: new RegExp(a.warrant.display_name) }),
  ).toBeVisible();
  await expect(page.getByText("10 offen", { exact: true })).toBeVisible();
  await page.goForward();
  await expect(
    page.getByRole("heading", { name: new RegExp(b.warrant.display_name) }),
  ).toBeVisible();
  await expect(page.getByText("18 offen", { exact: true })).toBeVisible();
  expect(writes).toHaveLength(1);
});
