import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { defaultAnalysisParameters } from "../../frontend/src/features/analysis/types/api";

const browserBase = new URL(
  process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:8080",
);
// The regular smoke bundle uses localhost for the API origin.
if (browserBase.hostname === "127.0.0.1") browserBase.hostname = "localhost";
test.use({ baseURL: browserBase.origin });

const createConfirmation =
  "Ich bestätige die Anlage genau einer Analyse für den angezeigten Basiswert und dieses Listing.";
const runConfirmation =
  "Ich bestätige diesen Datenkontext, den gewählten Zeitraum und alle Parameter für genau einen neuen Lauf.";
const createButton = "Bestätigte Analyse anlegen";
const runButton = "Bestätigten Analyselauf ausführen";
const timestamp = "2026-10-27T09:00:00Z";
type Write = { method: string; path: string; body: unknown };

function recordWrites(page: Page): Write[] {
  const writes: Write[] = [];
  page.on("request", (request) => {
    if (["GET", "OPTIONS"].includes(request.method())) return;
    writes.push({
      method: request.method(),
      path: new URL(request.url()).pathname.replace(/^\/api(?=\/api\/)/, ""),
      body: request.postDataJSON(),
    });
  });
  return writes;
}

test.describe("real analysis identity on the disposable PostgreSQL stack", () => {
  test.skip(
    process.env.TRADE_E2E_WRITES_ALLOWED !== "1" &&
      process.env.ANALYSIS_WORKFLOW_E2E_WRITES_ALLOWED !== "1",
    "Requires an explicitly disposable test stack",
  );

  test("one committed creation survives a failed run and an explicit second run", async ({
    page,
    request,
  }, testInfo) => {
    const api = new URL(
      process.env.ANALYSIS_WORKFLOW_E2E_API_BASE_URL ??
        "http://127.0.0.1:8000/api/v1",
    );
    expect(["localhost", "127.0.0.1", "[::1]"]).toContain(api.hostname);
    expect(["localhost", "127.0.0.1", "[::1]"]).toContain(browserBase.hostname);
    const root = api.toString().replace(/\/$/, "");
    const suffix = randomUUID().slice(0, 8);
    const name = `TEST ONLY analysis workflow ${suffix}`;
    const venueResponse = await request.get(
      `${root}/market-reference-data/trading-venues`,
    );
    expect(venueResponse.ok()).toBeTruthy();
    const venues = (await venueResponse.json()) as {
      items: { id: string; mic: string }[];
    };
    const venue = venues.items.find((item) => item.mic === "XETR");
    expect(venue).toBeDefined();
    const underlyingResponse = await request.post(`${root}/underlyings`, {
      data: {
        name,
        type: "STOCK",
        primary_listing: {
          trading_venue_id: venue!.id,
          ticker: `AW${suffix}`,
          currency_code: "EUR",
        },
      },
    });
    expect(underlyingResponse.status()).toBe(201);
    const created = (await underlyingResponse.json()) as { id: string };
    const underlying = (await (
      await request.get(`${root}/underlyings/${created.id}`)
    ).json()) as { id: string; primary_listing: { id: string } };
    const listingId = underlying.primary_listing.id;
    const writes = recordWrites(page);
    // No interception: every UI request in this case reaches API + PostgreSQL.
    await page.goto(
      `/market-analyses/setup?${new URLSearchParams({
        underlying_id: underlying.id,
        listing_id: listingId,
        overview_context: `underlying_id=${underlying.id}`,
      })}`,
    );
    await expect(page.getByText(name, { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: createButton }),
    ).toBeDisabled();
    expect(writes).toEqual([]);
    await page.getByRole("checkbox", { name: createConfirmation }).check();
    const receiptPromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/market-analyses"),
    );
    await page.getByRole("button", { name: createButton }).dblclick();
    const response = await receiptPromise;
    expect(response.status()).toBe(201);
    const receipt = (await response.json()) as {
      id: string;
      underlying_id: string;
      listing_id: string;
    };
    expect(receipt).toMatchObject({
      underlying_id: underlying.id,
      listing_id: listingId,
    });
    await expect(page).toHaveURL(new RegExp(`analysis_id=${receipt.id}`));
    await expect(page.getByText(/Analyse angelegt:/)).toBeVisible();
    await expect(page.getByRole("button", { name: runButton })).toBeDisabled();
    expect(writes).toEqual([
      {
        method: "POST",
        path: "/api/v1/market-analyses",
        body: { underlying_id: underlying.id, listing_id: listingId },
      },
    ]);

    // The synthetic listing has no prices. The real API rejects each explicitly
    // confirmed run with 422 before persisting any run; creation stays committed.
    await page.getByLabel("Von", { exact: true }).fill("2026-01-01");
    await page.getByLabel("Bis", { exact: true }).fill("2026-02-01");
    for (let attempt = 0; attempt < 2; attempt += 1) {
      if (attempt) {
        await page.getByLabel("Bis", { exact: true }).fill("2026-03-01");
      }
      await page.getByRole("checkbox", { name: runConfirmation }).check();
      const failedRun = page.waitForResponse(
        (entry) =>
          entry.request().method() === "POST" &&
          entry.url().endsWith(`/market-analyses/${receipt.id}/runs`),
      );
      await page.getByRole("button", { name: runButton }).click();
      expect((await failedRun).status()).toBe(422);
      await expect(page.getByRole("alert")).toContainText(
        "no persisted market data in requested range",
      );
      await expect(
        page.getByRole("checkbox", { name: runConfirmation }),
      ).not.toBeChecked();
      await expect(page).toHaveURL(new RegExp(`analysis_id=${receipt.id}`));
    }
    expect(writes).toHaveLength(3);
    expect(writes.slice(1).map((entry) => entry.path)).toEqual([
      `/api/v1/market-analyses/${receipt.id}/runs`,
      `/api/v1/market-analyses/${receipt.id}/runs`,
    ]);
    expect(writes[2].body).toEqual({
      start_date: "2026-01-01",
      end_date: "2026-03-01",
      model_version: "1.0.1",
      parameters: defaultAnalysisParameters,
    });
    const readbackResponse = await request.get(
      `${root}/market-analyses/${receipt.id}`,
    );
    expect(readbackResponse.ok()).toBeTruthy();
    const readback = await readbackResponse.json();
    expect(readback).toMatchObject({ analysis: receipt, runs: [] });
    const pageResponse = await request.get(
      `${root}/market-analyses/page?underlying_id=${underlying.id}&offset=0&limit=25`,
    );
    expect(pageResponse.ok()).toBeTruthy();
    const persisted = await pageResponse.json();
    expect(persisted.total).toBe(1);
    expect(persisted.items).toHaveLength(1);
    expect(persisted.items[0].id).toBe(receipt.id);
    await testInfo.attach("committed-analysis-and-failed-runs", {
      body: JSON.stringify({ receipt, readback, persisted, writes }, null, 2),
      contentType: "application/json",
    });
    await page
      .getByRole("link", { name: "← Zurück zum Ausgangskontext" })
      .click();
    await page
      .getByRole("button", { name: "Eingaben verwerfen und wechseln" })
      .click();
    await expect(page).toHaveURL(
      new RegExp(`/market-analyses/${receipt.id}\\?`),
    );
    await expect(
      page.getByText("Für diese Analyse wurde noch keine Version ausgeführt."),
    ).toBeVisible();
    expect(writes).toHaveLength(3);
  });
});

