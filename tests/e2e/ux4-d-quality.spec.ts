import {
  expect,
  test,
  type BrowserContext,
  type Locator,
  type Page,
  type TestInfo,
} from "@playwright/test";
import type {
  WarrantResponse,
  WarrantTermsResponse,
} from "../../frontend/src/features/product/types/api";
import type { QuoteHistoryReport } from "../../frontend/src/features/product/types/dataEvidence";
import {
  assertDocumentReflow,
  browserMeasurements,
  contrastSample,
  nativeScreenshot,
  nativeZoomBrowser,
} from "./support/ux4-native-zoom";

// Synthetic, stored responses only. Every API request is intercepted; an unknown
// endpoint or a command fails the test instead of reaching a backend/provider.
const assessedAt = "2026-11-06T11:00:00Z";
const originalAt = "2026-10-29T14:10:00Z";
const retrievedAt = "2026-11-06T10:40:00Z";
const capturedAt = "2026-11-06T10:51:00Z";
const firstFailureAt = "2026-11-06T10:45:00Z";
const lastFailureAt = "2026-11-06T10:55:00Z";
const oldRecoveryAt = "2026-11-06T10:30:00Z";
const issuerId = "d4000000-0000-4000-8000-000000000001";
const underlyingId = "d4000000-0000-4000-8000-000000000002";
const identity = "synthetic-historical-identity-" + "a".repeat(128);
const otherIdentity = "synthetic-older-mapping-" + "b".repeat(128);
const cacheIdentity = "synthetic-cache-only-identity-" + "c".repeat(128);
const fingerprint = "d".repeat(64);
const coverageIssuer =
  "Synthetic D issuer " + "LangerEmittentennachweis".repeat(8);
const warrant: WarrantResponse = {
  id: "d4000000-0000-4000-8000-000000000003",
  workspace_id: "d4000000-0000-4000-8000-000000000004",
  issuer_id: issuerId,
  underlying_id: underlyingId,
  product_family: "WARRANT",
  display_name: "Synthetischer UX4-D Kursbeleg",
  isin: "DE000VH2LU21",
  wkn: "VH2LU2",
  lifecycle_status: "ACTIVE",
  version: 2,
  created_at: "2026-10-01T09:00:00Z",
  updated_at: assessedAt,
};
const terms: WarrantTermsResponse = {
  id: "d4000000-0000-4000-8000-000000000005",
  warrant_id: warrant.id,
  version_no: 2,
  effective_from: "2026-10-01T09:00:00Z",
  effective_to: null,
  option_direction: "CALL",
  strike: "100",
  strike_currency_code: "EUR",
  maturity_date: "2099-12-31",
  ratio: "0.1",
  created_at: "2026-10-01T09:00:00Z",
};

function historyFixture(): QuoteHistoryReport {
  const reference = {
    id: "synthetic-reference-capture",
    provider: "FRANKFURT_QUOTES",
    identity_key: identity,
    isin: warrant.isin!,
    captured_at: capturedAt,
    slot_at: "2026-11-06T10:50:00Z",
    status: "REFERENCE_ONLY",
    reason: null,
    retrieved_at: retrievedAt,
    cache_status: "HIT",
    quote_fingerprint: fingerprint,
    quote: {
      bid: null,
      ask: null,
      reference_price: "0.231234567890123456789",
      reference_price_type: "LAST_TRADE",
      observed_at: originalAt,
      currency: "EUR",
      source_mode: "OFFICIAL_WEBSITE_LAST_TRADE",
      warrant_listing_id: "synthetic-historical-listing",
      provider_symbol: warrant.isin!,
      provider_exchange_code: "FRA",
      venue_mic: "XFRA",
      quote_time_text: null,
      quote_time_basis: null,
    },
  };
  return {
    warrant_id: warrant.id,
    window_start: "2026-10-30T11:00:00Z",
    window_end: assessedAt,
    collection_started_at: "2026-10-01T09:00:00Z",
    item_limit: 50,
    sampling_policy: "FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1",
    time_coverage_percent: null,
    iv_history_available: false,
    underlying_synchronization_available: false,
    execution_usable: false,
    segments: [
      {
        provider: "FRANKFURT_QUOTES",
        identity_key: identity,
        isin: warrant.isin!,
        sampled_slots: 60,
        distinct_quote_evidence: 1,
        observed_utc_days: 1,
        first_capture_at: "2026-11-06T06:00:00Z",
        last_capture_at: capturedAt,
        statuses: { REFERENCE_ONLY: 60, REQUEST_FAILED: 0 },
      },
      {
        provider: "FRANKFURT_QUOTES",
        identity_key: otherIdentity,
        isin: warrant.isin!,
        sampled_slots: 1,
        distinct_quote_evidence: 0,
        observed_utc_days: 1,
        first_capture_at: lastFailureAt,
        last_capture_at: lastFailureAt,
        statuses: { REQUEST_FAILED: 1, TWO_SIDED_WITHIN_AGE_LIMIT: 0 },
      },
      {
        provider: "MORGAN_STANLEY",
        identity_key: "synthetic-issuer-unknown-time",
        isin: warrant.isin!,
        sampled_slots: 1,
        distinct_quote_evidence: 1,
        observed_utc_days: 1,
        first_capture_at: "2026-11-06T10:56:00Z",
        last_capture_at: "2026-11-06T10:56:00Z",
        statuses: { TIMESTAMP_UNKNOWN: 1 },
      },
    ],
    items: [
      {
        ...reference,
        id: "synthetic-unknown-original-time",
        provider: "MORGAN_STANLEY",
        identity_key: "synthetic-issuer-unknown-time",
        captured_at: "2026-11-06T10:56:00Z",
        slot_at: "2026-11-06T10:55:00Z",
        status: "TIMESTAMP_UNKNOWN",
        quote_fingerprint: "e".repeat(64),
        quote: {
          ...reference.quote,
          bid: "0.41",
          ask: null,
          reference_price: null,
          reference_price_type: null,
          observed_at: null,
          source_mode: "OFFICIAL_ISSUER_INDICATION_LOCAL_DATETIME",
          provider_exchange_code: "ISSUER",
          venue_mic: null,
          quote_time_text: "06.11.2026 11:49",
          quote_time_basis: "LOCAL_DATETIME_TIMEZONE_UNKNOWN",
        },
      },
      {
        ...reference,
        id: "synthetic-failed-capture",
        identity_key: otherIdentity,
        captured_at: lastFailureAt,
        slot_at: lastFailureAt,
        status: "REQUEST_FAILED",
        reason: "FRANKFURT_HTTP_503",
        retrieved_at: null,
        cache_status: null,
        quote_fingerprint: null,
        quote: null,
      },
      reference,
      {
        ...reference,
        id: "synthetic-repeated-original-quote",
        captured_at: "2026-11-06T10:46:00Z",
        slot_at: "2026-11-06T10:45:00Z",
      },
    ],
  };
}

