import { randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { chartIdentity } from "../../frontend/src/test/chartFixtures";
import type { ProviderMapping } from "../../frontend/src/features/administration/services/topDownAdminClient";

const browserBase = new URL(
  process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:8080",
);
// The regular smoke bundle uses localhost for its API origin.
if (browserBase.hostname === "127.0.0.1") browserBase.hostname = "localhost";
test.use({ baseURL: browserBase.origin });

const confirmation =
  "Ich bestätige den angezeigten Kontext und diesen einzelnen Schritt.";

test.describe("real administrative assignment on the disposable stack", () => {
  // Reuse the existing smoke runner's explicit synthetic-write permission.
  // A separate local flag permits qualification on an identified native test stack.
  test.skip(
    process.env.TRADE_E2E_WRITES_ALLOWED !== "1" &&
      process.env.REFERENCE_DATA_E2E_WRITES_ALLOWED !== "1",
    "Requires an explicitly disposable test stack",
  );

  test("candidate sector repair preserves identities, writes once and reads committed readiness", async ({
    page,
    request,
  }, testInfo) => {
    const api = new URL(
      process.env.REFERENCE_DATA_E2E_API_BASE_URL ??
        "http://127.0.0.1:8000/api/v1",
    );
    expect(["127.0.0.1", "localhost", "[::1]"]).toContain(api.hostname);
    expect(["127.0.0.1", "localhost", "[::1]"]).toContain(browserBase.hostname);
    const root = api.toString().replace(/\/$/, "");
    const suffix = randomUUID().slice(0, 8);
    const name = `TEST ONLY UI5 ${suffix}`;
    const venuesResponse = await request.get(
      `${root}/market-reference-data/trading-venues`,
    );
    expect(venuesResponse.ok()).toBeTruthy();
    const venues = (await venuesResponse.json()) as {
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
          ticker: `UI5${suffix}`,
          currency_code: "EUR",
        },
      },
    });
    expect(underlyingResponse.status()).toBe(201);
    const underlying = (await underlyingResponse.json()) as { id: string };
    const sectorResponse = await request.post(
      `${root}/top-down-reference-data/sectors`,
      {
        data: {
          code: `UI5-${suffix}`,
          name: `TEST ONLY UI5 sector ${suffix}`,
          classification_system: "UI5 SYNTHETIC",
          classification_version: "browser-fixture-v1",
        },
      },
    );
    expect(sectorResponse.status()).toBe(201);
    const sector = (await sectorResponse.json()) as { id: string };
    const candidateResponse = await request.post(`${root}/candidates`, {
      data: { underlying_id: underlying.id },
    });
    expect(candidateResponse.status()).toBe(201);
    const candidate = (await candidateResponse.json()) as { id: string };
    const workflowUrl = `${root}/candidates/${candidate.id}/live-workflow`;
    const initial = await (await request.get(workflowUrl)).json();
    // This is deliberately a blocked step other than next_action.
    expect(initial.next_action).toBe("ASSIGN_BROAD_MARKET_BENCHMARK");
    expect(initial.steps).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          action: "ASSIGN_SECTOR",
          status: "BLOCKED",
          action_params: { underlying_id: underlying.id },
        }),
      ]),
    );

    const writes: { method: string; url: string; body: unknown }[] = [];
    page.on("request", (entry) => {
      if (entry.method() === "GET" || entry.method() === "OPTIONS") return;
      writes.push({
        method: entry.method(),
        url: entry.url(),
        body: entry.postDataJSON(),
      });
    });
    // No interception: each UI request reaches the real API and PostgreSQL.
    await page.goto(`/candidates?candidate=${candidate.id}`);
    const repair = page.locator(
      'a[href*="top-down-admin"][href*="action=ASSIGN_SECTOR&"]',
    );
    await expect(repair).toHaveCount(1);
    await repair.click();
    await expect(page).toHaveURL(/\/chart-setup\?/);
    await expect(
      page.getByRole("heading", { name: "Diagramm-Datenbasis einrichten" }),
    ).toBeVisible();
    await expect(page.getByText(name, { exact: true })).toBeVisible();
    await expect(page.getByText(/MANUAL_ADMIN/)).toBeVisible();
    await expect(page.getByText(/Candidate live workflow/)).toBeVisible();
    const target = page.getByRole("combobox", {
      name: "Administrierter Sektor",
      exact: true,
    });
    await target.selectOption(sector.id);
    const submit = page.getByRole("button", {
      name: "Geprüften Schritt ausführen",
    });
    await expect(submit).toBeDisabled();
    expect(writes).toEqual([]);
    const effectiveDay = new Date().toISOString().slice(0, 10);
    await page.getByRole("checkbox", { name: confirmation }).check();
    const assignmentResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response
          .url()
          .endsWith(
            `/top-down-reference-data/underlyings/${underlying.id}/sector-assignments`,
          ),
    );
    // Two rapid pointer clicks still produce one confirmed administrative write.
    await submit.dblclick();
    const committedResponse = await assignmentResponse;
    expect(committedResponse.status()).toBe(201);
    const committed = await committedResponse.json();
    expect(committed).toMatchObject({
      valid_from: effectiveDay,
      valid_to: null,
      source: "MANUAL_ADMIN",
      quality_status: "GOOD",
    });
    await expect(page.getByText(/Schritt gespeichert\./)).toBeVisible();
    expect(writes).toEqual([
      {
        method: "POST",
        url: expect.stringContaining(
          `/top-down-reference-data/underlyings/${underlying.id}/sector-assignments`,
        ),
        body: {
          sector_id: sector.id,
          valid_from: effectiveDay,
          valid_to: null,
          source: "MANUAL_ADMIN",
          source_reference: "Candidate live workflow",
          quality_status: "GOOD",
        },
      },
    ]);
    const currentWorkflow = await (await request.get(workflowUrl)).json();
    expect(currentWorkflow.steps).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "SECTOR_ASSIGNMENT",
          status: "COMPLETE",
          resource_id: sector.id,
          action: null,
        }),
      ]),
    );
    const catalog = await (
      await request.get(`${root}/market-charts/catalog?as_of=${effectiveDay}`)
    ).json();
    expect(catalog.sectors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          context: expect.objectContaining({ id: sector.id, active: true }),
        }),
      ]),
    );
    if (process.env.REFERENCE_DATA_E2E_RUN_ID) {
      const sqlEvidence = execFileSync(
        process.env.REFERENCE_DATA_E2E_PYTHON ?? "python3",
        [
          resolve(dirname(testInfo.file), "support/reference_data_postgres.py"),
          "--underlying",
          underlying.id,
          "--assignment",
          committed.id,
        ],
        { encoding: "utf8" },
      );
      const row = JSON.parse(sqlEvidence) as Record<string, unknown>;
      expect(row).toMatchObject({
        underlying_id: underlying.id,
        sector_id: sector.id,
        assignment_id: committed.id,
        valid_from: effectiveDay,
        valid_to: null,
        source: "MANUAL_ADMIN",
        source_reference: "Candidate live workflow",
        count: 1,
      });
      const sqlEvidencePath = testInfo.outputPath(
        "exact-postgres-assignment.json",
      );
      writeFileSync(sqlEvidencePath, sqlEvidence);
      await testInfo.attach("exact-postgres-assignment", {
        path: sqlEvidencePath,
        contentType: "application/json",
      });
    }
    await testInfo.attach("real-assignment-desktop", {
      body: await page.screenshot({
        fullPage: true,
        path: testInfo.outputPath("real-assignment-desktop.png"),
      }),
      contentType: "image/png",
    });
    await page.getByRole("link", { name: "Zurück zum Kandidaten" }).click();
    await expect(page).toHaveURL(
      new RegExp(`/candidates\\?candidate=${candidate.id}$`),
    );
    await expect(repair).toHaveCount(0);
    expect(writes).toHaveLength(1);
  });
});