// Controlled browser cases below are separate from the real persistence proof.
const ownerId = "91000000-0000-4000-8000-000000000001";
const primaryId = "91000000-0000-4000-8000-000000000002";
const secondaryId = "91000000-0000-4000-8000-000000000003";
const analysisId = "91000000-0000-4000-8000-000000000004";
const analysis = {
  id: analysisId,
  underlying_id: ownerId,
  listing_id: secondaryId,
  market_data_instrument_id: null,
  created_at: timestamp,
  created_by: "Synthetic browser test",
};
const run = {
  version: 1,
  status: "COMPLETED",
  quality_status: "GOOD",
  model_id: "EOD_TREND_MOMENTUM",
  model_version: "1.0.1",
  observation_count: 250,
  analysis_time: timestamp,
  input_hash: "browser-fixture-hash-1",
};

async function installControlledApi(page: Page) {
  const listings = [primaryId, secondaryId].map((id) => ({
    id,
    underlying_id: ownerId,
    trading_venue_id: "91000000-0000-4000-8000-000000000005",
    trading_venue_mic: "XETR",
    trading_venue_name: "Xetra",
    ticker: id === secondaryId ? "SECONDARY" : "PRIMARY",
    currency_code: "EUR",
    lifecycle_status: "ACTIVE",
    is_primary: id === primaryId,
    version: 1,
    created_at: timestamp,
    updated_at: timestamp,
  }));
  const state = {
    created: true,
    completed: false,
    loseCreateResponse: false,
    failReadback: false,
    runs: [run],
    parameters: { ...defaultAnalysisParameters },
    reads: 0,
  };
  await page.route("https://**", (route) => route.abort());
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(
      /^\/api(?=\/api\/)/,
      "",
    );
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204 });
    if (request.method() === "GET") {
      state.reads += 1;
      if (path === `/api/v1/underlyings/${ownerId}`) {
        return json({
          id: ownerId,
          name: "TEST ONLY analysis ETF",
          type: "ETF",
          isin: "TEST-ANALYSIS",
          wkn: null,
          lifecycle_status: "ACTIVE",
          quality_status: "VERIFIED",
          version: 1,
          created_at: timestamp,
          updated_at: timestamp,
          primary_listing: listings[0],
          listings,
        });
      }
      if (path === "/api/v1/market-analyses")
        return json(state.created ? [analysis] : []);
      if (path === `/api/v1/market-analyses/${analysisId}`) {
        if (state.completed && state.failReadback)
          return json({ message: "Controlled GET failure" }, 503);
        return json({ analysis, runs: state.runs });
      }
      if (path === `/api/v1/market-analyses/${analysisId}/events`)
        return json([]);
      const selected = state.runs.find(
        (item) =>
          path === `/api/v1/market-analyses/${analysisId}/runs/${item.version}`,
      );
      if (selected)
        return json({
          analysis,
          run: selected,
          parameters: state.parameters,
          metrics: {
            momentum: selected.version === 1 ? "historical-one" : "current-two",
          },
          notes: [],
          data_sources: ["SYNTHETIC"],
          criteria: [],
          snapshot: [],
        });
    }
    if (request.method() === "POST" && path === "/api/v1/market-analyses") {
      state.created = true;
      state.runs = [];
      if (state.loseCreateResponse) return route.abort("failed");
      return json(analysis, 201);
    }
    if (
      request.method() === "POST" &&
      path === `/api/v1/market-analyses/${analysisId}/runs`
    ) {
      state.completed = true;
      state.parameters = request.postDataJSON().parameters;
      const latest = {
        ...run,
        version: Math.max(0, ...state.runs.map((item) => item.version)) + 1,
      };
      state.runs.push(latest);
      return json(latest, 201);
    }
    return json(
      {
        code: "UNEXPECTED_TEST_REQUEST",
        message: path,
        details: [],
        timestamp,
      },
      404,
    );
  });
  return state;
}

