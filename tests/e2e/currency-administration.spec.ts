import { expect, test } from "@playwright/test";

// Use the same origin as the CI bundle's API base URL, without weakening browser CORS.
test.use({ baseURL: "http://localhost:8080" });
test.skip(
  process.env.CURRENCY_E2E_WRITES_ALLOWED !== "1",
  "Requires an explicitly disposable test stack",
);

// Real isolated CI stack: no intercepted API and no external reference/FX request.
test("imports bundled catalog explicitly, enables JPY and uses it in warrant terms", async ({
  page,
  request,
}) => {
  await page.goto("/currencies-admin");
  await expect(
    page.getByRole("heading", { name: "Währungen", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Mitgelieferten Katalog prüfen" })
    .click();
  const apply = page.getByRole("button", { name: "Katalog übernehmen" });
  // Retries can run against an already imported test catalog.
  await expect(
    page.getByRole("heading", { name: /Änderungsvorschau/ }),
  ).toBeVisible();
  if (await apply.count()) {
    await expect(apply).toBeDisabled();
    await page.getByLabel(/Ich habe Quelle und Änderungen geprüft/).check();
    await apply.click();
    await expect(
      page.getByText(/Katalog übernommen. Keine Währung/),
    ).toBeVisible();
  }
  await page.getByLabel("Währung suchen").fill("JPY");
  const activate = page.getByRole("button", {
    name: "JPY aktivieren",
    exact: true,
  });
  if (await activate.count()) {
    await activate.click();
    await page.getByRole("button", { name: "Freigabe bestätigen" }).click();
    await expect(page.getByText(/JPY wurde aktiviert/)).toBeVisible();
  }
  const root = "http://127.0.0.1:8000/api/v1";
  const references = await request.get(
    `${root}/market-reference-data/currencies`,
  );
  expect(references.ok()).toBeTruthy();
  const refBody = (await references.json()) as {
    items: { code: string; minor_unit: number }[];
  };
  expect(refBody.items.find((item) => item.code === "JPY")?.minor_unit).toBe(0);
  const issuer = await request.post(`${root}/market-reference-data/issuers`, {
    data: {
      legal_name: `Currency browser ${Date.now()}`,
      display_name: "Currency browser",
    },
  });
  expect(issuer.status()).toBe(201);
  const issuerBody = (await issuer.json()) as { id: string };
  const venues = await request.get(
    `${root}/market-reference-data/trading-venues`,
  );
  const venueBody = (await venues.json()) as {
    items: { id: string; mic: string }[];
  };
  const underlying = await request.post(`${root}/underlyings`, {
    data: {
      name: "Currency browser stock",
      type: "STOCK",
      primary_listing: {
        trading_venue_id: venueBody.items.find((v) => v.mic === "XETR")?.id,
        ticker: `FX${Date.now()}`,
        currency_code: "EUR",
      },
    },
  });
  expect(underlying.status()).toBe(201);
  const underlyingBody = (await underlying.json()) as { id: string };
  const warrant = await request.post(`${root}/warrants`, {
    data: {
      issuer_id: issuerBody.id,
      underlying_id: underlyingBody.id,
      display_name: "JPY currency browser call",
      option_direction: "CALL",
      strike: "500",
      strike_currency_code: "JPY",
      maturity_date: "2099-12-31",
      ratio: "0.1",
    },
  });
  expect(warrant.status()).toBe(201);
  const warrantBody = (await warrant.json()) as { id: string };
  const history = await request.get(`${root}/warrants/${warrantBody.id}/terms`);
  const historyBody = (await history.json()) as {
    strike_currency_code: string;
  }[];
  expect(historyBody[0].strike_currency_code).toBe("JPY");
  await page
    .getByRole("button", { name: "JPY deaktivieren", exact: true })
    .click();
  await page.getByRole("button", { name: "Freigabe bestätigen" }).click();
  await expect(page.getByText(/JPY wurde deaktiviert/)).toBeVisible();
  expect(
    await (
      await request.get(`${root}/warrants/${warrantBody.id}/terms`)
    ).json(),
  ).toEqual(historyBody);
});