// Controlled browser cases below use explicit synthetic responses; they are not
// included in the real API/PostgreSQL proof above.
async function blockExternalRequests(page: Page) {
  await page.route("https://**", (route) => route.abort());
}

const mappingUnderlying = "90000000-0000-4000-8000-000000000001";
const primaryListing = "90000000-0000-4000-8000-000000000002";
const chosenListing = "90000000-0000-4000-8000-000000000003";
const mappingId = "90000000-0000-4000-8000-000000000004";
const fixtureTime = "2026-10-26T09:00:00Z";

async function installMappingApi(page: Page) {
  const state = {
    mapping: {
      id: mappingId,
      workspace_id: "00000000-0000-4000-8000-000000000001",
      listing_id: chosenListing,
      market_data_instrument_id: "90000000-0000-4000-8000-000000000005",
      provider: "EODHD",
      provider_symbol: "REVIEWED",
      provider_exchange_code: "US",
      status: "DISABLED",
      validated_at: null,
      validation_message: null,
      created_at: fixtureTime,
      updated_at: fixtureTime,
      version: 3,
    } as ProviderMapping,
    writes: [] as { method: string; path: string; body: unknown }[],
    venueReads: 0,
    failVenueAfterWrite: false,
    validationFailure: "" as "" | "provider" | "transport",
    venue: "MATCHED" as "MATCHED" | "CONFLICT" | "AMBIGUOUS" | "UNRESOLVED",
  };
  const listing = (id: string, primary: boolean) => ({
    id,
    underlying_id: mappingUnderlying,
    trading_venue_id: "90000000-0000-4000-8000-000000000006",
    trading_venue_mic: primary ? "XETR" : "XNYS",
    trading_venue_name: primary
      ? "Fixture primary venue"
      : "Fixture chosen venue",
    ticker: primary ? "PRIMARY" : "CHOSEN",
    currency_code: "USD",
    lifecycle_status: "ACTIVE",
    is_primary: primary,
    version: 1,
    created_at: fixtureTime,
    updated_at: fixtureTime,
  });
  const underlying = {
    id: mappingUnderlying,
    type: "ETF",
    name: "TEST ONLY UI5 mapping ETF",
    isin: "US0000000001",
    wkn: null,
    lifecycle_status: "ACTIVE",
    quality_status: "COMPLETE",
    version: 1,
    created_at: fixtureTime,
    updated_at: fixtureTime,
    primary_listing: listing(primaryListing, true),
    listings: [listing(primaryListing, true), listing(chosenListing, false)],
  };
  await blockExternalRequests(page);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    if (method !== "GET") {
      state.writes.push({ method, path, body: request.postDataJSON() });
      if (
        method === "POST" &&
        path.endsWith(`/provider-mappings/${mappingId}/validate`)
      ) {
        if (state.validationFailure === "transport")
          return route.abort("failed");
        if (state.validationFailure === "provider") {
          return route.fulfill({
            status: 422,
            json: {
              code: "SYNTHETIC_PROVIDER_VALIDATION",
              message:
                "Synthetic provider validation rejected: exchange mismatch",
              details: [],
              timestamp: fixtureTime,
            },
          });
        }
        state.mapping = {
          ...state.mapping,
          version: state.mapping.version + 1,
          status: "ACTIVE",
          validated_at: fixtureTime,
        };
        return route.fulfill({ json: state.mapping });
      }
      if (method === "PUT" && path.endsWith("/provider-mappings")) {
        const body = request.postDataJSON() as {
          provider_symbol: string;
          provider_exchange_code: string;
        };
        state.mapping = {
          ...state.mapping,
          version: state.mapping.version + 1,
          status: "DISABLED",
          validated_at: null,
          provider_symbol: body.provider_symbol.trim().toUpperCase(),
          provider_exchange_code: body.provider_exchange_code
            .trim()
            .toUpperCase(),
        };
        return route.fulfill({ json: state.mapping });
      }
      return route.fulfill({
        status: 422,
        json: { detail: "Unexpected synthetic write" },
      });
    }
    if (path.endsWith("/market-charts/catalog")) {
      return route.fulfill({
        json: {
          references: [],
          sectors: [],
          proxies: [],
          taxonomy_status: "EMPTY",
          as_of: "2026-10-26",
        },
      });
    }
    if (
      path.endsWith("/top-down-reference-data/market-references") ||
      path.endsWith("/top-down-reference-data/sectors")
    ) {
      return route.fulfill({ json: [] });
    }
    if (path.endsWith(`/market-charts/underlyings/${mappingUnderlying}`)) {
      return route.fulfill({
        json: {
          underlying_id: mappingUnderlying,
          subject: {
            ...chartIdentity(
              `listing:${primaryListing}`,
              underlying.name,
              "ETF",
            ),
            listing_id: primaryListing,
            underlying_id: mappingUnderlying,
          },
          market: null,
          sector: null,
          issues: [],
          assignment_date: "2026-10-26",
        },
      });
    }
    if (path.endsWith(`/underlyings/${mappingUnderlying}`)) {
      return route.fulfill({ json: underlying });
    }
    if (path.endsWith("/underlyings")) {
      return route.fulfill({
        json: { items: [underlying], total: 1, limit: 50, offset: 0 },
      });
    }
    if (path.endsWith("/provider-mappings")) {
      return route.fulfill({ json: [state.mapping] });
    }
    if (path.endsWith(`/provider-mappings/${mappingId}/venue-reconciliation`)) {
      state.venueReads += 1;
      if (state.failVenueAfterWrite && state.writes.length) {
        return route.fulfill({
          status: 503,
          json: {
            code: "SYNTHETIC_READ_FAILURE",
            message: "Synthetic venue read unavailable",
            details: [],
            timestamp: fixtureTime,
          },
        });
      }
      return route.fulfill({
        json: {
          status: state.venue,
          listing_venue_id: "90000000-0000-4000-8000-000000000006",
          evidence_venue_ids:
            state.venue === "MATCHED"
              ? ["90000000-0000-4000-8000-000000000006"]
              : [],
          explanation: `Synthetic venue result: ${state.venue}`,
        },
      });
    }
    return route.fulfill({
      status: 404,
      json: { detail: `Unexpected synthetic GET ${path}` },
    });
  });
  return state;
}

