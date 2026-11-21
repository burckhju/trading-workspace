import {
  expect,
  test,
  type Locator,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

import type {
  MonitoringRuntimeStatusResponse,
  PositionMonitoringHealthResponse,
} from "../../frontend/src/features/alert/types/api";
import { indicativeReport } from "../../frontend/src/features/operational_workspace/test/indicativeEntryFixture";
import type {
  OperationalAction,
  OperationalPosition,
} from "../../frontend/src/features/operational_workspace/types";
import { position } from "../../frontend/src/test/positionFixture";
import { watchlistFixture } from "../../frontend/src/test/watchlistFixtures";
import { readonlyPositionDetail } from "./support/readonly-position-detail";

// Router/layout qualification only. All API responses are synthetic GET
// projections. Every mutation, unknown API read and external request is blocked.
// Purchase, review and journal persistence remain in their existing owner journeys.
test.use({ timezoneId: "Europe/Berlin", serviceWorkers: "block" });

const now = "2026-11-18T15:31:00Z";
const syntheticId = (group: number, index: number) =>
  `${group}0000000-0000-4000-8000-${String(index).padStart(12, "0")}`;

const positions: OperationalPosition[] = Array.from(
  { length: 35 },
  (_, index) => {
    const number = index + 1;
    const dax = number <= 32 || number === 35;
    const tradeId = syntheticId(1, number);
    const positionId = syntheticId(2, number);
    // A matching, qualified row proves that the data filter changes results,
    // rather than merely preserving the selected filter button.
    if (number === 35) {
      const healthy = position();
      return position({
        trade_id: tradeId,
        position_id: positionId,
        product_id: syntheticId(3, number),
        product_name: "DAX Call 35 · Synthetisches Beispiel mit Kursbeleg",
        product_wkn: "SYN035",
        product_isin: null,
        underlying_name: "DAX · Synthetisches Beispiel",
        target: `/trade-management?trade_id=${tradeId}`,
        position_signal: {
          ...healthy.position_signal!,
          trade_id: tradeId,
          position_id: positionId,
        },
      });
    }
    return position({
      trade_id: tradeId,
      position_id: positionId,
      product_id: syntheticId(3, number),
      product_name: `${dax ? "DAX" : "Anderer Basiswert"} Call ${String(number).padStart(2, "0")} · Synthetisches Beispiel`,
      product_isin: null,
      product_wkn: `SYN${String(number).padStart(3, "0")}`,
      underlying_id: syntheticId(4, dax ? 1 : 2),
      underlying_name: dax
        ? "DAX · Synthetisches Beispiel"
        : "Anderer synthetischer Basiswert",
      underlying_symbol: dax ? "SYNTHETIC.DAX" : "SYNTHETIC.OTHER",
      product_symbol: null,
      monitoring_status: "MISSING",
      valuation_status: "MISSING",
      market_value: null,
      unrealized_gross_pnl: null,
      unrealized_pnl_usable: false,
      unrealized_pnl_reason: "WARRANT_QUOTE_MISSING",
      quote_observed_at: null,
      quote_source: null,
      attention_state: "DATA_HEALTH",
      stop_price: null,
      target_price: null,
      target: `/trade-management?trade_id=${tradeId}`,
      position_signal: {
        trade_id: tradeId,
        position_id: positionId,
        alert_level: null,
        attention_required: false,
        quality_status: "MISSING",
        reason: "SYNTHETIC_QUOTE_MISSING",
        candidate_stop: null,
        latest_price: null,
        phase: null,
        policy_version: "V1",
        dynamic_stop_policy_version: "V1",
        analysis_run_id: null,
      },
    });
  },
);

const selected = positions[31];
const tradePath = `/trade-position/trades/${selected.trade_id}`;
const monitoringPath = `/position-monitoring/trades/${selected.trade_id}`;
const quoteProblem =
  "Synthetischer Datenbefund: Kursbeleg fehlt. Bewertung und kursabhängige Überwachung sind eingeschränkt.";
const actions: OperationalAction[] = [
  {
    id: "synthetic-position-data",
    source_feature: "position_monitoring",
    action_type: "POSITION_DATA_HEALTH",
    priority: "ACTION",
    state: "ACTIONABLE",
    title: "Kursbeleg für das synthetische DAX-Beispiel prüfen",
    detail: quoteProblem,
    resource_type: "TRADE",
    resource_id: selected.trade_id,
    next_action: "Überwachung und Datenlage öffnen",
    target: `${selected.target}#trade-risk`,
    occurred_at: now,
    product_id: selected.product_id,
    product_name: selected.product_name,
    product_wkn: selected.product_wkn,
    product_isin: null,
  },
  {
    id: "synthetic-exit-review",
    source_feature: "post_trade",
    action_type: "EXIT_REVIEW",
    priority: "REVIEW",
    state: "ACTIONABLE",
    title: "Synthetischen Vollabschluss nachbereiten",
    detail:
      "Ein vorhandener abgeschlossener Beispieltrade wartet auf seine Exit-Bewertung.",
    resource_type: "TRADE",
    resource_id: syntheticId(1, 90),
    next_action: "Exit Review öffnen",
    target: `/post-trade?trade_id=${syntheticId(1, 90)}#post-trade-review`,
    occurred_at: now,
    product_name: "Abgeschlossener Call · Synthetisches Beispiel",
  },
  {
    id: "synthetic-incomplete-selection",
    source_feature: "product_selection",
    action_type: "INITIAL_PURCHASE",
    priority: "BLOCKED",
    state: "BLOCKED",
    title: "Synthetische Produktauswahl vervollständigen",
    detail:
      "Die bestehende Produktbewertung hat noch keine ausdrückliche Produktauswahl.",
    resource_type: "TRADE_PLAN",
    resource_id: syntheticId(5, 1),
    next_action: "Produktsichtung öffnen",
    target: `/product-selection?trade_plan_id=${syntheticId(5, 1)}`,
    occurred_at: now,
    product_name: "Handelsvorbereitung · Synthetisches Beispiel",
  },
];

const runtime: MonitoringRuntimeStatusResponse = {
  enabled: false,
  running: false,
  cycle_running: false,
  interval_seconds: 300,
  scope: "PROCESS_LOCAL_ALL_WORKSPACES",
  price_basis: "EXPLICIT_INSTRUMENT_AND_CURRENCY",
  review_scope: "DISABLED",
  review_notifications_enabled: false,
  last_cycle_started_at: null,
  last_cycle_completed_at: null,
  next_run_at: null,
  last_error: null,
  last_error_at: null,
  last_result: null,
};

const health: PositionMonitoringHealthResponse = {
  trade_id: selected.trade_id,
  position_id: selected.position_id,
  status: "MISSING",
  reason: "SYNTHETIC_COMPLETED_UNDERLYING_PRICE_MISSING",
  symbol: selected.underlying_symbol,
  trading_date: null,
  market_data_observed_at: null,
  age_days: null,
  basis: null,
  daily_price: null,
};

type ReadAudit = {
  reads: string[];
  completedReads: string[];
  writes: string[];
  unexpected: string[];
  browserErrors: string[];
};
const audits = new WeakMap<Page, ReadAudit>();

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    headers: {
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
    },
    body: JSON.stringify(body),
  });
}

