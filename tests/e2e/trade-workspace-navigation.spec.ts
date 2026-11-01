import { expect, test, type Page, type Route } from "@playwright/test";
import type { PositionPriceHistoryReport } from "../../frontend/src/features/operational_workspace/positionPriceHistory";

import type {
  ExecutionCurrencyResolution,
  TradeResponse,
  TradeTimelineEntryResponse,
} from "../../frontend/src/features/trade/types/api";
import type {
  TradePlanSummaryResponse,
  TradePlanVersionResponse,
} from "../../frontend/src/features/trade_plan/types/api";
import { realizedGrossReport } from "../../frontend/src/test/realizedGrossFixtures";

// Read-only browser fixtures: every API request is intercepted. No real trade,
// provider, approval, execution or journal is created by these navigation tests.
test.use({ timezoneId: "Europe/Berlin", serviceWorkers: "block" });

const tradeId = "51000000-0000-4000-8000-000000000001";
const productId = "52000000-0000-4000-8000-000000000001";
const positionId = "53000000-0000-4000-8000-000000000001";
const buyId = "54000000-0000-4000-8000-000000000001";
const journalVersionId = "55000000-0000-4000-8000-000000000001";
const reviewVersionId = "56000000-0000-4000-8000-000000000001";
const planId = "57000000-0000-4000-8000-000000000001";
const planVersionId = "58000000-0000-4000-8000-000000000001";
const latestPlanVersionId = "58000000-0000-4000-8000-000000000002";
const underlyingId = "59000000-0000-4000-8000-000000000001";
const now = "2026-10-31T09:00:00Z";
const productName = "Synthetic UX2 navigation warrant";
const historicalThesis = "Synthetic approved P1 bound to this trade";
const latestThesis = "Synthetic newer draft P2, not the trade source";
const historicalCurrency: ExecutionCurrencyResolution = {
  currency_code: "EUR",
  source: "HISTORICAL_LISTING",
  source_execution_ids: [buyId],
  confirmation_ids: [],
  evidence_ids: ["synthetic-historical-currency-evidence"],
  evidence: [
    {
      id: "synthetic-historical-currency-evidence",
      kind: "HISTORICAL_LISTINGS",
      source_reference: "Synthetic archived EUR listing",
      recorded_at: "2026-08-01T09:00:00Z",
      valid_from: "2026-08-01T00:00:00Z",
      valid_to: "2026-09-01T00:00:00Z",
      verification: "USER_VERIFIED_SOURCE",
    },
  ],
};
const inheritedCurrency: ExecutionCurrencyResolution = {
  ...historicalCurrency,
  source: "PRIOR_BUYS",
};

const plan: TradePlanSummaryResponse = {
  id: planId,
  underlying_id: underlyingId,
  origin_type: "MANUAL",
  candidate_id: null,
  candidate_evaluation_id: null,
  created_at: "2026-08-01T09:00:00Z",
  created_by: "synthetic-actor",
};
const historicalPlan: TradePlanVersionResponse = {
  id: planVersionId,
  trade_plan_id: planId,
  version: 1,
  direction: "LONG",
  thesis: historicalThesis,
  entry: {
    type: "PRICE",
    currency: "EUR",
    price: "100",
    price_from: null,
    price_to: null,
    trigger: null,
    reference_price: null,
    valid_until: null,
    rationale: null,
  },
  invalidation: {
    stop_price: "95",
    invalidation_rule: null,
    rationale: null,
  },
  targets: [{ sequence: 1, price: "110", rationale: null }],
  risk_assumptions: {
    thesis_risk: "Synthetic trend break",
    max_loss_assumption: null,
    notes: null,
  },
  status: "APPROVED",
  created_at: plan.created_at,
  created_by: plan.created_by,
  previous_version_id: null,
  change_reason: null,
  candidate_evaluation: null,
  approval: {
    approval_id: "synthetic-approval-p1",
    trade_plan_version_id: planVersionId,
    version: 1,
    actor: plan.created_by,
    approved_at: "2026-08-02T09:00:00Z",
    correlation_id: null,
  },
  events: [],
};
const latestPlan: TradePlanVersionResponse = {
  ...historicalPlan,
  id: latestPlanVersionId,
  version: 2,
  thesis: latestThesis,
  status: "DRAFT",
  created_at: "2026-10-30T09:00:00Z",
  previous_version_id: planVersionId,
  change_reason: "Synthetic amendment after the original trade",
  approval: null,
};

// Existing server-shaped financial fixtures supply all amounts. This mapping
// changes identities only, so the report and booking/source owners share them.
function navigationReport() {
  const report = realizedGrossReport();
  report.items = report.items.map((item) => ({
    ...item,
    trade_id: tradeId,
    product_id: productId,
    product_name: productName,
  }));
  report.sources = report.sources.map((source) => ({
    ...source,
    trade_id: tradeId,
    product_id: productId,
    currency_confirmation: source.currency_confirmation
      ? { ...source.currency_confirmation, trade_id: tradeId }
      : null,
    currency_history: source.currency_history.map((confirmation) => ({
      ...confirmation,
      trade_id: tradeId,
    })),
  }));
  return report;
}

function reportQuery() {
  const report = navigationReport();
  return new URLSearchParams({
    report_context: "realized-gross",
    ...report.filters,
    report_view: "usable",
    report_page: "1",
    report_basis: report.basis.id,
  });
}

type Status = "OPEN" | "CLOSED" | "CANCELLED";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, json: body });
}

function salePreviewReads(reads: string[], dates = ["2026-08-20"]) {
  return reads.filter((read) => {
    const url = new URL(read, "http://synthetic-fixture.invalid");
    return (
      url.pathname.endsWith(
        `/api/v1/trade-position/trades/${tradeId}/execution-currency-preview`,
      ) &&
      url.searchParams.get("side") === "SELL" &&
      url.searchParams.get("execution_timezone") === "Europe/Berlin" &&
      dates.includes(url.searchParams.get("executed_on") ?? "")
    );
  });
}

