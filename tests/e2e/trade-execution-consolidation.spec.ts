import { randomUUID } from "node:crypto";
import { expect, test, type Page, type Route } from "@playwright/test";

import type {
  ExecutionCurrencyConfirmation,
  TradeTimelineEntryResponse,
} from "../../frontend/src/features/trade/types/api";

test.use({ timezoneId: "Europe/Berlin" });

const tradeId = "41000000-0000-4000-8000-000000000001";
const otherTradeId = "41000000-0000-4000-8000-000000000002";
const productId = "42000000-0000-4000-8000-000000000001";
const originalBuyId = "43000000-0000-4000-8000-000000000001";
const buyId = "43000000-0000-4000-8000-000000000002";
const sellId = "43000000-0000-4000-8000-000000000003";
const confirmationId = "44000000-0000-4000-8000-000000000001";
const now = "2026-08-25T13:14:15.123456Z";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function execution(
  overrides: Partial<TradeTimelineEntryResponse>,
): TradeTimelineEntryResponse {
  return {
    id: originalBuyId,
    trade_id: tradeId,
    kind: "EXECUTION",
    execution_side: "BUY",
    management_event_type: null,
    occurred_at: "2026-08-17T08:30:01.123456Z",
    recorded_at: now,
    executed_on: null,
    execution_timezone: null,
    quantity: 10,
    price_per_unit: "0.5500000000",
    numeric_value: null,
    text_value: null,
    supersedes_id: null,
    currency_confirmation: null,
    currency_resolution: {
      currency_code: "EUR",
      source: "REPLACED_EXECUTION",
      source_execution_ids: [originalBuyId],
      confirmation_ids: [confirmationId],
    },
    ...overrides,
  };
}

async function mockedBookings(page: Page) {
  const entries = [
    execution({ id: originalBuyId, currency_resolution: null }),
    execution({
      id: buyId,
      occurred_at: "2026-08-16T08:30:01.123456Z",
      supersedes_id: originalBuyId,
    }),
    execution({
      id: sellId,
      execution_side: "SELL",
      quantity: 4,
      price_per_unit: "0.9000000000",
      occurred_at: "2026-08-21T22:00:00Z",
      executed_on: "2026-08-22",
      execution_timezone: "Europe/Berlin",
      currency_resolution: {
        currency_code: "EUR",
        source: "PRIOR_BUYS",
        source_execution_ids: [buyId, originalBuyId],
        confirmation_ids: [confirmationId],
      },
    }),
    execution({
      id: "45000000-0000-4000-8000-000000000001",
      kind: "MANAGEMENT_EVENT",
      execution_side: null,
      management_event_type: "MANAGEMENT_NOTE",
      quantity: null,
      price_per_unit: null,
      text_value: "Immutable management source",
      currency_resolution: null,
    }),
  ];
  const writes: Array<{ path: string; body: Record<string, unknown> }> = [];
  let timelineReads = 0;
  await page.route(/\/api\/(?:api\/)?v1\/.*/, async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (req.method() !== "GET") {
      writes.push({ path, body: req.postDataJSON() });
      return json(
        route,
        {
          code: "UNEXPECTED_TEST_WRITE",
          message: "Unexpected synthetic write",
        },
        500,
      );
    }
    const id = path.includes(otherTradeId) ? otherTradeId : tradeId;
    if (path.endsWith(`/trade-position/trades/${id}`))
      return json(route, {
        id,
        product_id: productId,
        origin: "EXTERNAL",
        trade_plan_id: null,
        trade_plan_version_id: null,
        product_selection_id: null,
        product_evaluation_id: null,
        created_at: now,
        cancelled_at: null,
      });
    if (path.endsWith("/position"))
      return json(route, {
        id: "position",
        trade_id: id,
        product_id: productId,
        open_quantity: id === tradeId ? 6 : 20,
        cost_basis: "3.3000000000",
        average_entry_price: "0.5500000000",
        realized_gross_pnl: "1.4000000000",
        opened_at: "2026-08-16T08:30:01.123456Z",
        opened_on: null,
        closed_at: null,
        closed_on: null,
        last_execution_at: "2026-08-21T22:00:00Z",
        last_execution_on: "2026-08-22",
        is_closed: false,
      });
    if (path.endsWith("/management"))
      return json(route, {
        trade_id: id,
        stop_price: "0.40",
        target_price: "1.00",
        thesis: "Original thesis",
        stop_price_binding: null,
        target_price_binding: null,
        notes: [],
        last_event_at: null,
      });
    if (path.endsWith("/timeline")) {
      timelineReads += 1;
      return json(
        route,
        entries.map((entry) => ({ ...entry, trade_id: id })),
      );
    }
    if (path.endsWith("/currency-confirmations")) {
      const selected = path.includes(sellId) ? entries[2] : entries[1];
      return json(route, {
        current: null,
        history: [],
        currency_resolution: selected.currency_resolution,
      });
    }
    if (path.endsWith(`/warrants/${productId}`))
      return json(route, {
        id: productId,
        underlying_id: "underlying",
        issuer_id: "issuer",
        workspace_id: "workspace",
        display_name: "Synthetic UI4 warrant",
        product_family: "WARRANT",
        isin: "DE000TESTUI4",
        wkn: "UI4001",
        lifecycle_status: "ACTIVE",
        version: 1,
        created_at: now,
        updated_at: now,
      });
    if (path.includes("/alerts/trades/")) return json(route, []);
    return json(
      route,
      {
        code: "SYNTHETIC_UNAVAILABLE",
        message: "Synthetic read unavailable",
        details: [],
        timestamp: now,
      },
      503,
    );
  });
  return { writes, timelineReads: () => timelineReads };
}