function mappingUrl(action: string): string {
  return `/chart-setup?action=${action}&underlying_id=${mappingUnderlying}&listing_id=${chosenListing}&mapping_id=${mappingId}`;
}

test("structured mapping prefill preserves the nonprimary listing and protects the keyboard draft", async ({
  page,
}, testInfo) => {
  const state = await installMappingApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(mappingUrl("listingMapping"));
  const symbol = page.getByLabel("Geprüftes EODHD-Symbol", { exact: true });
  await expect(symbol).toHaveValue("REVIEWED");
  await expect(page.getByLabel("Geprüfter EODHD-Exchange-Code")).toHaveValue(
    "US",
  );
  await expect(page.getByLabel("Eindeutige Notierung")).toHaveValue(
    chosenListing,
  );
  const submit = page.getByRole("button", {
    name: "Geprüften Schritt ausführen",
  });
  await expect(
    page.getByRole("checkbox", { name: confirmation }),
  ).toBeDisabled();
  await expect(submit).toBeDisabled();
  await symbol.fill(" reviewed ");
  await expect(submit).toBeDisabled();
  await symbol.fill("REVIEWED_NEW");
  await page.getByRole("checkbox", { name: confirmation }).check();
  await symbol.fill("REVIEWED_NEWER");
  await page.getByRole("link", { name: "Diagramme", exact: true }).click();
  const guard = page.getByRole("alertdialog");
  await expect(guard).toBeVisible();
  await expect(
    guard.getByRole("button", { name: "Hier bleiben" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(symbol).toHaveValue("REVIEWED_NEWER");
  await expect(
    page.getByRole("checkbox", { name: confirmation }),
  ).not.toBeChecked();
  expect(state.writes).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await testInfo.attach("mapping-draft-mobile", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("mapping-draft-mobile.png"),
    }),
    contentType: "image/png",
  });
  await page
    .getByRole("combobox", { name: "Aktion", exact: true })
    .selectOption("listingValidate");
  await page
    .getByRole("button", { name: "Entwurf verwerfen und fortfahren" })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Aktion", exact: true }),
  ).toHaveValue("listingValidate");
  expect(state.writes).toEqual([]);
});