function coverageFixture() {
  const route = {
    provider: "FRANKFURT_QUOTES",
    listing_id: "synthetic-coverage-listing",
    mic: "XFRA",
    currency: "EUR",
    mapping_id: "synthetic-mapping-" + "f".repeat(128),
    mapping_status: "VALIDATED",
    provider_identity: warrant.isin,
    provider_exchange_code: "FRA",
    validated_at: "2026-10-01T09:00:00Z",
    configured: true,
    route_reason: "ROUTE_IDENTITY_VERIFIED",
    observation_status: "REFERENCE_ONLY",
    bid: null,
    ask: null,
    reference_price: "0.231234567890123456789",
    reference_price_type: "LAST_TRADE",
    observed_at: originalAt,
    retrieved_at: retrievedAt,
    age_seconds: 766200,
    max_quote_age_seconds: 3600,
    feed_delay_seconds: 0,
    trading_status: "CLOSED",
    refresh_error: "FRANKFURT_HTTP_503",
    quote_time_text: null,
    quote_time_basis: null,
  };
  return {
    assessed_at: assessedAt,
    scheduler_enabled: true,
    scheduler_leader: true,
    configured_sources: ["FRANKFURT_QUOTES", "MORGAN_STANLEY"],
    source_order: ["FRANKFURT_QUOTES", "MORGAN_STANLEY", "VONTOBEL_MARKETS"],
    assessment_scope: "STORED_OBSERVATIONS_NOT_LIVE_VALUATION",
    execution_usable: false,
    items: [
      {
        warrant_id: warrant.id,
        name: warrant.display_name,
        isin: warrant.isin,
        wkn: warrant.wkn,
        issuer: coverageIssuer,
        issuer_probe_eligible: true,
        coverage: "QUOTE_TIMESTAMP_UNKNOWN",
        routes: [
          route,
          {
            ...route,
            provider: "MORGAN_STANLEY",
            listing_id: "synthetic-issuer-listing",
            mapping_id: "synthetic-issuer-mapping",
            mic: "XSTU",
            provider_exchange_code: "ISSUER",
            bid: "0.41",
            reference_price: null,
            reference_price_type: null,
            observed_at: null,
            age_seconds: null,
            max_quote_age_seconds: 0,
            trading_status: null,
            refresh_error: null,
            observation_status: "QUOTE_TIMESTAMP_UNKNOWN",
            quote_time_text: "06.11.2026 11:49",
            quote_time_basis: "LOCAL_DATETIME_TIMEZONE_UNKNOWN",
          },
          {
            ...route,
            provider: "VONTOBEL_MARKETS",
            listing_id: "synthetic-unavailable-listing",
            mapping_id: null,
            mapping_status: "DISABLED",
            provider_identity: null,
            configured: false,
            route_reason: "MAPPING_DISABLED",
            observation_status: "ROUTE_UNAVAILABLE",
            reference_price: null,
            reference_price_type: null,
            observed_at: null,
            retrieved_at: null,
            age_seconds: null,
            max_quote_age_seconds: null,
            feed_delay_seconds: null,
            trading_status: null,
            refresh_error: null,
          },
        ],
        refresh_status: "MIXED",
        refresh_reason: null,
        checked_at: assessedAt,
        next_run_at: null,
        discovery_reasons: [],
        refresh_jobs: [
          {
            lane: "ISSUER_QUOTES",
            status: "AVAILABLE",
            reason: "QUOTE_OBSERVATIONS_AVAILABLE",
            checked_at: assessedAt,
            next_run_at: null,
          },
          {
            lane: "WARRANT_QUOTES",
            status: "ERROR",
            reason: "FRANKFURT_HTTP_503",
            checked_at: lastFailureAt,
            next_run_at: null,
          },
        ],
      },
      {
        warrant_id: "d4000000-0000-4000-8000-000000000006",
        name: "Synthetisches Produkt ohne Quelle",
        isin: null,
        wkn: null,
        issuer: "Synthetic other issuer",
        issuer_probe_eligible: false,
        coverage: "NO_USABLE_ROUTE",
        routes: [],
        refresh_status: "DISABLED",
        refresh_reason: null,
        checked_at: null,
        next_run_at: null,
        discovery_reasons: [],
        refresh_jobs: [],
      },
    ],
  };
}