async function fixture(
  page: Page,
  options: {
    status?: Status;
    missingPosition?: boolean;
    historicalPlan?: boolean;
    reportJourney?: boolean;
    currencyPreview?: "available" | ((route: Route, url: URL) => Promise<void>);
    priceHistory?: PositionPriceHistoryReport;
  } = {},
) {
  const status = options.status ?? "OPEN";
  const report = navigationReport();
  const lastSale = report.items[report.items.length - 1];
  const openQuantity =
    status === "OPEN"
      ? options.reportJourney
        ? lastSale.open_quantity_after
        : 10
      : 0;
  const trade: TradeResponse = {
    id: tradeId,
    product_id: productId,
    origin: options.historicalPlan ? "WORKSPACE_SELECTION" : "EXTERNAL",
    trade_plan_id: options.historicalPlan ? planId : null,
    trade_plan_version_id: options.historicalPlan ? planVersionId : null,
    product_selection_id: null,
    product_evaluation_id: null,
    created_at: "2026-08-17T08:30:00Z",
    cancelled_at: status === "CANCELLED" ? now : null,
    cancellation_reason: status === "CANCELLED" ? "Synthetic duplicate" : null,
  };
  const buy: TradeTimelineEntryResponse = {
    id: buyId,
    trade_id: tradeId,
    kind: "EXECUTION",
    execution_side: "BUY",
    management_event_type: null,
    occurred_at: "2026-08-16T22:00:00Z",
    recorded_at: "2026-08-17T08:30:00Z",
    executed_on: "2026-08-17",
    execution_timezone: "Europe/Berlin",
    quantity: 10,
    price_per_unit: "2.00",
    numeric_value: null,
    text_value: null,
    supersedes_id: null,
    currency_confirmation: null,
    currency_resolution: options.currencyPreview
      ? historicalCurrency
      : {
          currency_code: null,
          source: "UNKNOWN",
          source_execution_ids: [],
          confirmation_ids: [],
        },
  };
  const timeline: TradeTimelineEntryResponse[] = options.reportJourney
    ? report.sources.map((source) => ({
        id: source.execution_id,
        trade_id: tradeId,
        kind: "EXECUTION",
        execution_side: source.side,
        management_event_type: null,
        occurred_at: source.executed_at ?? source.recorded_at,
        recorded_at: source.recorded_at,
        executed_on: source.executed_on,
        execution_timezone: source.execution_timezone,
        quantity: source.quantity,
        price_per_unit: source.price_per_unit,
        numeric_value: null,
        text_value: null,
        supersedes_id: source.supersedes_execution_id,
        currency_confirmation: source.currency_confirmation,
        currency_resolution: source.currency_resolution,
      }))
    : [buy];
  const reads: string[] = [];
  const writes: string[] = [];
  const browserErrors: string[] = [];
  const snapshot = (data: unknown) => ({
    data,
    read_started_at: now,
    read_completed_at: now,
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() !== "GET") {
      writes.push(`${request.method()} ${path}`);
      return json(
        route,
        { message: "Unexpected write in read-only UX2 fixture" },
        405,
      );
    }
    reads.push(`${path}${url.search}`);
    if (path.endsWith("/execution-currency-preview")) {
      if (typeof options.currencyPreview === "function")
        return options.currencyPreview(route, url);
      if (options.currencyPreview === "available")
        return json(route, inheritedCurrency);
      return json(
        route,
        {
          code: "SYNTHETIC_PREVIEW_UNAVAILABLE",
          message: "Synthetic historical currency source is unavailable.",
          details: [],
          timestamp: now,
        },
        503,
      );
    }
    if (path.endsWith("/performance/realized-gross"))
      return json(route, report);
    if (options.historicalPlan) {
      if (path.endsWith(`/trade-plans/${planId}`))
        return json(route, { plan, latest_version: latestPlan });
      if (path.endsWith(`/trade-plans/${planId}/versions`))
        return json(route, [historicalPlan, latestPlan]);
      if (path.endsWith(`/trade-plans/${planId}/versions/${planVersionId}`))
        return json(route, historicalPlan);
      if (
        path.endsWith(`/trade-plans/${planId}/versions/${latestPlanVersionId}`)
      )
        return json(route, latestPlan);
      if (path.endsWith(`/underlyings/${underlyingId}`))
        return json(route, {
          id: underlyingId,
          display_name: "Synthetic plan underlying",
          symbol: "UX2",
          asset_class: "EQUITY",
        });
    }
    if (path.endsWith(`/trade-position/trades/${tradeId}`))
      return json(route, trade);
    if (path.endsWith("/position")) {
      if (options.missingPosition)
        return json(
          route,
          {
            code: "SYNTHETIC_POSITION_MISSING",
            message: "Synthetic UX2 position is unavailable.",
            details: [],
            timestamp: now,
          },
          404,
        );
      return json(route, {
        id: positionId,
        trade_id: tradeId,
        product_id: productId,
        open_quantity: openQuantity,
        cost_basis:
          status === "OPEN"
            ? options.reportJourney
              ? lastSale.cost_basis_after
              : "20.00"
            : "0.00",
        average_entry_price: options.reportJourney
          ? lastSale.average_cost_per_unit
          : "2.00",
        realized_gross_pnl: null,
        opened_at: trade.created_at,
        opened_on: "2026-08-17",
        closed_at: status === "CLOSED" ? now : null,
        last_execution_at: trade.created_at,
        is_closed: status === "CLOSED",
      });
    }
    if (path.endsWith("/management"))
      return json(route, {
        trade_id: tradeId,
        stop_price: "1.50",
        target_price: "3.00",
        stop_price_binding: null,
        target_price_binding: null,
        thesis: "Existing synthetic thesis",
        notes: [],
        last_event_at: trade.created_at,
      });
    if (path.endsWith("/timeline")) return json(route, timeline);
    if (path.endsWith("/currency-confirmations")) {
      const source = report.sources.find((item) =>
        path.includes(`/executions/${item.execution_id}/`),
      );
      return json(route, {
        current: source?.currency_confirmation ?? null,
        history: source?.currency_history ?? [],
        currency_resolution:
          source?.currency_resolution ?? buy.currency_resolution,
      });
    }
    if (path.endsWith(`/warrants/${productId}`))
      return json(route, {
        id: productId,
        workspace_id: "workspace",
        underlying_id: "underlying",
        issuer_id: "issuer",
        display_name: productName,
        product_family: "WARRANT",
        isin: null,
        wkn: null,
        lifecycle_status: "ACTIVE",
        version: 1,
        created_at: trade.created_at,
        updated_at: trade.created_at,
      });
    if (path.endsWith("/price-history"))
      return json(
        route,
        options.priceHistory ?? {
          trade_id: tradeId,
          position_id: positionId,
          warrant_id: productId,
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
        },
      );
    if (path.endsWith(`/alerts/trades/${tradeId}`)) return json(route, []);
    if (path.endsWith("/sources"))
      return json(
        route,
        snapshot({
          trade,
          product_name: productName,
          state: status,
          open_quantity: openQuantity,
          timeline,
          currency_history: [],
        }),
      );
    if (path.endsWith("/sources/plan"))
      return json(
        route,
        snapshot(
          options.historicalPlan
            ? {
                plan,
                version: historicalPlan,
                approval: historicalPlan.approval,
                candidate_evaluation: historicalPlan.candidate_evaluation,
                events: historicalPlan.events,
              }
            : null,
        ),
      );
    if (options.historicalPlan && path.endsWith("/sources/reviews")) {
      const selected = {
        version: {
          id: reviewVersionId,
          exit_review_id: "synthetic-review",
          version: 1,
          status: "FINALIZED",
          currentness: "CURRENT",
          timing: "IMPROVABLE",
          process_adherence: "NOT_ASSESSABLE",
          risk_decision: null,
          overall_exit_decision: "IMPROVABLE",
          rationale: "Synthetic historical review R1",
          created_at: now,
          finalized_at: now,
          supersedes_version_id: null,
          stale_reason: null,
        },
      };
      return json(
        route,
        snapshot({
          history: [selected],
          selected,
          source_currentness: "STALE",
          checked_at: now,
        }),
      );
    }
    if (options.historicalPlan && path.endsWith("/sources/journal")) {
      const selected = {
        id: journalVersionId,
        trade_journal_id: "synthetic-journal",
        version: 1,
        edit_revision: 1,
        status: "FINALIZED",
        source_exit_review_version_id: reviewVersionId,
        what_went_well: "Synthetic historical journal J1",
        would_do_differently: null,
        additional_notes: null,
        created_at: now,
        updated_at: now,
        finalized_at: now,
        supersedes_version_id: null,
      };
      return json(
        route,
        snapshot({
          history: [selected],
          selected,
          source_currentness: "STALE",
          checked_at: now,
        }),
      );
    }
    if (path.endsWith("/sources/reviews") || path.endsWith("/sources/journal"))
      return json(
        route,
        snapshot({
          history: [],
          selected: null,
          source_currentness: "UNKNOWN",
          checked_at: now,
        }),
      );
    if (path.endsWith("/sources/evidence")) return json(route, snapshot([]));
    return json(
      route,
      {
        code: "SYNTHETIC_UNAVAILABLE",
        message: "Outside the read-only UX2 navigation fixture.",
        details: [],
        timestamp: now,
      },
      503,
    );
  });
  return { reads, writes, browserErrors };
}