test("successful validation and failed venue read are separated; retry reads only and conflict blocks import", async ({
  page,
}) => {
  const state = await installMappingApi(page);
  await page.goto(mappingUrl("listingValidate"));
  await expect(page.getByText(/Mappingrevision: 3/)).toBeVisible();
  await expect(page.getByText(/^Gelesene Providerkennung:/)).toHaveText(
    "Gelesene Providerkennung: EODHD · Symbol: REVIEWED · Exchange-Code: US",
  );
  state.failVenueAfterWrite = true;
  await page.getByRole("checkbox", { name: confirmation }).check();
  await page
    .getByRole("button", { name: "Geprüften Schritt ausführen" })
    .click();
  await expect(page.getByText(/Prüfauftrag abgeschlossen\./)).toBeVisible();
  await expect(
    page.getByText(/Synthetic venue read unavailable/),
  ).toBeVisible();
  expect(state.writes).toEqual([
    {
      method: "POST",
      path: expect.stringContaining(`/provider-mappings/${mappingId}/validate`),
      body: { enabled: true, actor_name: "Trading Workspace User" },
    },
  ]);
  state.failVenueAfterWrite = false;
  state.venue = "CONFLICT";
  await page
    .getByRole("button", { name: "Nur Lesestand erneut laden" })
    .click();
  await expect(
    page.getByText("Handelsplatzabgleich: CONFLICT", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Mappingrevision: 4/)).toBeVisible();
  await expect(page.getByText(/nicht als eindeutig geklärt/)).toBeVisible();
  expect(state.writes).toHaveLength(1);
  await page
    .getByRole("combobox", { name: "Aktion", exact: true })
    .selectOption("listingImport");
  await expect(
    page.getByText(/Vor dem Import muss der Handelsplatz eindeutig/),
  ).toBeVisible();
  await expect(page.getByText(/^Gelesene Providerkennung:/)).toHaveText(
    "Gelesene Providerkennung: EODHD · Symbol: REVIEWED · Exchange-Code: US",
  );
  await expect(
    page.getByRole("button", { name: "Geprüften Schritt ausführen" }),
  ).toBeDisabled();
  expect(state.writes).toHaveLength(1);
});