test("one current list and one guarded inline editor replace history, including keyboard and narrow layout", async ({
  page,
}) => {
  const fixture = await mockedBookings(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/trade-management?trade_id=${tradeId}#execution-dates`);
  const panel = page.getByRole("region", { name: "Kauf- und Verkaufsdaten" });
  await expect(panel.getByRole("article")).toHaveCount(2);
  await expect(page.getByText("OPEN", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Offene Menge", { exact: true })).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Trade Timeline", exact: true }),
  ).toHaveCount(0);
  const initialReads = fixture.timelineReads();
  expect(initialReads).toBeGreaterThan(0);

  const buy = panel.getByRole("article", {
    name: `Buchung ${buyId}`,
    exact: true,
  });
  const sell = panel.getByRole("article", {
    name: `Buchung ${sellId}`,
    exact: true,
  });
  await buy
    .getByRole("button", { name: "Kauf korrigieren", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  const form = panel.getByRole("form", {
    name: "Buchung korrigieren",
  });
  await expect(form).toHaveCount(1);
  await expect(
    form.getByLabel("Kaufdatum korrigieren", { exact: true }),
  ).toHaveValue("2026-08-16");
  await expect(buy.getByText(/^Ausgeführt:/)).toHaveCount(0);
  await form
    .getByLabel("Kaufdatum korrigieren", { exact: true })
    .fill("2026-08-15");
  await sell
    .getByRole("button", { name: "Verkauf korrigieren", exact: true })
    .click();
  const dialog = page.getByRole("alertdialog", {
    name: "Ungespeicherte Änderungen",
  });
  await expect(
    dialog.getByRole("button", { name: "Hier bleiben" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(
    form.getByLabel("Kaufdatum korrigieren", { exact: true }),
  ).toHaveValue("2026-08-15");
  await panel.getByRole("tab", { name: "Historie", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Eingaben verwerfen und wechseln" })
    .click();
  await expect(form).toHaveCount(0);
  await expect(panel.getByRole("article")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Trade Timeline", exact: true }),
  ).toHaveCount(1);
  await expect(
    panel.getByText("Immutable management source", { exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText(originalBuyId, { exact: false }).first(),
  ).toBeVisible();
  await expect(
    panel.getByRole("button", { name: /^(Kauf|Verkauf) korrigieren$/ }),
  ).toHaveCount(0);
  expect(fixture.timelineReads()).toBe(initialReads);
  expect(fixture.writes).toEqual([]);
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await panel
    .getByRole("tab", { name: "Aktuelle Buchungen", exact: true })
    .click();
  await expect(panel.getByRole("article")).toHaveCount(2);
});

test("same-trade refresh preserves editor and management drafts; route and browser history require explicit discard", async ({
  page,
}) => {
  const fixture = await mockedBookings(page);
  await page.goto(`/trade-management?trade_id=${tradeId}`);
  const panel = page.getByRole("region", { name: "Kauf- und Verkaufsdaten" });
  await expect(panel.getByRole("article")).toHaveCount(2);
  await page.getByLabel("Stop", { exact: true }).fill("0.47");
  await panel
    .getByRole("button", { name: "Kauf korrigieren", exact: true })
    .click();
  const input = panel.getByLabel("Kaufdatum korrigieren", { exact: true });
  await input.fill("2026-08-15");
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  await expect(input).toHaveValue("2026-08-15");
  await expect(page.getByLabel("Stop", { exact: true })).toHaveValue("0.47");
  await page.getByLabel("Trade-ID", { exact: true }).fill(otherTradeId);
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  const dialog = page.getByRole("alertdialog", {
    name: "Ungespeicherte Änderungen",
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Hier bleiben" }).click();
  await expect(page).toHaveURL(new RegExp(`trade_id=${tradeId}$`));
  await expect(input).toHaveValue("2026-08-15");
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Eingaben verwerfen und wechseln" })
    .click();
  await expect(page).toHaveURL(new RegExp(`trade_id=${otherTradeId}$`));
  await expect(panel.getByRole("article")).toHaveCount(2);
  await expect(page.getByLabel("Stop", { exact: true })).toHaveValue("0.40");
  await panel
    .getByRole("button", { name: "Verkauf korrigieren", exact: true })
    .click();
  await panel
    .getByLabel("Verkaufsdatum korrigieren", { exact: true })
    .fill("2026-08-23");
  await page.goBack();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Hier bleiben" }).click();
  await expect(page).toHaveURL(new RegExp(`trade_id=${otherTradeId}$`));
  await expect(
    panel.getByLabel("Verkaufsdatum korrigieren", { exact: true }),
  ).toHaveValue("2026-08-23");
  expect(fixture.writes).toEqual([]);
});

test.describe("real PostgreSQL owner boundary", () => {
  test.use({ baseURL: "http://localhost:8080" });
  test.skip(
    process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
    "Only the existing disposable E2E database may receive these synthetic facts",
  );

  test("BUY and SELL date changes retain original facts and inherited currency, and a separate confirmation refreshes dependent rows", async ({
    page,
    request,
  }) => {
    const root = "http://127.0.0.1:8000/api/v1";
    const marker = randomUUID();
    const issuer = await request.post(`${root}/market-reference-data/issuers`, {
      data: {
        legal_name: `UI4 synthetic issuer ${marker}`,
        display_name: "UI4 synthetic issuer",
      },
    });
    expect(issuer.status()).toBe(201);
    const venues = await (
      await request.get(`${root}/market-reference-data/trading-venues`)
    ).json();
    const underlying = await request.post(`${root}/underlyings`, {
      data: {
        name: `UI4 synthetic underlying ${marker}`,
        type: "STOCK",
        primary_listing: {
          trading_venue_id: venues.items.find(
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
        display_name: `UI4 synthetic warrant ${marker}`,
        option_direction: "CALL",
        strike: "500",
        strike_currency_code: "USD",
        maturity_date: "2099-12-31",
        ratio: "0.1",
      },
    });
    expect(warrant.status()).toBe(201);
    const purchase = await request.post(
      `${root}/trade-position/purchases/external`,
      {
        data: {
          product_id: (await warrant.json()).id,
          quantity: 10,
          price_per_unit: "0.5500000000",
          executed_at: "2026-08-17T08:30:01.123456Z",
          request_id: randomUUID(),
          currency_confirmation: {
            currency_code: "EUR",
            source: "USER_CONFIRMED",
            note: "Synthetic original receipt",
          },
        },
      },
    );
    expect(purchase.status()).toBe(201);
    const original = await purchase.json();
    const url = `${root}/trade-position/trades/${original.trade.id}`;
    const sale = await request.post(`${url}/sales`, {
      data: {
        quantity: 4,
        price_per_unit: "0.9000000000",
        executed_on: "2026-08-22",
        execution_timezone: "Europe/Berlin",
        request_id: randomUUID(),
      },
    });
    expect(sale.status()).toBe(201);
    const initialSale = (await sale.json()).execution;
    async function history(): Promise<TradeTimelineEntryResponse[]> {
      const response = await request.get(`${url}/timeline`);
      expect(response.status()).toBe(200);
      return response.json();
    }
    const before = await history();
    const originalBuy = before.find(
      (entry) => entry.id === original.execution.id,
    )!;
    const originalSell = before.find((entry) => entry.id === initialSale.id)!;
    const writes: Array<{ path: string; body: Record<string, unknown> }> = [];
    // Observe actual browser traffic without routing, fulfilling or changing any API response.
    page.on("request", (req) => {
      if (req.method() === "POST" && req.url().includes("/trade-position/")) {
        writes.push({
          path: new URL(req.url()).pathname,
          body: req.postDataJSON(),
        });
      }
    });
    await page.goto(
      `/trade-management?trade_id=${original.trade.id}#execution-dates`,
    );
    const panel = page.getByRole("region", { name: "Kauf- und Verkaufsdaten" });
    await expect(panel.getByRole("article")).toHaveCount(2);
    await expect(
      panel.getByText(/EUR · aus vorherigen Käufen übernommen/),
    ).toBeVisible();
    await page.getByLabel("Stop", { exact: true }).fill("0.47");
    const form = panel.getByRole("form", {
      name: "Buchung korrigieren",
    });
    await panel
      .getByRole("button", { name: "Kauf korrigieren", exact: true })
      .click();
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
        name: /Ich bestätige die geänderten Buchungsdaten/,
      })
      .check();
    await form
      .getByRole("button", { name: "Korrektur speichern" })
      .click();
    await expect(panel.getByRole("status")).toContainText("Buchung korrigiert");
    await expect(page.getByLabel("Stop", { exact: true })).toHaveValue("0.47");
    expect(writes).toHaveLength(1);
    expect(writes[0].body).toEqual({
      side: "BUY",
      quantity: 10,
      price_per_unit: originalBuy.price_per_unit,
      executed_at: "2026-08-16T08:30:01.123456Z",
    });

    await panel
      .getByRole("button", { name: "Verkauf korrigieren", exact: true })
      .click();
    await expect(
      form.getByLabel("Verkaufsdatum korrigieren", { exact: true }),
    ).toHaveValue("2026-08-22");
    await form
      .getByLabel("Verkaufsdatum korrigieren", { exact: true })
      .fill("2026-08-23");
    await form
      .getByRole("checkbox", {
        name: /Ich bestätige die geänderten Buchungsdaten/,
      })
      .check();
    await form
      .getByRole("button", { name: "Korrektur speichern" })
      .click();
    await expect(panel.getByRole("status")).toContainText("Buchung korrigiert");
    expect(writes).toHaveLength(2);
    expect(writes[1].body).toEqual({
      side: "SELL",
      quantity: 4,
      price_per_unit: originalSell.price_per_unit,
      executed_on: "2026-08-23",
      execution_timezone: "Europe/Berlin",
    });
    const corrected = await history();
    const correctedBuy = corrected.find(
      (entry) => entry.supersedes_id === originalBuy.id,
    )!;
    const correctedSell = corrected.find(
      (entry) => entry.supersedes_id === originalSell.id,
    )!;
    expect(corrected).toHaveLength(4);
    for (const source of [originalBuy, originalSell]) {
      expect(corrected.find((entry) => entry.id === source.id)).toMatchObject({
        id: source.id,
        recorded_at: source.recorded_at,
        occurred_at: source.occurred_at,
        quantity: source.quantity,
        price_per_unit: source.price_per_unit,
        executed_on: source.executed_on,
        execution_timezone: source.execution_timezone,
      });
    }
    expect(correctedBuy.currency_confirmation).toBeNull();
    expect(correctedBuy.currency_resolution).toMatchObject({
      currency_code: "EUR",
      source: "REPLACED_EXECUTION",
      source_execution_ids: [originalBuy.id],
      confirmation_ids: [original.execution.currency_confirmation.id],
    });
    expect(correctedSell.currency_confirmation).toBeNull();
    expect(correctedSell.currency_resolution).toMatchObject({
      currency_code: "EUR",
      source: "PRIOR_BUYS",
    });
    expect(correctedSell.executed_on).toBe("2026-08-23");
    const position = await (await request.get(`${url}/position`)).json();
    expect(position).toMatchObject({
      trade_id: original.trade.id,
      open_quantity: 6,
      is_closed: false,
      opened_at: "2026-08-16T08:30:01.123456Z",
      last_execution_on: "2026-08-23",
    });
    expect(Number(position.cost_basis)).toBe(3.3);
    expect(Number(position.average_entry_price)).toBe(0.55);
    expect(Number(position.realized_gross_pnl)).toBe(1.4);
    await expect(panel.getByRole("article")).toHaveCount(2);
    await expect(panel.getByText(/Ausgeführt: 2026-08-23/)).toContainText(
      "Uhrzeit unbekannt",
    );

    const buyRow = panel.getByRole("article", {
      name: `Buchung ${correctedBuy.id}`,
      exact: true,
    });
    await buyRow.getByRole("button", { name: /Währung/ }).click();
    await buyRow
      .getByRole("button", { name: "Abweichende Währung angeben", exact: true })
      .click();
    const currencyForm = buyRow.getByRole("form", {
      name: "Ausführungswährung bestätigen",
    });
    await expect(
      currencyForm.getByLabel("Ausführungswährung (Code)"),
    ).toHaveValue("");
    await expect(
      currencyForm.getByLabel("Beleg / Erläuterung (optional)"),
    ).toHaveValue("");
    await currencyForm.getByLabel("Ausführungswährung (Code)").fill("USD");
    await currencyForm
      .getByRole("button", {
        name: "Währungsbestätigung speichern",
        exact: true,
      })
      .click();
    await expect(buyRow.getByRole("status")).toContainText("Währung bestätigt");
    expect(writes).toHaveLength(3);
    expect(writes[2].path).toContain(
      `/executions/${correctedBuy.id}/currency-confirmations`,
    );
    expect(writes[2].body).toEqual({
      currency_code: "USD",
      source: "USER_CONFIRMED",
      note: null,
      supersedes_confirmation_id: null,
      request_id: expect.any(String),
    });
    const confirmed = await history();
    expect(confirmed).toHaveLength(4);
    const changedBuy = confirmed.find((entry) => entry.id === correctedBuy.id)!;
    const changedSell = confirmed.find(
      (entry) => entry.id === correctedSell.id,
    )!;
    const ownConfirmation =
      changedBuy.currency_confirmation as ExecutionCurrencyConfirmation;
    expect(ownConfirmation).toMatchObject({
      execution_id: correctedBuy.id,
      currency_code: "USD",
      supersedes_confirmation_id: null,
    });
    expect(changedSell.currency_confirmation).toBeNull();
    expect(changedSell.currency_resolution).toEqual({
      currency_code: "USD",
      source: "PRIOR_BUYS",
      source_execution_ids: [correctedBuy.id],
      confirmation_ids: [ownConfirmation.id],
      evidence_ids: [],
      evidence: [],
      reason: null,
      resolver_version: "execution-currency-v3",
    });
    await expect(
      panel.getByRole("article", {
        name: `Buchung ${correctedSell.id}`,
        exact: true,
      }),
    ).toContainText("USD · aus vorherigen Käufen übernommen");
    expect(await (await request.get(`${url}/position`)).json()).toEqual(
      position,
    );
    await expect(page.getByLabel("Stop", { exact: true })).toHaveValue("0.47");
    await panel.getByRole("tab", { name: "Historie", exact: true }).click();
    await expect(panel.getByRole("article")).toHaveCount(0);
    await expect(
      panel.getByRole("heading", { name: "Trade Timeline", exact: true }),
    ).toBeVisible();
    for (const source of [
      originalBuy,
      originalSell,
      correctedBuy,
      correctedSell,
    ]) {
      await expect(
        panel.getByText(source.id, { exact: false }).first(),
      ).toBeVisible();
    }
    await expect(
      panel.getByRole("button", { name: /^(Kauf|Verkauf) korrigieren$/ }),
    ).toHaveCount(0);
    expect(writes).toHaveLength(3);
  });
});