function refreshFixture() {
  const retained = {
    kind: "SOURCE",
    source: "FRANKFURT_QUOTES",
    listing_id: "synthetic-retained-listing",
    identity_key: identity,
    status: "AVAILABLE",
    category: "PROVIDER_ERROR",
    reason: "FRANKFURT_HTTP_503",
    consecutive_failures: 2,
    first_failure_at: firstFailureAt,
    last_failure_at: lastFailureAt,
    last_failure_reason: "FRANKFURT_HTTP_503",
    last_failure_category: "PROVIDER_ERROR",
    last_success_at: oldRecoveryAt,
    recovered_at: oldRecoveryAt,
    last_checked_at: lastFailureAt,
    attempt_started_at: "2026-11-06T10:54:00Z",
    observed_in_latest_run: true,
    retained_quote: true,
    qualified_success: false,
    quote_status: "LAST_AVAILABLE",
    quote_usable: true,
    provider_reachable: true,
    response_valid: false,
    quote_observed_at: originalAt,
    quote_retrieved_at: retrievedAt,
  };
  return {
    enabled: true,
    running: true,
    leader: true,
    last_error: null,
    settings: {
      warrants_interval_seconds: 300,
      underlyings_interval_seconds: 3600,
      discovery_interval_seconds: 3600,
    },
    jobs: [
      {
        job: "WARRANT_QUOTES:synthetic-diagnostics",
        name: "Synthetische UX4-D Providerdiagnostik",
        isin: warrant.isin,
        status: "AVAILABLE",
        reason: "QUOTE_OBSERVATIONS_AVAILABLE",
        next_run_at: null,
        checked_at: lastFailureAt,
        execution: {
          running: true,
          started_at: "2026-11-06T10:59:00Z",
          elapsed_seconds: 0,
        },
        quotes: [
          {
            provider: "FRANKFURT_QUOTES",
            warrant_listing_id: "synthetic-cache-listing",
            identity_key: cacheIdentity,
            cache_status: "HIT",
            retrieved_at: retrievedAt,
            attempt_completed_at: lastFailureAt,
          },
        ],
        diagnostics: {
          scope: "PROCESS_LOCAL",
          checks: [
            retained,
            {
              ...retained,
              source: "MORGAN_STANLEY",
              listing_id: "synthetic-historical-listing",
              identity_key: otherIdentity,
              status: "UNKNOWN",
              category: null,
              reason: null,
              consecutive_failures: 0,
              first_failure_at: null,
              last_failure_at: null,
              last_failure_reason: null,
              last_failure_category: null,
              last_success_at: null,
              recovered_at: null,
              last_checked_at: oldRecoveryAt,
              attempt_started_at: null,
              observed_in_latest_run: false,
              retained_quote: null,
              qualified_success: null,
              quote_status: "UNASSESSED",
              quote_usable: null,
              provider_reachable: null,
              response_valid: null,
              quote_observed_at: null,
              quote_retrieved_at: null,
            },
            {
              ...retained,
              source: "VONTOBEL_MARKETS",
              listing_id: "synthetic-failed-listing",
              identity_key: "synthetic-unavailable-identity",
              status: "ERROR",
              reason: "SYNTHETIC_NETWORK_ERROR",
              last_failure_reason: "SYNTHETIC_NETWORK_ERROR",
              consecutive_failures: 1,
              recovered_at: null,
              last_success_at: null,
              observed_in_latest_run: null,
              retained_quote: false,
              qualified_success: false,
              quote_status: "MISSING",
              quote_usable: false,
              provider_reachable: false,
              response_valid: false,
              quote_observed_at: null,
              quote_retrieved_at: null,
            },
          ],
        },
      },
    ],
  };
}