function navigation(page: Page) {
  return page.getByRole("navigation", {
    name: "Trade-Arbeitsbereiche",
    exact: true,
  });
}

async function loaded(page: Page, bookingCount = 1) {
  await expect(
    page
      .getByRole("region", { name: "Trade und Position", exact: true })
      .getByRole("heading", { name: new RegExp(productName) }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Laden", exact: true }),
  ).toBeEnabled();
  await expect(
    page
      .getByRole("region", { name: "Kauf- und Verkaufsdaten" })
      .getByRole("article"),
  ).toHaveCount(bookingCount);
  await page.waitForLoadState("networkidle");
}

for (const width of [390, 1280]) {
  test(`one trade keeps both drafts and read owners through keyboard section changes at ${width}px`, async ({
    page,
  }, testInfo) => {
    const observed = await fixture(page, { currencyPreview: "available" });
    await page.setViewportSize({ width, height: 844 });
    // Preserve the exact spelling and ordering of supported context parameters.
    // URLSearchParams normalisation would change both and trigger a dirty guard.
    const query = `?journal_version_id=${journalVersionId}&trade_id=%35${tradeId.slice(1)}`;
    await page.goto(`/trade-management${query}#trade-overview`);
    await loaded(page);
    await expect(page.locator("#trade-overview")).toBeFocused();

    await page.getByLabel("Verkaufsmenge", { exact: true }).fill("3");
    await page.getByLabel("Verkaufspreis", { exact: true }).fill("2.50");
    const sale = page.locator("#sale-capture");
    await sale.getByLabel("Verkaufsdatum", { exact: true }).fill("2026-08-20");
    await expect(
      sale.getByText(
        "Vorhandene Währung: EUR · aus vorherigen Käufen übernommen",
      ),
    ).toBeVisible();
    await expect(sale.getByLabel("Ausführungswährung (Code)")).toHaveCount(0);
    await sale
      .getByText("Verwendete Währungsherkunft", { exact: true })
      .click();
    await expect(
      sale.getByText("Quelle: Synthetic archived EUR listing"),
    ).toBeVisible();
    await sale
      .getByRole("button", { name: "Abweichende Währung angeben", exact: true })
      .click();
    await sale.getByLabel("Ausführungswährung (Code)").fill("CHF");
    await sale
      .getByLabel("Beleg / Erläuterung (optional)")
      .fill("Synthetic manual sale receipt");
    const bookings = page.getByRole("region", {
      name: "Kauf- und Verkaufsdaten",
    });
    await bookings
      .getByRole("button", { name: "Kauf korrigieren", exact: true })
      .click();
    const correctionDate = bookings.getByLabel("Kaufdatum korrigieren", {
      exact: true,
    });
    await correctionDate.fill("2026-08-16");
    await page.waitForLoadState("networkidle");
    const originalReads = [...observed.reads];
    expect(salePreviewReads(originalReads)).toHaveLength(1);

    for (const [label, hash] of [
      ["Kursverlauf", "#position-price-history"],
      ["Buchungen", "#execution-dates"],
      ["Risiko und Management", "#trade-risk"],
      ["Überblick", "#trade-overview"],
    ]) {
      const link = navigation(page).getByRole("link", {
        name: label,
        exact: true,
      });
      await expect(link).toHaveAttribute(
        "href",
        `/trade-management${query}${hash}`,
      );
      await link.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator(hash)).toBeFocused();
      expect(new URL(page.url()).search).toBe(query);
      expect(new URL(page.url()).hash).toBe(hash);
      await expect(page.getByRole("alertdialog")).toHaveCount(0);
      await expect(
        page.getByLabel("Verkaufsmenge", { exact: true }),
      ).toHaveValue("3");
      await expect(
        page.getByLabel("Verkaufspreis", { exact: true }),
      ).toHaveValue("2.50");
      await expect(correctionDate).toHaveValue("2026-08-16");
      await expect(
        sale.getByLabel("Verkaufsdatum", { exact: true }),
      ).toHaveValue("2026-08-20");
      await expect(sale.getByLabel("Ausführungswährung (Code)")).toHaveValue(
        "CHF",
      );
      await expect(
        sale.getByLabel("Beleg / Erläuterung (optional)"),
      ).toHaveValue("Synthetic manual sale receipt");
      await expect(
        sale.getByText(
          "Vorhandene Währung: EUR · aus vorherigen Käufen übernommen",
        ),
      ).toBeVisible();
      expect(observed.reads).toEqual(originalReads);
    }

    await navigation(page)
      .getByRole("link", { name: "Überblick", exact: true })
      .focus();
    await page.keyboard.press("Tab");
    await expect(
      navigation(page).getByRole("link", { name: "Kursverlauf", exact: true }),
    ).toBeFocused();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      )
      .toBe(true);
    const screenshot = testInfo.outputPath(
      `trade-workspace-navigation-${width}.png`,
    );
    await navigation(page).screenshot({ path: screenshot });
    await testInfo.attach(`trade-workspace-navigation-${width}`, {
      path: screenshot,
      contentType: "image/png",
    });
    expect(observed.writes).toEqual([]);
    expect(observed.browserErrors).toEqual([]);
  });
}