test("controlled: completed run plus GET failure offers only readback, preserving the exact secondary listing", async ({
  page,
}, testInfo) => {
  const state = await installControlledApi(page);
  state.runs = [];
  state.failReadback = true;
  const writes = recordWrites(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/market-analyses/setup?analysis_id=${analysisId}`);
  await expect(page.getByText(/SECONDARY · Xetra/)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Neue Analyseversion", exact: true }),
  ).toBeFocused();
  await page.getByLabel("Von", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Bis", { exact: true }).fill("2026-10-01");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await testInfo.attach("analysis-narrow-editor", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("analysis-narrow-editor.png"),
    }),
    contentType: "image/png",
  });
  await page.getByRole("checkbox", { name: runConfirmation }).focus();
  await page.keyboard.press("Space");
  await page.getByRole("button", { name: runButton }).dblclick();
  await expect(
    page.getByRole("heading", {
      name: "Schreibauftrag für Version 1 abgeschlossen",
    }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "das Nachlesen ist gestört",
  );
  expect(writes).toEqual([
    {
      method: "POST",
      path: `/api/v1/market-analyses/${analysisId}/runs`,
      body: {
        start_date: "2026-01-01",
        end_date: "2026-10-01",
        model_version: "1.0.1",
        parameters: defaultAnalysisParameters,
      },
    },
  ]);
  state.failReadback = false;
  const reads = state.reads;
  await page
    .getByRole("button", { name: "Nur Lesestand erneut laden" })
    .click();
  await expect(page.getByText(/mit Modell EOD_TREND_MOMENTUM/)).toBeVisible();
  expect(state.reads).toBeGreaterThan(reads);
  expect(writes).toHaveLength(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await testInfo.attach("analysis-narrow-readback", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("analysis-narrow-readback.png"),
    }),
    contentType: "image/png",
  });
  await page
    .getByRole("link", { name: "Genau diese Analyseversion öffnen" })
    .click();
  await expect(page).toHaveURL(
    new RegExp(`/market-analyses/${analysisId}\\?version=1`),
  );
  await expect(
    page.getByRole("heading", { name: "Ergebnis · Version 1" }),
  ).toBeVisible();
  expect(writes).toHaveLength(1);
});

test("controlled: unknown creation lists matching reads without adopting or repeating the request", async ({
  page,
}) => {
  const state = await installControlledApi(page);
  state.created = false;
  state.loseCreateResponse = true;
  const writes = recordWrites(page);
  await page.goto(
    `/market-analyses/setup?underlying_id=${ownerId}&listing_id=${secondaryId}`,
  );
  await page.getByRole("checkbox", { name: createConfirmation }).check();
  await page.getByRole("button", { name: createButton }).click();
  await expect(
    page.getByText(/Der Transportabschluss ist unbekannt/),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: `Analyse ${analysisId} lesend öffnen` }),
  ).toBeVisible();
  await expect(page).not.toHaveURL(/analysis_id=/);
  await expect(page.getByRole("button", { name: createButton })).toBeDisabled();
  await page
    .getByRole("button", { name: "Nur Lesestand erneut laden" })
    .click();
  await expect(
    page.getByRole("link", { name: `Analyse ${analysisId} lesend öffnen` }),
  ).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toEqual({
    underlying_id: ownerId,
    listing_id: secondaryId,
  });
});

test("controlled: historical version, candidate return and keyboard draft guard remain exact", async ({
  page,
}, testInfo) => {
  const state = await installControlledApi(page);
  state.runs = [
    run,
    { ...run, version: 2, input_hash: "browser-fixture-hash-2" },
  ];
  const writes = recordWrites(page);
  await page.goto(
    `/market-analyses/${analysisId}?version=1&candidate_id=candidate-context&evaluation_id=evaluation-context`,
  );
  await expect(
    page.getByRole("heading", { name: "Ergebnis · Version 1" }),
  ).toBeVisible();
  await expect(page.getByText("historical-one", { exact: true })).toBeVisible();
  await expect(page.getByText("current-two", { exact: true })).toHaveCount(0);
  await page
    .getByRole("link", {
      name: "Neue Analyseversion aus Version 1 vorbereiten",
    })
    .click();
  await expect(page).toHaveURL(/source_version=1/);
  await expect(page.getByLabel("Von", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Bis", { exact: true })).toHaveValue("");
  const back = page.getByRole("link", {
    name: "← Zurück zum konkreten Kandidaten",
  });
  await expect(back).toHaveAttribute(
    "href",
    "/candidates?candidate=candidate-context&evaluation=evaluation-context",
  );
  await page.getByLabel("Von", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Bis", { exact: true }).fill("2026-10-01");
  await page
    .getByRole("button", { name: "Parameter aus Version 1 vorbereiten" })
    .click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Hier bleiben" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Von", { exact: true })).toHaveValue(
    "2026-01-01",
  );
  await back.click();
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/source_version=1/);
  await expect(page.getByLabel("Bis", { exact: true })).toHaveValue(
    "2026-10-01",
  );
  expect(writes).toEqual([]);
  await testInfo.attach("analysis-historical-editor", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("analysis-historical-editor.png"),
    }),
    contentType: "image/png",
  });
});
