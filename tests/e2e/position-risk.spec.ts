import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Synthetic positions only in disposable CI database",
);

test("qualified risk preview, explicit activation and immutable evaluation preserve the position", async ({
  page,
  request,
}, testInfo) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const marker = randomUUID();
  const issuerResponse = await request.post(
    `${root}/market-reference-data/issuers`,
    {
      data: {
        legal_name: `Risk test ${marker}`,
        display_name: "Synthetic risk issuer",
      },
    },
  );
  expect(issuerResponse.status()).toBe(201);
  const issuer = await issuerResponse.json();
  const venues = await (
    await request.get(`${root}/market-reference-data/trading-venues`)
  ).json();
  const stockResponse = await request.post(`${root}/underlyings`, {
    data: {
      name: `Synthetic risk ${marker}`,
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venues.items.find(
          (v: { mic: string }) => v.mic === "XETR",
        ).id,
        ticker: `R${marker.slice(0, 8)}`,
        currency_code: "EUR",
      },
    },
  });
  expect(stockResponse.status()).toBe(201);
  const stock = await stockResponse.json();
  const productResponse = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: issuer.id,
      underlying_id: stock.id,
      display_name: `Synthetic risk call ${marker}`,
      option_direction: "CALL",
      strike: "100",
      strike_currency_code: "EUR",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(productResponse.status()).toBe(201);
  const product = await productResponse.json();
  const buy = await request.post(`${root}/trade-position/purchases/external`, {
    data: {
      product_id: product.id,
      quantity: 10,
      price_per_unit: "2.00",
      executed_on: "2026-08-17",
      execution_timezone: "Europe/Berlin",
      request_id: randomUUID(),
    },
  });
  expect(buy.status()).toBe(201);
  const captured = await buy.json();
  const riskUrl = `${root}/position-monitoring/trades/${captured.trade.id}/risk`;
  const positionUrl = `${root}/trade-position/trades/${captured.trade.id}/position`;
  const original = await (await request.get(positionUrl)).json();
  const preview = await (await request.get(riskUrl)).json();
  expect(preview.configuration.enabled).toBe(false);
  expect(preview.snapshot_id).toBeNull();
  expect(preview.comparison.reasons).toContain("PRODUCT_HISTORY_NOT_AVAILABLE");
  await page.goto(`/trade-management?trade_id=${captured.trade.id}`);
  const panel = page.getByRole("region", { name: "Risiko- und Trendsignale" });
  const summary = panel.getByRole("region", { name: "Risikoübersicht" });
  await expect(summary.getByText("Deaktiviert", { exact: true })).toBeVisible();
  await expect(
    summary.getByText("Nicht auswertbar", { exact: true }),
  ).toHaveCount(2);
  await testInfo.attach("risk-overview-desktop", {
    body: await panel.screenshot(),
    contentType: "image/png",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(summary).toBeVisible();
  await testInfo.attach("risk-overview-mobile", {
    body: await panel.screenshot(),
    contentType: "image/png",
  });
  const overflow = await page.evaluate(() => ({
    pageWidth: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    elements: [...document.querySelectorAll("body *")]
      .filter(
        (element) =>
          element.getBoundingClientRect().right > window.innerWidth + 1,
      )
      .map((element) => ({ tag: element.tagName, classes: element.className }))
      .slice(0, 12),
  }));
  expect(overflow.pageWidth, JSON.stringify(overflow)).toBeLessThanOrEqual(
    overflow.viewport,
  );
  await panel
    .getByText("Kennzahlen, Kursqualität und Quellen im Detail")
    .click();
  await expect(panel).toContainText(
    "Mindestens 21 abgeschlossene bereinigte Tageskurse erforderlich",
  );
  await expect(panel).toContainText("Echte Optionsschein-Kurshistorie fehlt");
  const activate = panel.getByRole("button", {
    name: "Warnregeln für diese Position aktivieren",
  });
  await expect(activate).toBeDisabled();
  await panel.getByRole("checkbox").check();
  await activate.click();
  await expect(panel).toContainText("Revision 1 · Warnregeln aktiv");
  await panel
    .getByRole("button", {
      name: "Aktuelle Konfiguration auswerten und speichern",
    })
    .click();
  await panel
    .getByRole("button", { name: "Letzte 20 Auswertungen anzeigen" })
    .click();
  const history = await (await request.get(`${riskUrl}/history`)).json();
  expect(history).toHaveLength(1);
  expect(history[0].metrics.status).toBe("NOT_EVALUABLE");
  expect(history[0].execution_usable).toBe(false);
  expect(await (await request.get(positionUrl)).json()).toEqual(original);
  const repeated = await (await request.post(`${riskUrl}/evaluations`)).json();
  expect(repeated.snapshot_id).toBe(history[0].snapshot_id);
});