test("a failed currency preview remains a read error while manual drafts survive sections and retry", async ({
  page,
}) => {
  let available = false;
  const observed = await fixture(page, {
    currencyPreview: async (route) =>
      available
        ? json(route, inheritedCurrency)
        : json(
            route,
            { message: "Synthetic historical currency source is unavailable." },
            503,
          ),
  });
  await page.goto(`/trade-management?trade_id=${tradeId}#sale-capture`);
  await loaded(page);
  const sale = page.locator("#sale-capture");
  await sale.getByLabel("Verkaufsdatum", { exact: true }).fill("2026-08-20");
  await expect(
    sale.getByText(/Währungsherkunft derzeit nicht geprüft/),
  ).toBeVisible();
  await expect(sale.getByText(/Vorhandene Währung:/)).toHaveCount(0);
  await sale
    .getByRole("button", { name: "Abweichende Währung angeben", exact: true })
    .click();
  await sale.getByLabel("Ausführungswährung (Code)").fill("CHF");
  await sale
    .getByLabel("Beleg / Erläuterung (optional)")
    .fill("Synthetic manual receipt after read error");
  const readsBeforeSection = [...observed.reads];
  await navigation(page)
    .getByRole("link", { name: "Buchungen", exact: true })
    .click();
  await expect(page.locator("#execution-dates")).toBeFocused();
  expect(observed.reads).toEqual(readsBeforeSection);
  available = true;
  await sale
    .getByRole("button", { name: "Währungsherkunft erneut prüfen" })
    .click();
  await expect(
    sale.getByText(
      "Vorhandene Währung: EUR · aus vorherigen Käufen übernommen",
    ),
  ).toBeVisible();
  await expect(sale.getByLabel("Ausführungswährung (Code)")).toHaveValue("CHF");
  await expect(sale.getByLabel("Beleg / Erläuterung (optional)")).toHaveValue(
    "Synthetic manual receipt after read error",
  );
  expect(salePreviewReads(observed.reads)).toHaveLength(2);
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

test("UX4-B same-trade hashes preserve source visibility, exact evidence page and manual drafts without another read", async ({
  page,
}) => {
  const series = {
    id: "synthetic-hash-source-a",
    provider: "SYNTHETIC_HASH_PROVIDER_A",
    identity_key: "synthetic-historical-identity-a",
    warrant_listing_id: "synthetic-historical-listing-a",
    isin: "DE000VH2LU21",
    currency: "EUR",
    price_kind: "BID" as const,
    source_mode: "OFFICIAL_WEBSITE",
    provider_exchange_code: "_FRA",
    venue_mic: "XFRA",
    points: Array.from({ length: 55 }, (_, index) => ({
      id: "synthetic-point-" + index,
      observed_at: new Date(
        Date.parse("2026-09-10T13:00:00Z") + index * 60000,
      ).toISOString(),
      price: "2.231234567890123456789",
      captured_at: now,
      retrieved_at: now,
      status: "TWO_SIDED_WITHIN_AGE_LIMIT",
      storage: "SAMPLE" as const,
      quote_time_basis: null,
    })),
  };
  const priceHistory: PositionPriceHistoryReport = {
    trade_id: tradeId,
    position_id: positionId,
    warrant_id: productId,
    isin: series.isin,
    window_start: null,
    window_end: now,
    sampling_policy: "FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1",
    sample_limit: 10000,
    samples_considered: 56,
    samples_available: 56,
    truncated: false,
    collection_started_at: now,
    excluded: {},
    series: [
      series,
      {
        ...series,
        id: "synthetic-hash-source-b",
        provider: "SYNTHETIC_HASH_PROVIDER_B",
        identity_key: "synthetic-historical-identity-b",
        points: [{ ...series.points[54], price: "2.33" }],
      },
    ],
    events: [],
  };
  const observed = await fixture(page, {
    currencyPreview: "available",
    priceHistory,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(
    "/trade-management?trade_id=" + tradeId + "#position-price-history",
  );
  await loaded(page);
  const panel = page.getByRole("region", {
    name: "Positionskursverlauf",
    exact: true,
  });
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(56);
  const hiddenSource = panel.getByRole("checkbox", { name: /^Quelle 2:/ });
  await hiddenSource.focus();
  await page.keyboard.press("Space");
  await expect(hiddenSource).not.toBeChecked();
  const choosePoint = panel.getByText("Punkte und Buchungen auswählen (EUR)", {
    exact: true,
  });
  await choosePoint.focus();
  await page.keyboard.press("Enter");
  for (let next = 0; next < 2; next += 1) {
    await panel
      .getByRole("button", { name: "Weitere Einzelbelege", exact: true })
      .focus();
    await page.keyboard.press("Enter");
  }
  const point = panel.getByRole("button", { name: /^Quelle 1, Kurspunkt 55:/ });
  await point.focus();
  await page.keyboard.press("Enter");
  const selected = panel.getByRole("region", {
    name: "Ausgewählter Originalkursbeleg",
    exact: true,
  });
  await expect(selected).toBeFocused();
  await expect(selected).toContainText("2,231234567890123456789 EUR");
  await expect(panel.getByText("Seite 2 / 2", { exact: true })).toBeVisible();

  await page.getByLabel("Verkaufsmenge", { exact: true }).fill("3");
  await page.getByLabel("Verkaufspreis", { exact: true }).fill("2.50");
  await page
    .getByLabel("Neue Management-Notiz", { exact: true })
    .fill("Synthetic unsaved note survives chart navigation");
  await page.waitForLoadState("networkidle");
  const originalReads = [...observed.reads];
  expect(
    originalReads.filter((url) => url.endsWith("/price-history")),
  ).toHaveLength(1);

  for (const [label, hash] of [
    ["Buchungen", "#execution-dates"],
    ["Überblick", "#trade-overview"],
    ["Kursverlauf", "#position-price-history"],
  ]) {
    const link = navigation(page).getByRole("link", {
      name: label,
      exact: true,
    });
    await link.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(hash)).toBeFocused();
    expect(new URL(page.url()).hash).toBe(hash);
    await expect(hiddenSource).not.toBeChecked();
    await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(55);
    await expect(panel.getByText("Seite 2 / 2", { exact: true })).toBeVisible();
    await expect(
      panel.getByText("Auswahlseite 3 / 3", { exact: true }),
    ).toBeVisible();
    await expect(selected).toContainText("2,231234567890123456789 EUR");
    await expect(page.getByLabel("Verkaufsmenge", { exact: true })).toHaveValue(
      "3",
    );
    await expect(page.getByLabel("Verkaufspreis", { exact: true })).toHaveValue(
      "2.50",
    );
    await expect(
      page.getByLabel("Neue Management-Notiz", { exact: true }),
    ).toHaveValue("Synthetic unsaved note survives chart navigation");
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    expect(observed.reads).toEqual(originalReads);
  }
  const table = panel.getByRole("region", {
    name: "Historische Kursdaten",
    exact: true,
  });
  // A duplicated local point ID in the other historical source remains a separate row.
  await expect(
    table.getByRole("row").filter({ hasText: "Punkt-ID: synthetic-point-54" }),
  ).toHaveCount(2);
  await expect(
    table
      .getByRole("row")
      .filter({ hasText: "Serien-ID: synthetic-hash-source-b" }),
  ).toContainText("2,33");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

for (const lateOutcome of ["success", "error"] as const) {
  test(`date A → B → A ignores a late preview ${lateOutcome} and retains manual currency through navigation`, async ({
    page,
  }) => {
    let releaseFirst: () => void = () => {};
    let firstReleased: () => void = () => {};
    const firstPending = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const firstHandled = new Promise<void>((resolve) => {
      firstReleased = resolve;
    });
    let aReads = 0;
    const observed = await fixture(page, {
      currencyPreview: async (route, url) => {
        const day = url.searchParams.get("executed_on");
        if (day === "2026-08-20" && ++aReads === 1) {
          await firstPending;
          try {
            await json(
              route,
              lateOutcome === "success"
                ? { ...inheritedCurrency, currency_code: "USD" }
                : { message: "Synthetic obsolete preview error" },
              lateOutcome === "success" ? 200 : 503,
            );
          } finally {
            firstReleased();
          }
          return;
        }
        await json(
          route,
          day === "2026-08-21"
            ? { ...inheritedCurrency, currency_code: "GBP" }
            : inheritedCurrency,
        );
      },
    });
    await page.goto(`/trade-management?trade_id=${tradeId}#sale-capture`);
    await loaded(page);
    const sale = page.locator("#sale-capture");
    const date = sale.getByLabel("Verkaufsdatum", { exact: true });
    await date.fill("2026-08-20");
    await expect.poll(() => aReads).toBe(1);
    await sale
      .getByRole("button", { name: "Abweichende Währung angeben", exact: true })
      .click();
    await sale.getByLabel("Ausführungswährung (Code)").fill("CHF");
    await sale
      .getByLabel("Beleg / Erläuterung (optional)")
      .fill("Synthetic receipt retained across dates");
    await date.fill("2026-08-21");
    await expect(
      sale.getByText(
        "Vorhandene Währung: GBP · aus vorherigen Käufen übernommen",
      ),
    ).toBeVisible();
    await date.fill("2026-08-20");
    await expect(
      sale.getByText(
        "Vorhandene Währung: EUR · aus vorherigen Käufen übernommen",
      ),
    ).toBeVisible();
    releaseFirst();
    await firstHandled;
    await page.waitForLoadState("networkidle");
    const readsBeforeSection = [...observed.reads];
    for (const label of ["Kursverlauf", "Überblick"]) {
      await navigation(page)
        .getByRole("link", { name: label, exact: true })
        .click();
      await expect(
        sale.getByText(
          "Vorhandene Währung: EUR · aus vorherigen Käufen übernommen",
        ),
      ).toBeVisible();
      await expect(sale.getByText(/Vorhandene Währung: (USD|GBP)/)).toHaveCount(
        0,
      );
      await expect(
        sale.getByText(/Synthetic obsolete preview error/),
      ).toHaveCount(0);
      await expect(sale.getByLabel("Ausführungswährung (Code)")).toHaveValue(
        "CHF",
      );
      await expect(
        sale.getByLabel("Beleg / Erläuterung (optional)"),
      ).toHaveValue("Synthetic receipt retained across dates");
    }
    expect(observed.reads).toEqual(readsBeforeSection);
    expect(
      salePreviewReads(observed.reads, ["2026-08-20", "2026-08-21"]).map(
        (read) =>
          new URL(read, "http://synthetic-fixture.invalid").searchParams.get(
            "executed_on",
          ),
      ),
    ).toEqual(["2026-08-20", "2026-08-21", "2026-08-20"]);
    expect(observed.writes).toEqual([]);
    expect(observed.browserErrors).toEqual([]);
  });
}

test("leaving for plan sources or journal uses the one existing discard guard", async ({
  page,
}) => {
  const observed = await fixture(page);
  const original = `/trade-management?trade_id=${tradeId}#trade-overview`;
  await page.goto(original);
  await loaded(page);
  await page
    .getByLabel("Neue Management-Notiz", { exact: true })
    .fill("Unfinished UX2 note");

  for (const label of ["Plan und Quellen", "Journal und Lessons"]) {
    await navigation(page)
      .getByRole("link", { name: label, exact: true })
      .click();
    const guard = page.getByRole("alertdialog", {
      name: "Ungespeicherte Änderungen",
    });
    await expect(guard).toHaveCount(1);
    const stay = guard.getByRole("button", { name: "Hier bleiben" });
    const discard = guard.getByRole("button", {
      name: "Eingaben verwerfen und wechseln",
    });
    await expect(stay).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(discard).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(stay).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(guard).toHaveCount(0);
    expect(
      new URL(page.url()).pathname +
        new URL(page.url()).search +
        new URL(page.url()).hash,
    ).toBe(original);
    await expect(
      page.getByLabel("Neue Management-Notiz", { exact: true }),
    ).toHaveValue("Unfinished UX2 note");
  }

  await navigation(page)
    .getByRole("link", { name: "Plan und Quellen", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Eingaben verwerfen und wechseln" })
    .click();
  await expect(page.locator("#trade-plan-sources")).toBeFocused();
  expect(new URL(page.url()).searchParams.get("trade_id")).toBe(tradeId);
  expect(new URL(page.url()).searchParams.get("view")).toBe("sources");
  await expect(
    page.getByText(
      "Eigener EXTERNAL-Trade ohne dokumentierte ursprüngliche Planherkunft.",
    ),
  ).toBeVisible();
  await navigation(page)
    .getByRole("link", { name: "Überblick", exact: true })
    .click();
  await loaded(page);
  await expect(
    page.getByLabel("Neue Management-Notiz", { exact: true }),
  ).toHaveValue("");
  expect(new URL(page.url()).searchParams.get("trade_id")).toBe(tradeId);
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

test("native reload warns about an unfinished booking and cancelling keeps the draft", async ({
  page,
}) => {
  const observed = await fixture(page);
  await page.goto(`/trade-management?trade_id=${tradeId}#execution-dates`);
  await loaded(page);
  const bookings = page.getByRole("region", {
    name: "Kauf- und Verkaufsdaten",
  });
  await bookings
    .getByRole("button", { name: "Kauf korrigieren", exact: true })
    .click();
  const input = bookings.getByLabel("Kaufdatum korrigieren", { exact: true });
  await input.fill("2026-08-16");
  const dialogPromise = page.waitForEvent("dialog");
  // Trigger the real native reload without waiting for a navigation commit:
  // a correctly dismissed beforeunload dialog deliberately prevents that commit.
  const reloadPromise = page.evaluate(() => window.location.reload());
  const dialog = await dialogPromise;
  expect(dialog.type()).toBe("beforeunload");
  await dialog.dismiss();
  await reloadPromise;
  await expect(input).toHaveValue("2026-08-16");
  expect(new URL(page.url()).hash).toBe("#execution-dates");
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

test("direct section URLs survive reload, including the existing booking and sale anchors", async ({
  page,
}) => {
  const observed = await fixture(page);
  for (const hash of [
    "#trade-overview",
    "#position-price-history",
    "#execution-dates",
    "#trade-risk",
    "#sale-capture",
  ]) {
    await page.goto(`/trade-management?trade_id=${tradeId}${hash}`);
    await loaded(page);
    await expect(page.locator(hash)).toBeFocused();
    await page.reload();
    await loaded(page);
    await expect(page.locator(hash)).toBeFocused();
    expect(new URL(page.url()).searchParams.get("trade_id")).toBe(tradeId);
    expect(new URL(page.url()).hash).toBe(hash);
  }
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

test("a missing position offers no stale booking context or fabricated holding", async ({
  page,
}) => {
  const observed = await fixture(page, { missingPosition: true });
  await page.goto(`/trade-management?trade_id=${tradeId}#execution-dates`);
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Synthetic UX2 position is unavailable." }),
  ).toBeVisible();
  await expect(
    page.getByRole("form", { name: "Verkauf erfassen", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Kauf- und Verkaufsdaten" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Trade und Position" }),
  ).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get("trade_id")).toBe(tradeId);
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

for (const status of ["CLOSED", "CANCELLED"] as const) {
  test(`${status.toLowerCase()} trade keeps source and booking navigation without enabling a sale`, async ({
    page,
  }) => {
    const observed = await fixture(page, { status });
    await page.goto(`/trade-management?trade_id=${tradeId}#execution-dates`);
    await loaded(page);
    await expect(page.getByText(status, { exact: true })).toHaveCount(1);
    await expect(
      navigation(page).getByRole("link", { name: "Buchungen", exact: true }),
    ).toHaveAttribute(
      "href",
      `/trade-management?trade_id=${tradeId}#execution-dates`,
    );
    await expect(
      navigation(page).getByRole("link", {
        name: "Plan und Quellen",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Teilverkauf erfassen", exact: true }),
    ).toHaveCount(0);
    if (status === "CANCELLED") {
      await expect(
        page.getByRole("region", { name: "Positionskursverlauf" }),
      ).toHaveCount(0);
      expect(observed.reads.some((url) => url.includes("/price-history"))).toBe(
        false,
      );
    } else {
      await expect(
        page.getByRole("region", { name: "Positionskursverlauf" }),
      ).toBeVisible();
    }
    expect(observed.writes).toEqual([]);
    expect(observed.browserErrors).toEqual([]);
  });
}

function expectReportContext(url: string, expected: URLSearchParams) {
  const actual = new URL(url, "http://fixture.invalid").searchParams;
  for (const [key, value] of expected) {
    expect(actual.getAll(key), key).toEqual([value]);
  }
}

test("the bound approved plan opens in this tab and retains historical trade sources through a copied URL and reload", async ({
  page,
}) => {
  const observed = await fixture(page, { historicalPlan: true });
  await page.setViewportSize({ width: 1280, height: 844 });
  const context = reportQuery();
  context.set("trade_id", tradeId);
  context.set("review_version_id", reviewVersionId);
  context.set("journal_version_id", journalVersionId);
  const sourceQuery = new URLSearchParams(context);
  sourceQuery.set("view", "sources");
  await page.goto(`/trade-management?${sourceQuery}#trade-plan-sources`);
  const planSource = page.getByRole("region", { name: "Ursprünglicher Plan" });
  await expect(planSource).toContainText(historicalThesis);
  await expect(planSource).toContainText(
    "Ursprünglich referenzierte Planversion 1 · Status APPROVED",
  );
  await expect(page.getByText("Synthetic historical review R1")).toBeVisible();
  await expect(page.getByText("Synthetic historical journal J1")).toBeVisible();

  const planLink = planSource.getByRole("link", {
    name: "Gebundene Planversion öffnen",
    exact: true,
  });
  const copiedLink = await planLink.getAttribute("href");
  expect(copiedLink).not.toBeNull();
  const destination = new URL(copiedLink!, page.url());
  expect(destination.pathname).toBe("/trade-plans");
  expect(destination.searchParams.getAll("trade_plan_id")).toEqual([planId]);
  expect(destination.searchParams.getAll("trade_plan_version_id")).toEqual([
    planVersionId,
  ]);
  expect(destination.searchParams.get("trade_return_view")).toBe("sources");
  expectReportContext(destination.href, context);
  await expect(planLink).not.toHaveAttribute("target", "_blank");
  const originalTabCount = page.context().pages().length;
  await planLink.click();
  await expect(page).toHaveURL(destination.href);

  const assertHistoricalPlan = async () => {
    await expect(
      page.getByRole("heading", { name: "Version 1 · APPROVED", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Neueste Version: 2 · DRAFT")).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Planversion", exact: true }),
    ).toHaveValue(planVersionId);
    await expect(page.getByRole("region", { name: "These" })).toContainText(
      historicalThesis,
    );
    await expect(page.getByText(latestThesis, { exact: true })).toHaveCount(0);
    expectReportContext(page.url(), context);
    expect(page.context().pages()).toHaveLength(originalTabCount);
  };
  await assertHistoricalPlan();
  await page.reload();
  await assertHistoricalPlan();
  // A copied ordinary href must work without any prior router/location state.
  await page.goto(destination.href);
  await assertHistoricalPlan();

  const returnLink = page.getByRole("link", {
    name: "Zurück zu den Tradequellen",
    exact: true,
  });
  const returnHref = await returnLink.getAttribute("href");
  expect(returnHref).not.toBeNull();
  expectReportContext(returnHref!, context);
  const returnUrl = new URL(returnHref!, page.url());
  expect(returnUrl.pathname).toBe("/trade-management");
  expect(returnUrl.searchParams.get("view")).toBe("sources");
  expect(returnUrl.hash).toBe("#trade-plan-sources");
  await returnLink.click();
  await expect(planSource).toBeFocused();
  await expect(planSource).toContainText(historicalThesis);
  await expect(page.getByText("Synthetic historical review R1")).toBeVisible();
  await expect(page.getByText("Synthetic historical journal J1")).toBeVisible();
  expectReportContext(page.url(), context);
  for (const [section, version] of [
    ["reviews", reviewVersionId],
    ["journal", journalVersionId],
  ]) {
    const reads = observed.reads.filter((url) =>
      url.includes(`/sources/${section}`),
    );
    expect(reads.length).toBeGreaterThanOrEqual(2);
    expect(
      reads.every((url) =>
        url.endsWith(`/sources/${section}?version_id=${version}`),
      ),
    ).toBe(true);
  }
  expect(
    observed.reads.filter((url) =>
      url.endsWith(`/trade-plans/${planId}/versions/${planVersionId}`),
    ).length,
  ).toBeGreaterThanOrEqual(3);
  expect(
    observed.reads.some((url) =>
      url.endsWith(`/trade-plans/${planId}/versions/${latestPlanVersionId}`),
    ),
  ).toBe(false);
  expect(observed.reads.some((url) => url.includes("/performance/"))).toBe(
    false,
  );
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});

test("a sales report keeps its exact selection through bookings, copied source links and the return at mobile width", async ({
  page,
}) => {
  const observed = await fixture(page, { reportJourney: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const context = reportQuery();
  const reportUrl = `/performance/realized-gross?${context}`;
  const sellId = "sell-september-2";
  await page.goto(reportUrl);
  const sale = page.getByRole("article", {
    name: `Verkauf ${sellId}`,
    exact: true,
  });
  await expect(sale).toContainText("-20,00 EUR");
  await sale
    .getByRole("button", { name: "Quellen und Berechnung", exact: true })
    .click();
  const reportSources = page.getByRole("region", {
    name: `Herkunft SELL ${sellId}`,
    exact: true,
  });
  await expect(
    reportSources.getByRole("listitem", {
      name: `Buchungsquelle ${sellId}`,
      exact: true,
    }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  const originalReportReads = observed.reads.filter((url) =>
    url.includes("/performance/"),
  );
  expect(originalReportReads.length).toBeGreaterThanOrEqual(1);
  const bookingsLink = reportSources.getByRole("link", {
    name: "Buchungen und Währungsbestätigungen im Trade prüfen",
    exact: true,
  });
  const bookingsHref = await bookingsLink.getAttribute("href");
  expect(bookingsHref).not.toBeNull();
  expectReportContext(bookingsHref!, context);
  expect(new URL(bookingsHref!, page.url()).hash).toBe("#execution-dates");
  await bookingsLink.click();
  await expect(page).toHaveURL(new URL(bookingsHref!, page.url()).href);
  await loaded(page, 5);
  await expect(page.locator("#execution-dates")).toBeFocused();
  await expect(
    page.getByRole("article", { name: `Buchung ${sellId}`, exact: true }),
  ).toBeVisible();
  expectReportContext(page.url(), context);
  expect(new URL(page.url()).searchParams.getAll("trade_id")).toEqual([
    tradeId,
  ]);
  await page.reload();
  await loaded(page, 5);
  await expect(page.locator("#execution-dates")).toBeFocused();
  expectReportContext(page.url(), context);

  const sourceLink = navigation(page).getByRole("link", {
    name: "Plan und Quellen",
    exact: true,
  });
  const copiedSourceHref = await sourceLink.getAttribute("href");
  expect(copiedSourceHref).not.toBeNull();
  expectReportContext(copiedSourceHref!, context);
  await sourceLink.click();
  const source = page.getByRole("article", {
    name: `Quelle ${sellId}`,
    exact: true,
  });
  await expect(source).toBeVisible();
  await expect(source).toContainText("Verkauf");
  await page.goto(new URL(copiedSourceHref!, page.url()).href);
  await expect(source).toBeVisible();
  await page.reload();
  await expect(source).toBeVisible();
  expectReportContext(page.url(), context);
  // A sales origin is navigation context, never a request for a closing report.
  expect(observed.reads.filter((url) => url.includes("/performance/"))).toEqual(
    originalReportReads,
  );
  await expect(
    page.getByText(/Ungültiger oder mehrdeutiger Abschlussberichtskontext/),
  ).toHaveCount(0);
  const returnLink = page
    .getByRole("navigation", { name: "Quellenansicht verlassen", exact: true })
    .getByRole("link", {
      name: "Zur ursprünglichen Verkaufsauswahl",
      exact: true,
    });
  const returnHref = await returnLink.getAttribute("href");
  expect(returnHref).toBe(reportUrl);
  await returnLink.click();
  await expect(page).toHaveURL(new URL(reportUrl, page.url()).href);
  await expect(sale).toContainText("-20,00 EUR");
  expectReportContext(page.url(), context);
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  await expect(page.getByLabel("Von (einschließlich)")).toHaveValue(
    "2026-09-01",
  );
  await expect(page.getByLabel("Bis (einschließlich)")).toHaveValue(
    "2026-09-30",
  );
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Europe/Berlin",
  );
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.waitForLoadState("networkidle");
  const returnedReportReads = observed.reads.filter((url) =>
    url.includes("/performance/"),
  );
  expect(returnedReportReads.length).toBeGreaterThan(
    originalReportReads.length,
  );
  expect(
    returnedReportReads.every((url) => url === originalReportReads[0]),
  ).toBe(true);
  expect(
    observed.reads.some((url) => url.includes("/performance/closed-trades")),
  ).toBe(false);
  expect(observed.writes).toEqual([]);
  expect(observed.browserErrors).toEqual([]);
});