async function installReadonlyFixture(
  page: Page,
  baseURL: string,
): Promise<ReadAudit> {
  const audit: ReadAudit = {
    reads: [],
    completedReads: [],
    writes: [],
    unexpected: [],
    browserErrors: [],
  };
  audits.set(page, audit);
  page.on("pageerror", (error) => audit.browserErrors.push(error.message));
  const frontend = new URL(baseURL);
  const configuredApi = new URL(
    process.env.E2E_VITE_API_BASE_URL ??
      process.env.VITE_API_BASE_URL ??
      `http://localhost:${process.env.E2E_FRONTEND_PORT ?? (frontend.port || "8080")}/api`,
  );
  const apiPrefix = configuredApi.pathname.replace(/\/$/, "") + "/api/v1";
  page.on("requestfinished", (request) => {
    const url = new URL(request.url());
    if (
      request.method() === "GET" &&
      url.origin === configuredApi.origin &&
      url.pathname.startsWith(apiPrefix + "/")
    )
      audit.completedReads.push(
        url.pathname.slice(apiPrefix.length) + url.search,
      );
  });
  const detailPaths = new Set([
    tradePath,
    `${tradePath}/position`,
    `${tradePath}/management`,
    `${tradePath}/timeline`,
    `/warrants/${selected.product_id}`,
  ]);
  const unavailablePositionReads = new Set([
    `${tradePath}/hebeltrader-evidence`,
    `${monitoringPath}/hebeltrader-targets`,
    `${monitoringPath}/hebeltrader-sessions`,
    `${monitoringPath}/hebeltrader-original-bid`,
    `${monitoringPath}/hebeltrader-loss`,
  ]);
  await page.context().routeWebSocket("**/*", async (socket) => {
    audit.unexpected.push(`WebSocket ${socket.url()}`);
    await socket.close({
      code: 1008,
      reason: "Read-only navigation fixture has no sockets",
    });
  });
  await page.context().route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const requestLabel = `${request.method()} ${url.origin}${url.pathname}${url.search}`;
    if (request.method() !== "GET") {
      audit.writes.push(requestLabel);
      return json(
        route,
        { message: "Unexpected write in read-only navigation fixture" },
        405,
      );
    }
    if (
      url.origin === configuredApi.origin &&
      url.pathname.startsWith(apiPrefix + "/")
    ) {
      const path = url.pathname.slice(apiPrefix.length);
      const query = url.searchParams;
      audit.reads.push(path + url.search);
      if (path === "/operational-workspace/actions" && !url.search)
        return json(route, { generated_at: now, actions });
      if (path === "/operational-workspace/positions" && !url.search)
        return json(route, { generated_at: now, positions });
      const signalPosition = positions.find(
        (item) =>
          path ===
          `/position-monitoring/trades/${item.trade_id}/alert-projection`,
      );
      if (signalPosition && !url.search)
        return json(route, signalPosition.position_signal);
      if (detailPaths.has(path) && !url.search) {
        const projection = readonlyPositionDetail(path, [selected]);
        if (projection !== undefined) return json(route, projection);
      }
      if (path === `${monitoringPath}/product-valuation` && !url.search) {
        const projection = readonlyPositionDetail(path, [selected]);
        if (projection !== undefined) return json(route, projection);
      }
      if (path === `/alerts/trades/${selected.trade_id}` && !url.search)
        return json(route, []);
      if (path === `${monitoringPath}/health` && !url.search)
        return json(route, health);
      if (path === "/position-monitoring/runtime/status" && !url.search)
        return json(route, runtime);
      if (
        path === `${monitoringPath}/indicative-entry` &&
        query.size === 1 &&
        query.get("position_id") === selected.position_id
      )
        return json(
          route,
          indicativeReport({
            trade_id: selected.trade_id,
            position_id: selected.position_id,
          }),
        );
      if (path === `${tradePath}/price-history` && !url.search)
        return json(route, {
          trade_id: selected.trade_id,
          position_id: selected.position_id,
          warrant_id: selected.product_id,
          isin: null,
          window_start: null,
          window_end: now,
          sampling_policy: "FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1",
          sample_limit: 10000,
          samples_considered: 0,
          samples_available: 0,
          truncated: false,
          collection_started_at: null,
          excluded: {},
          series: [],
          events: [],
        });
      if (
        path === `${tradePath}/execution-currency-preview` &&
        query.size === 3 &&
        ["BUY", "SELL"].includes(query.get("side") ?? "") &&
        /^\d{4}-\d{2}-\d{2}$/.test(query.get("executed_on") ?? "") &&
        query.get("execution_timezone") === "Europe/Berlin"
      )
        return json(route, {
          currency_code: null,
          source: "UNKNOWN",
          source_execution_ids: [],
          confirmation_ids: [],
          evidence_ids: [],
          evidence: [],
          reason: "SYNTHETIC_NO_EXECUTION_CURRENCY_EVIDENCE",
        });
      // These mounted, collapsed readers are deliberately unavailable in this
      // narrow fixture. A known 503 is not an invented successful domain report.
      if (
        (path === `${monitoringPath}/risk` && !url.search) ||
        (unavailablePositionReads.has(path) &&
          query.size === 1 &&
          query.get("position_id") === selected.position_id)
      )
        return json(
          route,
          {
            code: "SYNTHETIC_READ_UNAVAILABLE",
            message:
              "Dieser zusätzliche Prüfstand ist in der synthetischen Navigation nicht verfügbar.",
            details: [],
            timestamp: now,
          },
          503,
        );
      if (path === "/market-charts/watchlist" && !url.search)
        return json(route, watchlistFixture(1, false));
      if (
        path === "/underlyings" &&
        query.size === 2 &&
        query.get("offset") === "0" &&
        query.get("limit") === "25"
      )
        return json(route, { items: [], total: 0, offset: 0, limit: 25 });
      if (
        [
          "/market-reference-data/trading-venues",
          "/market-reference-data/currencies",
        ].includes(path) &&
        !url.search
      )
        return json(route, { items: [] });
      if (path === "/market-data/refresh/status" && !url.search)
        return json(route, {
          enabled: true,
          running: false,
          leader: true,
          last_error: null,
          settings: {
            warrants_interval_seconds: 300,
            underlyings_interval_seconds: 3600,
            discovery_interval_seconds: 3600,
            auto_select_position_sources: false,
            auto_discover_issuer_routes: false,
          },
          jobs: [
            {
              job: "WARRANT_QUOTES:synthetic-navigation",
              name: selected.product_name,
              isin: null,
              held: true,
              status: "MISSING",
              reason: "SYNTHETIC_QUOTE_MISSING",
              next_run_at: null,
              diagnostics: {
                scope: "PROCESS_LOCAL",
                checks: [
                  {
                    kind: "SOURCE",
                    source: "SYNTHETIC_PROVIDER",
                    listing_id: "synthetic-listing",
                    status: "MISSING",
                    category: "NO_QUOTE",
                    reason: "SYNTHETIC_QUOTE_MISSING",
                    consecutive_failures: 1,
                    first_failure_at: now,
                    last_failure_at: now,
                    recovered_at: null,
                    last_checked_at: now,
                    qualified_success: false,
                    retained_quote: false,
                    quote_status: "MISSING",
                    quote_observed_at: null,
                    quote_retrieved_at: null,
                    quote_usable: false,
                    provider_reachable: true,
                    response_valid: true,
                    observed_in_latest_run: true,
                  },
                ],
              },
            },
          ],
        });
      audit.unexpected.push(requestLabel);
      return json(
        route,
        { message: "Unknown API read in navigation fixture" },
        500,
      );
    }
    if (
      url.origin === frontend.origin &&
      (request.resourceType() === "document" ||
        url.pathname === "/favicon.ico" ||
        ["script", "stylesheet", "font", "image", "manifest"].includes(
          request.resourceType(),
        )) &&
      !url.pathname.includes("/api/")
    )
      return route.continue();
    audit.unexpected.push(requestLabel);
    await route.abort("blockedbyclient");
  });
  return audit;
}

