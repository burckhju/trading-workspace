import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

// Requires the separately identified CI Compose stack + Python fixtures. Never a user stack.
test("real PostgreSQL: captured full exit, review, journal, lesson and stale correction", async ({
  page,
  request,
  baseURL,
}) => {
  test.skip(
    process.env.JOURNAL_E2E_WRITES_ALLOWED !== "1",
    "Explicit disposable PostgreSQL journal browser qualification required",
  );
  test.setTimeout(120_000);
  expect(process.env.CI).toBe("true");
  expect(baseURL).toBe("http://127.0.0.1:28080");
  const api = `${baseURL}/api/api/v1`;
  const post = async (path: string, data?: object) => {
    const response = await request.post(api + path, { data });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  };
  const suffix = crypto.randomUUID();
  const issuer = await post("/market-reference-data/issuers", {
    legal_name: `Journal CI ${suffix}`,
    display_name: "Synthetic journal CI",
  });
  const venue = (
    await (
      await request.get(api + "/market-reference-data/trading-venues")
    ).json()
  ).items.find((v: { mic: string }) => v.mic === "XETR");
  const underlying = await post("/underlyings", {
    name: `Synthetic journal ${suffix}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venue.id,
      ticker: `J${suffix.slice(0, 7)}`,
      currency_code: "EUR",
    },
  });
  const product = await post("/warrants", {
    issuer_id: issuer.id,
    underlying_id: underlying.id,
    display_name: `Synthetic Journal Call ${suffix}`,
    option_direction: "CALL",
    strike: "500",
    strike_currency_code: "EUR",
    maturity_date: "2099-12-31",
    ratio: "0.1",
  });
  const buy = await post("/trade-position/purchases/external", {
    product_id: product.id,
    quantity: 10,
    price_per_unit: "0.55",
    executed_on: "2026-08-17",
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
  });
  const tid = buy.trade.id;
  expect(
    (
      await request.post(api + `/post-trade/trades/${tid}/observation`)
    ).status(),
  ).toBe(409);
  const sale = await post(`/trade-position/trades/${tid}/sales`, {
    quantity: 10,
    price_per_unit: "0.65",
    executed_on: "2026-08-18",
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
  });
  expect(sale.position.is_closed).toBe(true);
  expect(Number(sale.position.realized_gross_pnl)).toBe(1);
  const observation = await post(`/post-trade/trades/${tid}/observation`);
  const root = resolve(process.cwd(), "..");
  execFileSync(
    "python",
    [
      resolve(root, "tests/e2e/support/seed_journal_prices.py"),
      observation.underlying_listing_id,
    ],
    {
      cwd: root,
      env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
      stdio: "pipe",
    },
  );
  await page.goto(`/post-trade?trade_id=${tid}`);
  // FT-011 owner refresh completes only after 20 seeded completed sessions.
  await expect(page.getByText("COMPLETED", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Exit Review anlegen", exact: true })
    .click();
  await page
    .getByLabel("Review-Begründung")
    .fill(
      "Bewusstes synthetisches Review – kein handelbarer Underlying-Vergleich.",
    );
  await page
    .getByRole("button", { name: "Review finalisieren", exact: true })
    .click();
  const journal = page.getByRole("region", {
    name: "Trade-Journal",
    exact: true,
  });
  await journal
    .getByRole("button", { name: "Journalentwurf anlegen", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await journal
    .getByLabel("Was lief gut?")
    .fill("Exit und Reflexion getrennt dokumentiert.");
  await journal
    .getByLabel("Weitere Notizen")
    .fill("Kein virtueller Gewinn wurde als realisiert erfasst.");
  await expect(
    journal.getByRole("button", { name: "Journal finalisieren", exact: true }),
  ).toBeDisabled();
  await journal
    .getByRole("button", { name: "Journalentwurf speichern", exact: true })
    .click();
  await expect(
    journal.getByRole("button", { name: "Journal finalisieren", exact: true }),
  ).toBeEnabled();
  await page.reload();
  await expect(journal.getByLabel("Was lief gut?")).toHaveValue(
    "Exit und Reflexion getrennt dokumentiert.",
  );
  await journal
    .getByRole("button", { name: "Journal finalisieren", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await expect(journal.getByLabel("Was lief gut?")).toHaveCount(0);
  const getHistory = async () =>
    (await request.get(api + `/learning/trades/${tid}/journal`)).json();
  const original = (await getHistory()).versions[0].version;
  await journal
    .getByRole("button", {
      name: "Journalversion als Evidence übergeben",
      exact: true,
    })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await journal.getByLabel("Lesson-Titel").fill("Synthetische Journal-Lesson");
  await journal.getByLabel("Lesson-Kategorie").fill("Prozess");
  await journal
    .getByLabel("Lesson-Inhalt")
    .fill(
      "Meine ausdrückliche Interpretation: Dokumentation prüfen, keine automatische Handelsregel.",
    );
  await journal
    .getByRole("button", { name: "Lesson anlegen", exact: true })
    .click();
  const lessonLink = journal.getByRole("link", {
    name: "Angelegte Lesson öffnen",
    exact: true,
  });
  await expect(lessonLink).toBeVisible();
  const lessonPath = (await lessonLink.getAttribute("href"))!;
  const lessonId = lessonPath.split("/").at(-1)!;
  const before = await (
    await request.get(api + `/learning/lessons/${lessonId}`)
  ).json();
  await post(
    `/trade-position/trades/${tid}/executions/${sale.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 10,
      price_per_unit: "0.60",
      executed_on: "2026-08-18",
      execution_timezone: "Europe/Berlin",
    },
  );
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  await expect(journal.getByText(/Quellenprüfung jetzt: STALE/)).toBeVisible();
  expect((await getHistory()).versions[0].version).toEqual(original);
  await lessonLink.click();
  await expect(page.getByText(/Quellenprüfung jetzt: STALE/)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Genau diese Journalversion öffnen" }),
  ).toHaveAttribute(
    "href",
    `/post-trade?trade_id=${tid}&journal_version_id=${original.id}`,
  );
  const after = await (
    await request.get(api + `/learning/lessons/${lessonId}`)
  ).json();
  expect(after).toEqual(before);
  await page.screenshot({
    path: "test-results/journal-real-postgres-stale.png",
    fullPage: true,
  });
});