type Requests = {
  api: string[];
  history: string[];
  coverage: string[];
  refresh: string[];
  writes: string[];
  unexpected: string[];
  external: string[];
  browserErrors: string[];
};

async function setup(
  page: Page,
  baseURL: string | undefined,
): Promise<Requests> {
  const calls: Requests = {
    api: [],
    history: [],
    coverage: [],
    refresh: [],
    writes: [],
    unexpected: [],
    external: [],
    browserErrors: [],
  };
  const origin = new URL(baseURL ?? "http://127.0.0.1:8080").origin;
  page.on("pageerror", (error) => calls.browserErrors.push(error.message));
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    // CI serves the page at 127.0.0.1 while its configured API uses localhost.
    // Both API origins remain intercepted; only same-origin static assets pass.
    if (!url.pathname.startsWith("/api/")) {
      if (url.origin !== origin) {
        calls.external.push(request.url());
        return route.abort();
      }
      return route.continue();
    }
    const path = url.pathname.replace(/^\/api(?:\/api)?\/v1/, "");
    const key = `${request.method()} ${path}${url.search}`;
    calls.api.push(key);
    if (request.method() !== "GET") {
      calls.writes.push(key);
      return route.fulfill({
        status: 405,
        json: { message: "Synthetic read-only fixture" },
      });
    }
    if (path === `/market-data/warrants/${warrant.id}/quote-history`) {
      calls.history.push(url.search);
      return route.fulfill({ json: historyFixture() });
    }
    if (path === "/market-data/warrants/quote-coverage") {
      calls.coverage.push(key);
      return route.fulfill({ json: coverageFixture() });
    }
    if (path === "/market-data/refresh/status") {
      calls.refresh.push(key);
      return route.fulfill({ json: refreshFixture() });
    }
    if (path === "/operational-workspace/actions")
      return route.fulfill({ json: { generated_at: assessedAt, actions: [] } });
    if (path === "/operational-workspace/positions")
      return route.fulfill({
        json: { generated_at: assessedAt, positions: [] },
      });
    if (path === "/market-reference-data/issuers")
      return route.fulfill({
        json: {
          items: [
            {
              id: issuerId,
              legal_name: "Synthetic D issuer AG",
              display_name: "Synthetic D issuer",
              country_code: "DE",
              lei: null,
            },
          ],
        },
      });
    if (path === "/market-reference-data/trading-venues")
      return route.fulfill({ json: { items: [] } });
    if (path === "/market-reference-data/currencies")
      return route.fulfill({
        json: {
          items: [
            {
              code: "EUR",
              name: "Euro",
              minor_unit: 2,
              reference_version: "synthetic",
            },
          ],
        },
      });
    if (path === "/underlyings")
      return route.fulfill({
        json: {
          items: [
            {
              id: underlyingId,
              type: "STOCK",
              name: "Synthetic D underlying",
              isin: null,
              wkn: null,
              lifecycle_status: "ACTIVE",
              quality_status: "COMPLETE",
              version: 1,
              created_at: assessedAt,
              updated_at: assessedAt,
              primary_listing: null,
            },
          ],
          total: 1,
          offset: 0,
          limit: 100,
        },
      });
    if (path === "/warrants") return route.fulfill({ json: [warrant] });
    if (path === `/warrants/${warrant.id}`)
      return route.fulfill({ json: warrant });
    if (path === `/warrants/${warrant.id}/terms`)
      return route.fulfill({ json: [terms] });
    if (path === `/warrants/${warrant.id}/listings`)
      return route.fulfill({ json: [] });
    calls.unexpected.push(key);
    return route.fulfill({
      status: 500,
      json: { message: "Unexpected synthetic API request" },
    });
  });
  return calls;
}

function field(scope: Locator, label: string) {
  return scope.getByText(label, { exact: true }).locator("..").locator("dd");
}

async function visibleFocus(target: Locator) {
  await expect(target).toBeFocused();
  expect(
    await target.evaluate((element) => {
      const style = getComputedStyle(element);
      return (
        element.matches(":focus-visible") &&
        style.outlineStyle !== "none" &&
        parseFloat(style.outlineWidth) >= 2
      );
    }),
  ).toBe(true);
}

async function openDetails(
  page: Page,
  summary: Locator,
  key: "Enter" | "Space" = "Enter",
) {
  await summary.focus();
  if ((await summary.locator("..").getAttribute("open")) === null)
    await page.keyboard.press(key);
  await expect(summary.locator("..")).toHaveAttribute("open", "");
}