test.afterEach(async ({ page }, testInfo) => {
  const audit = audits.get(page);
  if (!audit) return;
  await testInfo.attach("read-only-navigation-requests", {
    body: JSON.stringify(audit, null, 2),
    contentType: "application/json",
  });
  expect(
    audit.writes,
    "No domain writes may leave this navigation journey",
  ).toEqual([]);
  expect(
    audit.unexpected,
    "Every read must have an explicit synthetic fixture",
  ).toEqual([]);
  expect(
    audit.browserErrors,
    "The real application must render without page errors",
  ).toEqual([]);
  expect(
    [...audit.completedReads].sort(),
    "Every started synthetic read must finish before leaving its owner",
  ).toEqual([...audit.reads].sort());
});

async function finishPresentation(page: Page) {
  // Cross a painted frame and the following React effects without relying on
  // an earlier document-load event or a fixed sleep after SPA navigation.
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

async function expectReadLedger(
  page: Page,
  audit: ReadAudit,
  expected: string[],
) {
  const ledger = [...expected].sort();
  await finishPresentation(page);
  await expect
    .poll(() => [...audit.reads].sort(), {
      message: "The owner must start exactly the expected synthetic reads",
    })
    .toEqual(ledger);
  await expect
    .poll(() => [...audit.completedReads].sort(), {
      message:
        "Every expected response body must finish before the next navigation",
    })
    .toEqual(ledger);
  await finishPresentation(page);
  expect([...audit.reads].sort()).toEqual(ledger);
  expect([...audit.completedReads].sort()).toEqual(ledger);
}

async function tabTo(page: Page, target: Locator) {
  // Begin at the header, then use the real tab order; focus() is not used to
  // bypass an inaccessible navigation link or a hidden mobile submenu.
  await page
    .getByRole("link", { name: "Trading Workspace", exact: true })
    .focus();
  for (let index = 0; index < 30; index++) {
    await page.keyboard.press("Tab");
    if (await target.evaluate((element) => element === document.activeElement))
      break;
  }
  await expect(target).toBeFocused();
  await expect
    .poll(() =>
      target.evaluate((element) => {
        const style = getComputedStyle(element);
        return (
          element.matches(":focus-visible") &&
          (style.boxShadow !== "none" ||
            (style.outlineStyle !== "none" &&
              parseFloat(style.outlineWidth) > 0))
        );
      }),
    )
    .toBe(true);
}

async function openNavigation(page: Page, narrow: boolean) {
  if (narrow) {
    const toggle = page.getByRole("button", {
      name: /^Navigation (öffnen|schließen)$/,
    });
    if ((await toggle.getAttribute("aria-expanded")) === "false") {
      await tabTo(page, toggle);
      await page.keyboard.press("Enter");
    }
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
  }
  await expect(
    page.getByRole("navigation", { name: "Hauptnavigation", exact: true }),
  ).toBeVisible();
}

async function navigateFromMenu(
  page: Page,
  narrow: boolean,
  name: string,
  path: string,
  group?: string,
) {
  await openNavigation(page, narrow);
  const navigation = page.getByRole("navigation", {
    name: group ? `${group}: Unterbereiche` : "Hauptnavigation",
    exact: true,
  });
  const link = navigation.getByRole("link", { name, exact: true });
  await tabTo(page, link);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL((url) => url.pathname === path);
  if (narrow) {
    await expect(
      page.getByRole("button", { name: "Navigation öffnen" }),
    ).toHaveAttribute("aria-expanded", "false");
    await expect(
      page.getByRole("navigation", { name: "Hauptnavigation", exact: true }),
    ).toBeHidden();
  }
  await expect(
    page.getByRole("navigation", { name: "Aktueller Ort" }),
  ).toContainText(group ?? name);
}

async function attachScreen(page: Page, testInfo: TestInfo, name: string) {
  await testInfo.attach(name, {
    body: await page.screenshot({ fullPage: true, animations: "disabled" }),
    contentType: "image/png",
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(
    overflow,
    "Only the position table may scroll horizontally, not the page",
  ).toBeLessThanOrEqual(1);
}

for (const width of [1440, 390]) {
  test.describe(`Fachstruktur A · ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test("keyboard navigation preserves the depot context and keeps diagnostic/report reads explicit", async ({
      page,
      baseURL,
    }, testInfo) => {
      const narrow = width < 1024;
      // Pin date-only preview inputs while letting timers and rendering run normally.
      await page.clock.setFixedTime(new Date(now));
      const audit = await installReadonlyFixture(page, baseURL!);
      const expectedReads: string[] = [];
      const expectReads = async (...newReads: string[]) => {
        expectedReads.push(...newReads);
        await expectReadLedger(page, audit, expectedReads);
      };
      const depotReads = [
        "/operational-workspace/positions",
        ...positions.map(
          (item) =>
            `/position-monitoring/trades/${item.trade_id}/alert-projection`,
        ),
      ];
      const positionQuery = `?position_id=${selected.position_id}`;
      const tradeReads = [
        tradePath,
        `${tradePath}/position`,
        `${tradePath}/management`,
        `/warrants/${selected.product_id}`,
        `${monitoringPath}/product-valuation`,
        `${tradePath}/timeline`,
        `${tradePath}/price-history`,
        `/alerts/trades/${selected.trade_id}`,
        `${monitoringPath}/health`,
        "/position-monitoring/runtime/status",
        `${monitoringPath}/indicative-entry${positionQuery}`,
        `${tradePath}/hebeltrader-evidence${positionQuery}`,
        `${monitoringPath}/hebeltrader-targets${positionQuery}`,
        `${monitoringPath}/hebeltrader-sessions${positionQuery}`,
        `${monitoringPath}/hebeltrader-original-bid${positionQuery}`,
        `${monitoringPath}/hebeltrader-loss${positionQuery}`,
        `${monitoringPath}/risk`,
        ...["BUY", "SELL"].map(
          (side) =>
            `${tradePath}/execution-currency-preview?${new URLSearchParams({
              side,
              executed_on: "2026-11-18",
              execution_timezone: "Europe/Berlin",
            })}`,
        ),
      ];
      const diagnosticReads = () =>
        audit.reads.filter((path) => path.startsWith("/market-data/")).length;
      const reportReads = () =>
        audit.reads.filter((path) => path.startsWith("/performance/")).length;

      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Aktuelles", exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Jetzt prüfen · 1" }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Nachbereiten · 1" }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Voraussetzungen klären · 1" }),
      ).toBeVisible();
      await expect(page.getByText(quoteProblem, { exact: true })).toBeVisible();
      await expect(
        page.getByRole("link", {
          name: "Überwachung und Datenlage öffnen: Kursbeleg für das synthetische DAX-Beispiel prüfen",
          exact: true,
        }),
      ).toHaveAttribute("href", `${selected.target}#trade-risk`);
      await expectReads("/operational-workspace/actions");
      await attachScreen(page, testInfo, `fachstruktur-${width}-aktuelles.png`);

      await navigateFromMenu(page, narrow, "Depot", "/workspace");
      await expect(
        page.getByRole("heading", { name: "Offene Positionen · 35" }),
      ).toBeVisible();
      await expectReads(...depotReads);
      await expect(
        page.getByText(/Positionssignale werden ergänzt/),
      ).toHaveCount(0);
      await page.getByLabel("Position suchen", { exact: true }).fill("DAX");
      await expect(page.getByRole("status")).toContainText(
        "33 Treffer von 35 offenen Positionen",
      );
      await page
        .getByRole("group", { name: "Positionsfilter" })
        .getByRole("button", { name: "Datenprobleme", exact: true })
        .click();
      await page
        .getByRole("combobox", { name: "Sortierung", exact: true })
        .selectOption("product");
      await page
        .getByRole("combobox", { name: "Zeilen pro Seite", exact: true })
        .selectOption("25");
      await page.getByRole("button", { name: "Nächste Seite" }).click();
      await expect(page.getByRole("status")).toContainText(
        "32 Treffer von 35 offenen Positionen · Seite 2 von 2",
      );
      const row = page.getByRole("row").filter({
        has: page.getByRole("rowheader", {
          name: selected.product_name,
          exact: false,
        }),
      });
      await expect(row).toBeVisible();
      const detailLink = row.getByRole("link", {
        name: "Trade öffnen",
        exact: true,
      });
      await detailLink.focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(
        (url) =>
          url.pathname === "/trade-management" &&
          url.searchParams.get("trade_id") === selected.trade_id &&
          url.hash === "#trade-overview",
      );
      await expect(
        page.getByRole("region", { name: "Trade und Position" }),
      ).toContainText(selected.product_name);
      await expectReads(...tradeReads);
      await expect(
        page.getByRole("button", { name: "Stand neu laden", exact: true }),
      ).toBeEnabled();
      const readsBeforeTab = audit.reads.length;
      const monitoringLink = page
        .getByRole("navigation", { name: "Trade-Arbeitsbereiche" })
        .getByRole("link", { name: "Überwachung", exact: true });
      await monitoringLink.focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(
        (url) =>
          url.pathname === "/trade-management" &&
          url.searchParams.get("trade_id") === selected.trade_id &&
          url.hash === "#trade-risk",
      );
      await expect(
        page.getByRole("region", {
          name: "Überwachung und Datenlage",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByText("Daten fehlen", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("Automatische Prüfung deaktiviert", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText(/Abgeschlossene Tagesdaten des Basiswerts fehlen/),
      ).toBeVisible();
      await expect(
        page.getByRole("link", {
          name: "Produkttermine und Handelsplatz am Optionsschein prüfen",
        }),
      ).toBeVisible();
      await attachScreen(
        page,
        testInfo,
        `fachstruktur-${width}-depotdetail.png`,
      );
      await expectReads();
      expect(
        audit.reads.length,
        "Switching object tabs must keep the existing readers mounted",
      ).toBe(readsBeforeTab);

      const returnLink = page.getByRole("link", {
        name: "Zur Positionsübersicht",
        exact: true,
      });
      await returnLink.focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL((url) => url.pathname === "/workspace");
      await expectReads(...depotReads);
      await expect(
        page.getByLabel("Position suchen", { exact: true }),
      ).toHaveValue("DAX");
      await expect(
        page.getByRole("button", { name: "Datenprobleme", exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await expect(
        page.getByRole("combobox", { name: "Sortierung", exact: true }),
      ).toHaveValue("product");
      await expect(
        page.getByRole("combobox", { name: "Zeilen pro Seite", exact: true }),
      ).toHaveValue("25");
      await expect(page.getByRole("status")).toContainText(
        "32 Treffer von 35 offenen Positionen · Seite 2 von 2",
      );
      await expect(row).toHaveAttribute("aria-selected", "true");
      await expect(
        row.getByRole("link", { name: "Überwachung", exact: true }),
      ).toBeFocused();

      await navigateFromMenu(page, narrow, "Marktanalyse", "/market-charts");
      await expect(
        page.getByRole("heading", {
          name: "Markt, Sektoren und Aktien",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", {
          name: "TEST S&P 500 und ETF-Übersicht",
          exact: true,
        }),
      ).toBeVisible();
      await expectReads("/market-charts/watchlist");
      await navigateFromMenu(page, narrow, "Lessons Learned", "/learning");
      await expect(
        page.getByRole("heading", {
          name: "Nachbeobachtung & Exit Review",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByText(
          /Eine vollständige Liste aller Journale ist derzeit nicht verfügbar/,
        ),
      ).toBeVisible();
      await expectReads("/operational-workspace/actions");
      await expect(
        page.getByRole("region", { name: "Vorhandener Nachbereitungsbedarf" }),
      ).toContainText("Abgeschlossener Call · Synthetisches Beispiel");
      await navigateFromMenu(page, narrow, "Basisdaten", "/underlyings");
      await expect(
        page.getByRole("heading", { name: "Basiswerte", exact: true }),
      ).toBeVisible();
      await expectReads(
        "/underlyings?offset=0&limit=25",
        "/market-reference-data/trading-venues",
        "/market-reference-data/currencies",
      );
      await navigateFromMenu(
        page,
        narrow,
        "Datenquellen & Diagnose",
        "/data-sources",
        "Basisdaten",
      );
      await expect(
        page.getByRole("heading", {
          name: "Datenquellen & Diagnose",
          exact: true,
        }),
      ).toBeVisible();
      await expectReads();
      expect(
        diagnosticReads(),
        "Entering diagnostics must not start a refresh or coverage read",
      ).toBe(0);
      const refreshDisclosure = page.getByText("Automatischer Kursabruf", {
        exact: true,
      });
      await refreshDisclosure.focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("button", { name: "Abrufstatus laden" }),
      ).toBeVisible();
      await expectReads();
      expect(
        diagnosticReads(),
        "Opening the disclosure does not read the scheduler",
      ).toBe(0);
      await page.getByRole("button", { name: "Abrufstatus laden" }).click();
      await expect(
        page.getByText("Diagnose · 1 Abrufnachweis", { exact: true }),
      ).toBeVisible();
      await expectReads("/market-data/refresh/status");
      expect(diagnosticReads()).toBe(1);
      await page
        .getByText("Diagnose · 1 Abrufnachweis", { exact: true })
        .click();
      await expect(
        page.getByText("Kein Kurs verfügbar · 1 Prüfung in Folge mit Befund", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByText("Qualifizierter Erfolg dieser Prüfung: Nein", {
          exact: true,
        }),
      ).toBeVisible();

      await navigateFromMenu(page, narrow, "Depot", "/workspace");
      await expectReads(...depotReads);
      await expect(
        page.getByText(/Positionssignale werden ergänzt/),
      ).toHaveCount(0);
      await navigateFromMenu(
        page,
        narrow,
        "Performance",
        "/performance/realized-gross",
        "Depot",
      );
      await expect(
        page.getByRole("form", { name: "Performance-Zeitraum auswählen" }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Bericht lesen", exact: true }),
      ).toBeVisible();
      await expectReads();
      expect(
        reportReads(),
        "Performance requires an explicit period and read action",
      ).toBe(0);
      await navigateFromMenu(page, narrow, "Aktuelles", "/");
      await expect(
        page.getByRole("heading", { name: "Jetzt prüfen · 1" }),
      ).toBeVisible();
      await expectReads("/operational-workspace/actions");
      expect(
        diagnosticReads(),
        "A return to Aktuelles must not repeat diagnostic reads",
      ).toBe(1);
      expect(reportReads()).toBe(0);
    });
  });
}
