import { randomUUID } from "node:crypto";
import { expect, test, type APIResponse } from "@playwright/test";

test.use({ baseURL: "http://localhost:8080" });
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Disposable CI database only",
);
async function body(response: APIResponse) {
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}
function syntheticIsin() {
  const prefix = `DE${(BigInt(`0x${randomUUID().replaceAll("-", "")}`) % 1000000000n).toString().padStart(9, "0")}`;
  for (let check = 0; check < 10; check++) {
    const candidate = prefix + check;
    const digits = [...candidate]
      .map((c) => (/[A-Z]/.test(c) ? String(c.charCodeAt(0) - 55) : c))
      .join("");
    const sum = [...digits].reverse().reduce((s, c, i) => {
      const n = Number(c) * (i % 2 ? 2 : 1);
      return s + (n > 9 ? n - 9 : n);
    }, 0);
    if (sum % 10 === 0) return candidate;
  }
  throw new Error("ISIN fixture checksum");
}

test("document revision and empty observation journal remain explicit at mobile and desktop widths", async ({
  page,
  request,
}, testInfo) => {
  const root = "http://127.0.0.1:8000/api/v1";
  const token = randomUUID();
  const issuer = await body(
    await request.post(`${root}/market-reference-data/issuers`, {
      data: {
        legal_name: `IV evidence ${token}`,
        display_name: "Synthetic IV evidence",
      },
    }),
  );
  const venues = await (
    await request.get(`${root}/market-reference-data/trading-venues`)
  ).json();
  const underlying = await body(
    await request.post(`${root}/underlyings`, {
      data: {
        name: `IV fixture ${token}`,
        type: "STOCK",
        primary_listing: {
          trading_venue_id: venues.items.find(
            (v: { mic: string }) => v.mic === "XETR",
          ).id,
          ticker: `IV${token.slice(0, 8)}`,
          currency_code: "EUR",
        },
      },
    }),
  );
  const warrant = await body(
    await request.post(`${root}/warrants`, {
      data: {
        issuer_id: issuer.id,
        underlying_id: underlying.id,
        display_name: `IV evidence ${token}`,
        isin: syntheticIsin(),
        option_direction: "CALL",
        strike: "100",
        strike_currency_code: "EUR",
        maturity_date: "2099-12-31",
        ratio: ".1",
      },
    }),
  );
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));
  await page.goto("/warrants-admin");
  await page
    .getByRole("button", { name: new RegExp(warrant.display_name) })
    .click();
  await page.getByText("Produktmerkmale für IV mit Beleg erfassen").click();
  await page.getByRole("button", { name: "Produktbelege laden" }).click();
  await expect(page.getByLabel("Ausübungsart", { exact: true })).toHaveValue(
    "",
  );
  await page
    .getByLabel("Produktart", { exact: true })
    .selectOption("VANILLA_WARRANT");
  await page
    .getByLabel("Ausübungsart", { exact: true })
    .selectOption("EUROPEAN");
  await page
    .getByLabel("Quanto-Eigenschaft", { exact: true })
    .selectOption("false");
  await page
    .getByLabel("Bezugsverhältnis-Konvention", { exact: true })
    .selectOption("UNDERLYING_UNITS_PER_WARRANT");
  await page
    .getByLabel("Bewertungszeitpunkt mit Zeitzone (optional)", { exact: true })
    .fill("2099-12-31T17:30:00+01:00");
  await page
    .getByLabel("Beleg geprüft am, mit Zeitzone", { exact: true })
    .fill("2026-09-01T12:00:00Z");
  await page
    .getByLabel("Dokument und Fundstelle", { exact: true })
    .fill(`Synthetic terms ${"A".repeat(180)}`);
  await page
    .getByLabel("Quellen-URL (optional)", { exact: true })
    .fill(`https://example.org/${"b".repeat(180)}`);
  await page
    .getByLabel("Prüfnotiz / Grund der Berichtigung", { exact: true })
    .fill("Synthetic fixture only; no actual product was reviewed");
  await expect(
    page.getByRole("button", { name: "Belegrevision speichern" }),
  ).toBeDisabled();
  await page
    .getByRole("checkbox", { name: /Ich habe die genannten Angaben/ })
    .check();
  await page.getByRole("button", { name: "Belegrevision speichern" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Belegrevision 1 gespeichert",
  );
  const stored = await (
    await request.get(`${root}/warrants/${warrant.id}/valuation-evidence`)
  ).json();
  expect(stored.current.facts.quanto).toBe(false);
  expect(stored.current.origin).toBe("MANUAL_DOCUMENT_REVIEW");
  await page.getByText("Letzte 20 Belegrevisionen").click();
  await page
    .getByText("Kursdaten-Verfügbarkeit und Erfassungsprotokoll")
    .click();
  await page
    .getByRole("button", { name: "Gespeichertes Protokoll laden" })
    .click();
  await expect(page.getByText(/Daraus folgt keine Entwarnung/)).toBeVisible();
  expect(requests.some((url) => url.startsWith("https://example.org/"))).toBe(
    false,
  );
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await expect(
      page.getByRole("button", { name: "Belegrevision speichern" }),
    ).toBeVisible();
    await testInfo.attach(`iv-evidence-${width}`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
  }
  await page.reload();
  await page
    .getByRole("button", { name: new RegExp(warrant.display_name) })
    .click();
  await page.getByText("Produktmerkmale für IV mit Beleg erfassen").click();
  await page.getByRole("button", { name: "Produktbelege laden" }).click();
  await expect(
    page.getByLabel("Quanto-Eigenschaft", { exact: true }),
  ).toHaveValue("false");
});