test("changed mapping values are visible for review while the single editor preserves the local draft", async ({
  page,
}, testInfo) => {
  const state = await installMappingApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(mappingUrl("listingMapping"));
  const symbol = page.getByLabel("Geprüftes EODHD-Symbol", { exact: true });
  const exchange = page.getByLabel("Geprüfter EODHD-Exchange-Code");
  await expect(symbol).toHaveValue("REVIEWED");
  await expect(page.getByText(/^Gelesene Providerkennung:/)).toHaveCount(0);
  await symbol.fill("REVIEWED_LOCAL");
  const externalSymbol = `OTHER_TAB_${"X".repeat(48)}`;
  state.mapping = {
    ...state.mapping,
    provider_symbol: externalSymbol,
    provider_exchange_code: "XETRA",
    version: 4,
  };
  const confirm = page.getByRole("checkbox", { name: confirmation });
  const submit = page.getByRole("button", {
    name: "Geprüften Schritt ausführen",
  });
  await confirm.check();
  await submit.click();
  const review = page.getByRole("button", {
    name: "Aktuellen Stand prüfen und Entwurf beibehalten",
  });
  await expect(review).toBeVisible();
  await expect(page.getByText(/^Gelesene Providerkennung:/)).toHaveText(
    `Gelesene Providerkennung: EODHD · Symbol: ${externalSymbol} · Exchange-Code: XETRA`,
  );
  await expect(page.getByText(/Mappingrevision: 4/)).toBeVisible();
  await expect(symbol).toHaveValue("REVIEWED_LOCAL");
  await expect(exchange).toHaveValue("US");
  await expect(page.getByRole("form")).toHaveCount(1);
  await expect(confirm).not.toBeChecked();
  await expect(submit).toBeDisabled();
  expect(state.writes).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await testInfo.attach("mapping-conflict-review-mobile", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("mapping-conflict-review-mobile.png"),
    }),
    contentType: "image/png",
  });
  await review.focus();
  await page.keyboard.press("Enter");
  await expect(confirm).not.toBeChecked();
  await confirm.focus();
  await page.keyboard.press("Space");
  await submit.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Schritt gespeichert\./)).toBeVisible();
  expect(state.writes).toEqual([
    {
      method: "PUT",
      path: "/api/v1/market-data/provider-mappings",
      body: {
        listing_id: chosenListing,
        provider: "EODHD",
        provider_symbol: "REVIEWED_LOCAL",
        provider_exchange_code: "US",
        actor_name: "Trading Workspace User",
      },
    },
  ]);
  await expect(page.getByText(/Mappingrevision: 5/)).toBeVisible();
  await expect(page.getByText(/^Gelesene Providerkennung:/)).toHaveCount(0);
});