async function openHistory(page: Page, calls: Requests) {
  await expect(
    page.getByRole("article", {
      name: `Produktdetails ${warrant.display_name}`,
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  const summary = page.getByText(
    "Kursdaten-Verfügbarkeit und Erfassungsprotokoll",
    { exact: true },
  );
  await openDetails(page, summary);
  await visibleFocus(summary);
  expect(calls.history).toEqual([]);
  await page.keyboard.press("Tab");
  const select = page.getByRole("combobox", {
    name: "Beobachtungsfenster",
    exact: true,
  });
  await expect(select).toBeFocused();
  await page.keyboard.press("Tab");
  const button = page.getByRole("button", {
    name: "Gespeichertes Protokoll laden",
    exact: true,
  });
  await expect(button).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(select).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  const report = page.getByRole("region", {
    name: "Gespeicherte Kursbeobachtungen",
    exact: true,
  });
  await expect(report).toBeVisible();
  expect(calls.history).toEqual(["?days=7"]);
  return report;
}

async function inspectHistory(page: Page, report: Locator) {
  await expect(
    field(report, "Erste bekannte Produkterfassung (UTC)"),
  ).toHaveText("2026-10-01T09:00:00Z");
  await expect(field(report, "Zeitabdeckungsquote")).toHaveText(
    "nicht verfügbar",
  );
  await expect(
    report.getByText(
      /Eine Anzahl erwarteter oder aus einer Kurshistorie ausgeschlossener Kurspunkte/,
    ),
  ).toBeVisible();
  const segments = report.getByRole("article");
  await expect(segments).toHaveCount(3);
  await expect(field(segments.nth(0), "Erfasste Intervalle")).toHaveText(
    "60 UTC-Slots",
  );
  await expect(
    field(segments.nth(0), "Unterschiedliche Kursbelege"),
  ).toHaveText("1 Kursbeleg");
  await expect(
    field(segments.nth(1), "Unterschiedliche Kursbelege"),
  ).toHaveText("0 Kursbelege");
  const statuses = segments
    .nth(1)
    .getByText("Statuszahlen dieses Quellsegments", { exact: true });
  await openDetails(page, statuses, "Space");
  await page.keyboard.press("Enter");
  await expect(segments.nth(1).getByRole("table")).toBeHidden();
  await page.keyboard.press("Space");
  await visibleFocus(statuses);
  const table = segments.nth(1).getByRole("table");
  await expect(
    table.getByRole("columnheader", { name: "Anzahl Intervalle" }),
  ).toBeVisible();
  await expect(
    table.getByRole("row", { name: /TWO_SIDED_WITHIN_AGE_LIMIT 0/ }),
  ).toBeVisible();
  const summary = report.getByText(
    "Erfassungsbelege mit Originalzeiten (4 geliefert)",
    { exact: true },
  );
  await openDetails(page, summary);
  await expect(
    report.getByText(/Höchstens 50 zuletzt erfasste Beobachtungen/),
  ).toContainText("über alle Quellsegmente zusammen");
  const observations = report
    .getByRole("list", {
      name: "Einzelne gespeicherte Erfassungsbelege",
      exact: true,
    })
    .getByRole("listitem");
  await expect(observations).toHaveCount(4);
  const unknown = observations.nth(0);
  await expect(field(unknown, "Originalkurszeit (UTC)")).toHaveText(
    "unbekannt",
  );
  await expect(
    field(unknown, "Originalzeittext der Quelle (unverändert)"),
  ).toHaveText("06.11.2026 11:49");
  await expect(field(unknown, "Zeitbasis der Quelle")).toHaveText(
    "LOCAL_DATETIME_TIMEZONE_UNKNOWN",
  );
  await expect(field(unknown, "Briefkurs (ASK)")).toHaveText("nicht vorhanden");
  await expect(field(unknown, "Handelsplatz (MIC)")).toHaveText(
    "nicht übermittelt",
  );
  const failure = observations.nth(1);
  await expect(failure).toContainText(
    "Kein Kursbeleg für diese Erfassung gespeichert.",
  );
  await expect(failure).toContainText("FRANKFURT_HTTP_503");
  await expect(field(failure, "Quellsegment / Identität")).toHaveText(
    otherIdentity,
  );
  const reference = observations.nth(2);
  await expect(
    field(reference, "Originalkurszeit (UTC)").locator("time"),
  ).toHaveAttribute("datetime", originalAt);
  await expect(
    field(reference, "Erfassungszeit (UTC)").locator("time"),
  ).toHaveAttribute("datetime", capturedAt);
  await expect(
    field(reference, "Abrufzeit (UTC)").locator("time"),
  ).toHaveAttribute("datetime", retrievedAt);
  await expect(field(reference, "Referenzkurs")).toHaveText(
    "0.231234567890123456789",
  );
  await expect(field(reference, "Referenz-Preisart")).toContainText(
    "LAST_TRADE",
  );
  await expect(field(reference, "Währung der Preise")).toHaveText("EUR");
  await expect(field(reference, "Handelsplatz (MIC)")).toHaveText("XFRA");
  await expect(field(reference, "Kursbeleg-Fingerprint")).toHaveText(
    fingerprint,
  );
  await expect(field(observations.nth(3), "Kursbeleg-Fingerprint")).toHaveText(
    fingerprint,
  );
  await expect(report.locator("[aria-live]")).toHaveCount(0);
  await assertDocumentReflow(page);
  return unknown;
}

async function openWorkspace(page: Page, calls: Requests) {
  await expect(
    page.getByRole("heading", {
      name: "Was benötigt jetzt deine Aufmerksamkeit?",
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  const summary = page.getByText("Automatischer Kursabruf", { exact: true });
  await openDetails(page, summary);
  await visibleFocus(summary);
  expect(calls.coverage).toEqual([]);
  expect(calls.refresh).toEqual([]);
  return summary.locator("..");
}

async function openCoverage(page: Page, calls: Requests) {
  await openWorkspace(page, calls);
  const panel = page.getByRole("region", {
    name: "Kursquellen im Depot",
    exact: true,
  });
  const button = panel.getByRole("button", {
    name: "Kursquellen im Depot prüfen",
    exact: true,
  });
  await button.focus();
  await page.keyboard.press("Space");
  await expect(
    panel.getByRole("rowheader").filter({ hasText: warrant.display_name }),
  ).toBeVisible();
  expect(calls.coverage).toHaveLength(1);
  expect(calls.refresh).toEqual([]);
  return panel;
}

async function inspectCoverage(page: Page, panel: Locator) {
  await expect(panel).toContainText("2 gehaltene Optionsscheine");
  await expect(panel).toContainText("Produkte, keine Positionen oder Kurse");
  await expect(field(panel, "Prüfumfang")).toHaveText(
    "STORED_OBSERVATIONS_NOT_LIVE_VALUATION",
  );
  await expect(
    field(panel, "Ausführungsverwendbarkeit (execution_usable)"),
  ).toHaveText("false");
  const config = panel.getByText("Quellenkonfiguration des Prüfstands", {
    exact: true,
  });
  await openDetails(page, config);
  await expect(
    panel.getByText("VONTOBEL_MARKETS: nicht konfiguriert", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  const issuer = panel.getByRole("combobox", {
    name: "Kursquellen nach Emittent",
    exact: true,
  });
  await expect(issuer).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await visibleFocus(config);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const gaps = panel.getByRole("checkbox", {
    name: "Nur Prüfbedarf",
    exact: true,
  });
  await expect(gaps).toBeFocused();
  if (!(await gaps.isChecked())) await page.keyboard.press("Space");
  await visibleFocus(gaps);
  await issuer.selectOption(coverageIssuer);
  await expect(panel.getByRole("rowheader")).toHaveCount(1);
  await expect(panel).toContainText("2 gehaltene Optionsscheine");
  await issuer.selectOption("");
  const row = panel.getByRole("row").filter({ hasText: warrant.display_name });
  const summary = row.getByText("Kurswege (3)", { exact: true });
  await openDetails(page, summary, "Space");
  await visibleFocus(summary);
  const reference = row
    .getByRole("heading", {
      name: "FRANKFURT_QUOTES · XFRA · EUR",
      exact: true,
    })
    .locator("..");
  await expect(reference).toContainText("Geld: nicht vorhanden");
  await expect(reference).toContainText("Brief: nicht vorhanden");
  await expect(reference).toContainText("0.231234567890123456789 EUR");
  await expect(reference).toContainText(
    "Kursalter am Prüfstand: 766200 Sekunden",
  );
  await expect(reference).toContainText("Quellenverzögerung: 0 Sekunden");
  await expect(reference).toContainText(
    "aktueller Providererfolg nicht bestätigt",
  );
  await expect(field(reference, "Mapping-ID")).toHaveText(
    "synthetic-mapping-" + "f".repeat(128),
  );
  const unknown = row
    .getByRole("heading", {
      name: "MORGAN_STANLEY · Emittentenindikation · EUR",
      exact: true,
    })
    .locator("..");
  await expect(unknown).toContainText("Kurszeit: Unbekannt");
  await expect(unknown).toContainText("Originalzeittext: 06.11.2026 11:49");
  await expect(unknown).toContainText(
    "Zeitbasis der Quelle: LOCAL_DATETIME_TIMEZONE_UNKNOWN",
  );
  await expect(unknown).toContainText("Kursalter am Prüfstand: Unbekannt");
  await expect(unknown).toContainText("Altersgrenze laut Quelle: 0 Sekunden");
  const unavailable = row
    .getByRole("heading", {
      name: "VONTOBEL_MARKETS · XFRA · EUR",
      exact: true,
    })
    .locator("..");
  await expect(unavailable).toContainText("Provider nicht konfiguriert");
  await expect(unavailable).toContainText("Zuordnung ausdrücklich deaktiviert");
  await expect(unavailable).toContainText("Quellenverzögerung: unbekannt");
  const empty = panel
    .getByRole("row")
    .filter({ hasText: "Synthetisches Produkt ohne Quelle" });
  await openDetails(page, empty.getByText("Kurswege (0)", { exact: true }));
  await expect(empty).toContainText(
    "Keine passende gespeicherte Notierung oder Providerzuordnung.",
  );
  const scroll = panel.getByRole("region", {
    name: "Kursabdeckung je Produkt, horizontal scrollbar",
    exact: true,
  });
  await expect(scroll.getByRole("table")).toHaveAccessibleName(
    "Verifizierte Kurswege gehaltener Optionsscheine",
  );
  await expect(scroll.getByRole("columnheader")).toHaveCount(3);
  await scroll.focus();
  await page.keyboard.press("Shift+Tab");
  await expect(gaps).toBeFocused();
  await page.keyboard.press("Tab");
  await visibleFocus(scroll);
  if (
    await scroll.evaluate(
      (element) => element.scrollWidth > element.clientWidth,
    )
  ) {
    await scroll.evaluate((element) => {
      element.scrollLeft = 0;
    });
    await page.keyboard.press("ArrowRight");
    await expect
      .poll(() => scroll.evaluate((element) => element.scrollLeft))
      .toBeGreaterThan(0);
  }
  await assertDocumentReflow(page);
  await config.focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  await visibleFocus(config);
  return reference;
}

async function openDiagnostics(page: Page, calls: Requests) {
  const panel = await openWorkspace(page, calls);
  const button = panel.getByRole("button", {
    name: "Abrufstatus laden",
    exact: true,
  });
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(
    panel.getByText(/Synthetische UX4-D Providerdiagnostik/),
  ).toBeVisible();
  expect(calls.refresh).toHaveLength(1);
  expect(calls.coverage).toEqual([]);
  return panel;
}

async function inspectDiagnostics(page: Page, panel: Locator) {
  await expect(panel.getByText(/Aktueller Abruf · Start:/)).toContainText(
    "bisher 0 Sek.",
  );
  const summary = panel.getByText("Diagnose · 3 Abrufnachweise", {
    exact: true,
  });
  await openDetails(page, summary);
  const evidence = panel.getByRole("list", {
    name: "Abgeschlossene Diagnosebelege",
    exact: true,
  });
  await expect(evidence.getByRole("listitem")).toHaveCount(3);
  const retained = evidence.getByRole("listitem").filter({
    has: page.getByRole("heading", { name: "FRANKFURT_QUOTES", exact: true }),
  });
  await expect(retained).toContainText(`Quellenidentität: ${identity}`);
  await expect(retained).not.toContainText(cacheIdentity);
  for (const text of [
    "Provider technisch erreichbar: Ja",
    "Antwort gültig: Nein",
    "Kurs verwendbar: Ja",
    "Qualifizierter Erfolg dieser Prüfung: Nein",
    "Gespeicherter Ersatzkurs: Ja",
    "Providerfehler · 2 Prüfungen in Folge mit Befund",
    "Die gemeldete Fehlerfolge bleibt bestehen.",
  ])
    await expect(retained).toContainText(text);
  await expect(
    retained.locator(`time[datetime="${originalAt}"]`),
  ).toBeVisible();
  await expect(
    retained.locator(`time[datetime="${retrievedAt}"]`),
  ).toBeVisible();
  await expect(retained).not.toContainText("Kursversorgung wiederhergestellt");
  const historical = evidence.getByRole("listitem").filter({
    has: page.getByRole("heading", { name: "MORGAN_STANLEY", exact: true }),
  });
  for (const text of [
    "Historischer Beleg · In letzter Prüfung nicht erneut geprüft.",
    "Provider technisch erreichbar: Nicht belegt",
    "Antwort gültig: Nicht belegt",
    "Kurs verwendbar: Nicht belegt",
    "Gespeicherter Ersatzkurs: Nicht belegt",
    "0 Prüfungen in Folge mit Befund.",
  ])
    await expect(historical).toContainText(text);
  const failed = evidence.getByRole("listitem").filter({
    has: page.getByRole("heading", { name: "VONTOBEL_MARKETS", exact: true }),
  });
  await expect(failed).toContainText("Provider technisch erreichbar: Nein");
  await expect(failed).toContainText("Kurs verwendbar: Nein");
  await expect(failed).toContainText(
    "Zuordnung zum letzten abgeschlossenen Lauf nicht belegt.",
  );
  await expect(panel).toContainText("keinen dauerhaften Verfügbarkeitsverlauf");
  await summary.focus();
  await page.keyboard.press("Space");
  await expect(evidence).toBeHidden();
  await page.keyboard.press("Enter");
  await visibleFocus(summary);
  await page.keyboard.press("Tab");
  const cache = panel.getByText(
    "Cachebelege des letzten abgeschlossenen Laufs",
    { exact: true },
  );
  await expect(cache).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(summary).toBeFocused();
  await page.keyboard.press("Tab");
  if ((await cache.locator("..").getAttribute("open")) === null)
    await page.keyboard.press("Space");
  await visibleFocus(cache);
  const cacheList = panel.getByRole("list", {
    name: "Gelieferte Cachebelege",
    exact: true,
  });
  await expect(cacheList).toContainText("Cachetreffer · HIT");
  await expect(cacheList).toContainText(cacheIdentity);
  await expect(cacheList).not.toContainText(identity);
  await assertDocumentReflow(page);
  return retained;
}

function noSideEffects(calls: Requests, before: string[]) {
  expect(calls.api).toEqual(before);
  expect(calls.writes).toEqual([]);
  expect(calls.unexpected).toEqual([]);
  expect(calls.external).toEqual([]);
  expect(calls.browserErrors).toEqual([]);
}

async function attachEvidence(
  page: Page,
  panel: Locator,
  testInfo: TestInfo,
  name: string,
  calls: Requests,
  native?: BrowserContext,
) {
  const focused = panel.locator(":focus");
  await visibleFocus(focused);
  const contrast = await contrastSample(focused);
  expect(contrast.textRatio).toBeGreaterThanOrEqual(4.5);
  expect(contrast.focusRatio).toBeGreaterThanOrEqual(3);
  await testInfo.attach(`${name}-semantics.yml`, {
    body: Buffer.from(await panel.ariaSnapshot()),
    contentType: "text/yaml",
  });
  await testInfo.attach(`${name}-measurements.json`, {
    body: Buffer.from(
      JSON.stringify(
        {
          ...(await browserMeasurements(page)),
          contrast,
          requests: calls,
          scope:
            "Synthetic stored fixtures; accessibility tree is not a human screenreader acceptance.",
        },
        null,
        2,
      ),
    ),
    contentType: "application/json",
  });
  if (native) {
    await nativeScreenshot(native, page, testInfo, `${name}.png`);
    await focused.evaluate((element) =>
      element.scrollIntoView({ block: "center" }),
    );
    await nativeScreenshot(native, page, testInfo, `${name}-focus.png`);
  } else
    await testInfo.attach(`${name}.png`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
}

const surfaces = [
  {
    id: "D1",
    path: "/warrants-admin",
    open: openHistory,
    inspect: inspectHistory,
  },
  {
    id: "D2",
    path: "/workspace",
    open: openCoverage,
    inspect: inspectCoverage,
  },
  {
    id: "D3",
    path: "/workspace",
    open: openDiagnostics,
    inspect: inspectDiagnostics,
  },
] as const;

for (const width of [320, 390, 1280]) {
  for (const surface of surfaces) {
    test(`UX4-${surface.id} stored quality, keyboard and semantic evidence at ${width}px`, async ({
      page,
      baseURL,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      const calls = await setup(page, baseURL);
      await page.goto(surface.path);
      const panel = await surface.open(page, calls);
      const before = [...calls.api];
      await surface.inspect(page, panel);
      noSideEffects(calls, before);
      await attachEvidence(
        page,
        panel,
        testInfo,
        `ux4-${surface.id.toLowerCase()}-${width}-synthetic`,
        calls,
      );
    });
  }
}

for (const surface of surfaces) {
  test(`UX4-${surface.id} evidence at native Chromium 200% and 400% page zoom`, async ({
    baseURL,
  }, testInfo) => {
    test.setTimeout(90_000);
    const { context, page, setZoom } = await nativeZoomBrowser(testInfo);
    try {
      const calls = await setup(page, baseURL);
      await page.goto((baseURL ?? "http://127.0.0.1:8080") + surface.path);
      const panel = await surface.open(page, calls);
      const before = [...calls.api];
      for (const factor of [2, 4]) {
        const measurements = await setZoom(factor);
        const target = await surface.inspect(page, panel);
        await target.evaluate((element) =>
          element.scrollIntoView({ block: "center" }),
        );
        await assertDocumentReflow(page);
        noSideEffects(calls, before);
        await testInfo.attach(
          `ux4-${surface.id.toLowerCase()}-native-${factor * 100}-zoom.json`,
          {
            body: Buffer.from(JSON.stringify(measurements, null, 2)),
            contentType: "application/json",
          },
        );
        await attachEvidence(
          page,
          panel,
          testInfo,
          `ux4-${surface.id.toLowerCase()}-native-${factor * 100}-synthetic`,
          calls,
          context,
        );
      }
    } finally {
      await context.close();
    }
  });
}
