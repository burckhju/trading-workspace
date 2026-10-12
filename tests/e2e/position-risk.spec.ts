import { randomUUID } from "node:crypto";
import { expect, test, type Locator, type Page } from "@playwright/test";

async function expectUsableWidth(page: Page, panel: Locator) {
  const layout = await panel.evaluate((element) => {
    const ancestors = [];
    for (
      let node: HTMLElement | null = element as HTMLElement;
      node;
      node = node.parentElement
    ) {
      const style = getComputedStyle(node);
      ancestors.push({
        tag: node.tagName,
        classes: node.className,
        width: node.getBoundingClientRect().width,
        display: style.display,
        flex: style.flex,
        alignItems: style.alignItems,
      });
    }
    return { width: element.getBoundingClientRect().width, ancestors };
  });
  expect(layout.width, JSON.stringify(layout)).toBeGreaterThanOrEqual(
    Math.min(page.viewportSize()!.width, 1600) - 64,
  );
}

async function expectStackedPanels(
  page: Page,
  risk: Locator,
  valuation: Locator,
) {
  await expectUsableWidth(page, risk);
  await expectUsableWidth(page, valuation);
  const riskBounds = await risk.boundingBox();
  const valuationBounds = await valuation.boundingBox();
  expect(valuationBounds!.y).toBeGreaterThanOrEqual(
    riskBounds!.y + riskBounds!.height,
  );
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
}

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
  expect(preview.iv.status).toBe("NOT_EVALUABLE");
  expect(preview.iv.current_iv_decimal).toBeNull();
  expect(preview.iv.percentile).toBeNull();
  expect(preview.iv.risk_level).toBeNull();
  await page.goto(`/trade-management?trade_id=${captured.trade.id}`);
  const panel = page.getByRole("region", { name: "Risiko- und Trendsignale" });
  const summary = panel.getByRole("region", { name: "Risikoübersicht" });
  const valuation = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Produktbewertung", exact: true }),
  });
  await expect(summary.getByText("Deaktiviert", { exact: true })).toBeVisible();
  await expect(
    summary.getByText("Nicht auswertbar", { exact: true }),
  ).toHaveCount(2);
  await testInfo.attach("risk-overview-desktop", {
    body: await panel.screenshot(),
    contentType: "image/png",
  });
  await expectStackedPanels(page, panel, valuation);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(summary).toBeVisible();
  await testInfo.attach("risk-overview-mobile", {
    body: await panel.screenshot(),
    contentType: "image/png",
  });
  await expectStackedPanels(page, panel, valuation);
  await panel
    .getByText("Kennzahlen, Kursqualität und Quellen im Detail")
    .click();
  await expect(panel).toContainText(
    "Mindestens 21 abgeschlossene bereinigte Tageskurse erforderlich",
  );
  await expect(panel).toContainText("Echte Optionsschein-Kurshistorie fehlt");
  await expectStackedPanels(page, panel, valuation);
  for (const width of [320, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await expectStackedPanels(page, panel, valuation);
    await testInfo.attach(`risk-details-${width}`, {
      body: await panel.screenshot(),
      contentType: "image/png",
    });
  }
  const iv = panel.getByRole("region", {
    name: "Implizite Volatilität",
    exact: true,
  });
  await expect(iv.getByText("Nicht verfügbar", { exact: true })).toHaveCount(6);
  await iv.getByText("Warum IV-Kennzahlen fehlen · Daten und Grenzen").click();
  await expect(iv).toContainText(
    "Ein Basiswertkurs mit passendem Originalzeitpunkt fehlt",
  );
  await iv.getByText("Modelllabor: IV-Szenario mit eigenen Annahmen").click();
  await iv.getByRole("button", { name: "Beispielannahmen laden" }).click();
  await iv
    .getByLabel("Modellgeltung ausdrücklich wählen")
    .selectOption("EUROPEAN");
  await iv
    .getByRole("button", { name: "Annahmen berechnen", exact: true })
    .click();
  await expect(
    iv.getByRole("region", { name: "Hypothetisches IV-Ergebnis" }),
  ).toBeVisible();
  await expect(iv).toContainText("kein Verkaufserlös");
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expectStackedPanels(page, panel, valuation);
    await testInfo.attach(`iv-model-${width}`, {
      body: await iv.screenshot(),
      contentType: "image/png",
    });
  }
  await iv.getByLabel("IV-Änderung (Prozentpunkte)").fill("-10");
  await expect(
    iv.getByRole("region", { name: "Hypothetisches IV-Ergebnis" }),
  ).toHaveCount(0);
  await iv
    .getByRole("button", { name: "Annahmen berechnen", exact: true })
    .click();
  await expect(iv).toContainText("lineare Näherung ausgesetzt");
  expect(await (await request.get(positionUrl)).json()).toEqual(original);
  await page.setViewportSize({ width: 390, height: 844 });
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