test("explicit provider rejection preserves the correction context without a follow-up write", async ({
  page,
}) => {
  const state = await installMappingApi(page);
  state.validationFailure = "provider";
  await page.goto(mappingUrl("listingValidate"));
  await expect(page.getByText(/Mappingrevision: 3/)).toBeVisible();
  await page.getByRole("checkbox", { name: confirmation }).check();
  await page
    .getByRole("button", { name: "Geprüften Schritt ausführen" })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Synthetic provider validation rejected: exchange mismatch",
  );
  await expect(page.getByLabel("Eindeutige Notierung")).toHaveValue(
    chosenListing,
  );
  await expect(page.getByText(/Mappingrevision: 3/)).toBeVisible();
  expect(state.writes).toHaveLength(1);
  expect(state.mapping.status).toBe("DISABLED");
});

test("unknown validation transport outcome triggers a read and never an automatic replay", async ({
  page,
}) => {
  const state = await installMappingApi(page);
  state.validationFailure = "transport";
  await page.goto(mappingUrl("listingValidate"));
  await expect(page.getByText(/Mappingrevision: 3/)).toBeVisible();
  const beforeReads = state.venueReads;
  await page.getByRole("checkbox", { name: confirmation }).check();
  await page
    .getByRole("button", { name: "Geprüften Schritt ausführen" })
    .click();
  await expect(page.getByText(/unbekannt|unklar/i).first()).toBeVisible();
  await expect.poll(() => state.venueReads).toBeGreaterThan(beforeReads);
  expect(state.writes).toHaveLength(1);
  await page
    .getByRole("button", { name: "Nur Lesestand erneut laden" })
    .click();
  expect(state.writes).toHaveLength(1);
  await expect(
    page.getByRole("button", { name: "Geprüften Schritt ausführen" }),
  ).toBeDisabled();
});

test("unknown workflow context is blocked without writes on a narrow screen", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await blockExternalRequests(page);
  const writes: string[] = [];
  await page.route("**/api/v1/**", (route) => {
    if (route.request().method() !== "GET") writes.push(route.request().url());
    return route.fulfill({ json: [] });
  });
  await page.goto("/top-down-admin?action=UNKNOWN_UI5_ACTION");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /ausführen|speichern/i }),
  ).toHaveCount(0);
  expect(writes).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await testInfo.attach("blocked-context-mobile", {
    body: await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("blocked-context-mobile.png"),
    }),
    contentType: "image/png",
  });
});
