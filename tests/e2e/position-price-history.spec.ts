import {
  chromium,
  expect,
  test,
  type Page,
  type Route,
} from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { position } from "../../frontend/src/test/positionFixture";
import type { PositionPriceHistoryReport } from "../../frontend/src/features/operational_workspace/positionPriceHistory";

// Synthetic stored evidence only. Every API request is intercepted so these
// browser journeys cannot activate a provider or alter an existing position.
const observedAt = "2026-09-10T13:45:22Z";
const receivedAt = "2026-10-30T08:00:00Z";
const isin = "DE000VH2LU21";

function series(
  id = "frankfurt-last",
  currency = "EUR",
  provider = "FRANKFURT_QUOTES",
  price = "0.2312345678",
) {
  return {
    id,
    provider,
    identity_key: `verified-${id}`,
    warrant_listing_id: `listing-${id}`,
    isin,
    currency,
    venue_mic: "XFRA" as string | null,
    provider_exchange_code: "_FRA" as string | null,
    price_kind: "LAST_TRADE" as const,
    source_mode: "OFFICIAL_WEBSITE",
    points: [
      {
        id: `point-${id}`,
        observed_at: observedAt,
        price,
        captured_at: receivedAt as string | null,
        retrieved_at: receivedAt,
        status: "REFERENCE_ONLY",
        storage: "SAMPLE" as "SAMPLE" | "RETAINED",
        quote_time_basis: null,
      },
    ],
  };
}

function history(tradeId = "trade-a") {
  return {
    trade_id: tradeId,
    position_id: tradeId.replace("trade-", "position-"),
    warrant_id: tradeId.replace("trade-", "warrant-"),
    isin,
    window_start: null as string | null,
    window_end: "2026-10-30T09:00:00Z",
    sampling_policy: "FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1",
    sample_limit: 10000,
    samples_considered: 1,
    samples_available: 1,
    truncated: false,
    collection_started_at: receivedAt as string | null,
    excluded: {} as Record<string, number>,
    series: [series()],
    events: [] as Array<{
      id: string;
      side: "BUY" | "SELL";
      occurred_at: string | null;
      executed_on: string | null;
      execution_timezone: string | null;
      price: string;
      currency: string | null;
      currency_source: string;
      quantity: number;
      plottable: boolean;
      reason: string | null;
    }>,
  };
}

async function setup(
  page: Page,
  read: (route: Route, url: URL) => Promise<void>,
  managedStatus?: "OPEN" | "CLOSED" | "CANCELLED",
) {
  const reads: URL[] = [];
  const writes: string[] = [];
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== "GET") {
      writes.push(`${request.method()} ${url.pathname}`);
      return route.fulfill({
        status: 405,
        json: { message: "Read-only test" },
      });
    }
    if (url.pathname.endsWith("/price-history")) {
      reads.push(url);
      return read(route, url);
    }
    if (url.pathname.endsWith("/operational-workspace/actions")) {
      return route.fulfill({ json: { generated_at: receivedAt, actions: [] } });
    }
    if (url.pathname.endsWith("/operational-workspace/positions")) {
      return route.fulfill({
        json: {
          generated_at: receivedAt,
          positions: ["a", "b"].map((id) =>
            position({
              trade_id: `trade-${id}`,
              position_id: `position-${id}`,
              product_name: `Stored position ${id.toUpperCase()}`,
              product_isin: isin,
              target: `/trade-management?trade_id=trade-${id}`,
            }),
          ),
        },
      });
    }
    if (url.pathname.endsWith("/alert-projection")) {
      const tradeId = url.pathname.split("/").at(-2)!;
      return route.fulfill({
        json: {
          ...position().position_signal,
          trade_id: tradeId,
          position_id: tradeId.replace("trade-", "position-"),
        },
      });
    }
    if (managedStatus) {
      const fixture = managedTradeFixture(url.pathname, managedStatus);
      if (fixture !== undefined) return route.fulfill({ json: fixture });
    }
    return route.fulfill({
      status: 404,
      json: { message: "Outside the synthetic price-history fixture" },
    });
  });
  return { reads, writes, browserErrors };
}

// A separate synthetic, already recorded trade. These GET fixtures never book
// the executions below, and no provider or real holdings are used by the tests.
function managedTradeFixture(
  path: string,
  status: "OPEN" | "CLOSED" | "CANCELLED",
) {
  const tradeId = "trade-managed";
  const productId = "warrant-managed";
  if (path.endsWith(`/trade-position/trades/${tradeId}`)) {
    return {
      id: tradeId,
      product_id: productId,
      origin: "EXTERNAL",
      trade_plan_id: null,
      created_at: observedAt,
      cancelled_at: status === "CANCELLED" ? receivedAt : null,
      cancellation_reason:
        status === "CANCELLED" ? "Synthetic duplicate" : null,
    };
  }
  if (path.endsWith(`/trade-position/trades/${tradeId}/position`)) {
    return {
      id: "position-managed",
      trade_id: tradeId,
      product_id: productId,
      open_quantity: status === "OPEN" ? 6 : 0,
      cost_basis: status === "OPEN" ? "1.32" : "0",
      average_entry_price: "0.22",
      realized_gross_pnl: status === "OPEN" ? "0.16" : "0.46",
      opened_at: "2026-09-10T13:30:00Z",
      last_execution_at: "2026-09-12T14:00:00Z",
      closed_at: status === "CLOSED" ? "2026-09-12T14:00:00Z" : null,
      is_closed: status === "CLOSED",
      is_cancelled: status === "CANCELLED",
    };
  }
  if (path.endsWith(`/trade-position/trades/${tradeId}/management`)) {
    return {
      trade_id: tradeId,
      stop_price: null,
      target_price: null,
      thesis: "Synthetic historical display fixture",
      notes: [],
      last_event_at: observedAt,
    };
  }
  if (path.endsWith(`/trade-position/trades/${tradeId}/timeline`)) return [];
  if (path.endsWith(`/warrants/${productId}`)) {
    return {
      id: productId,
      underlying_id: "underlying-managed",
      issuer_id: "issuer-managed",
      display_name: "Synthetic retained historical warrant",
      isin,
      wkn: null,
      product_family: "WARRANT",
      lifecycle_status: "ACTIVE",
      version: 1,
      created_at: observedAt,
      updated_at: receivedAt,
    };
  }
  return undefined;
}

async function openPosition(page: Page, id = "a") {
  await page
    .locator(`tr[data-position-id="position-${id}"]`)
    .getByRole("button", { name: "Details", exact: true })
    .click();
  return page.getByRole("region", {
    name: "Positionskursverlauf",
    exact: true,
  });
}

for (const width of [1440, 390]) {
  test(`existing position: automatically show one retained original quote at ${width}px, without a fabricated line`, async ({
    page,
  }, testInfo) => {
    const evidence = history();
    evidence.samples_available = evidence.samples_considered = 0;
    evidence.collection_started_at = null;
    evidence.series[0].points[0].storage = "RETAINED";
    evidence.series[0].points[0].captured_at = null;
    const requests = await setup(page, async (route) => {
      await route.fulfill({ json: evidence });
    });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/workspace");
    const panel = await openPosition(page);
    await expect(
      panel.getByRole("heading", { name: "Historischer Positionskurs" }),
    ).toBeVisible();
    await expect(panel.getByLabel("Zeitraum")).toHaveValue("all");
    await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
    await expect(
      panel.locator(
        ".recharts-line-curve, .recharts-scatter-line, .recharts-area-curve",
      ),
    ).toHaveCount(0);
    await expect(panel).toContainText(
      "Zwischen den Punkten ist kein Kursverlauf belegt",
    );
    await expect(
      panel.getByRole("region", { name: "Kursbeobachtungen EUR", exact: true }),
    ).toBeVisible();
    await expect.poll(() => requests.reads.length).toBe(1);
    expect(requests.reads[0].pathname).toMatch(
      /\/trades\/trade-a\/price-history$/,
    );
    expect(requests.reads[0].searchParams.has("days")).toBe(false);

    await panel.getByText("Kursdaten und Quellen", { exact: true }).click();
    const table = panel.getByRole("region", {
      name: "Historische Kursdaten",
      exact: true,
    });
    await expect(table).toContainText("FRANKFURT_QUOTES");
    await expect(table).toContainText("verified-frankfurt-last");
    await expect(table).toContainText("0,2312345678");
    await expect(table.locator(`time[datetime="${observedAt}"]`)).toBeVisible();
    await expect(table.locator(`time[datetime="${receivedAt}"]`)).toBeVisible();
    await expect(
      table.getByRole("columnheader", { name: /Originalkurszeit/ }),
    ).toBeVisible();

    const bounds = await panel.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width + 1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const screenshot = testInfo.outputPath(
      `position-price-history-${width}.png`,
    );
    await panel.screenshot({ path: screenshot });
    await testInfo.attach(`position-price-history-${width}-synthetic`, {
      path: screenshot,
      contentType: "image/png",
    });
    expect(requests.writes).toEqual([]);
    expect(requests.browserErrors).toEqual([]);
  });
}

test("provider changes, sparse gaps and currencies stay separate; only a verified execution receives a marker", async ({
  page,
}) => {
  const evidence = history();
  evidence.samples_available = evidence.samples_considered = 4;
  evidence.series = [
    series("old-frankfurt", "EUR", "FRANKFURT_QUOTES", "0.2312345678"),
    series("new-issuer", "EUR", "JPMORGAN", "0.2412345678"),
    series("usd-listing", "USD", "FRANKFURT_QUOTES", "0.2512345678"),
  ];
  evidence.series[0].points.push({
    ...evidence.series[0].points[0],
    id: "after-unobserved-weeks",
    observed_at: "2026-10-29T13:45:22Z",
    price: "0.2412345678",
  });
  evidence.events = [
    {
      id: "exact-buy",
      side: "BUY",
      occurred_at: "2026-09-10T13:30:00Z",
      executed_on: null,
      execution_timezone: null,
      price: "0.2212345678",
      currency: "EUR",
      currency_source: "USER_CONFIRMED",
      quantity: 10,
      plottable: true,
      reason: null,
    },
    {
      id: "date-only-sale",
      side: "SELL",
      occurred_at: null,
      executed_on: "2026-09-11",
      execution_timezone: "Europe/Berlin",
      price: "0.2612345678",
      currency: "EUR",
      currency_source: "USER_CONFIRMED",
      quantity: 2,
      plottable: false,
      reason: "DATE_ONLY",
    },
    {
      id: "unknown-currency-sale",
      side: "SELL",
      occurred_at: "2026-09-11T09:00:00Z",
      executed_on: null,
      execution_timezone: null,
      price: "0.2712345678",
      currency: null,
      currency_source: "UNKNOWN",
      quantity: 1,
      plottable: false,
      reason: "CURRENCY_UNKNOWN",
    },
  ];
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  const euros = panel.getByRole("region", {
    name: "Kursbeobachtungen EUR",
    exact: true,
  });
  const dollars = panel.getByRole("region", {
    name: "Kursbeobachtungen USD",
    exact: true,
  });
  await expect(euros.locator(".recharts-scatter-symbol")).toHaveCount(4);
  await expect(dollars.locator(".recharts-scatter-symbol")).toHaveCount(1);
  await expect(euros).toContainText("FRANKFURT_QUOTES");
  await expect(euros).toContainText("JPMORGAN");
  await expect(
    panel.locator(".recharts-line-curve, .recharts-scatter-line"),
  ).toHaveCount(0);
  await panel
    .getByText("Kauf- und Verkaufsereignisse", { exact: true })
    .click();
  await expect(panel).toContainText("0,2612345678");
  await expect(panel).toContainText("0,2712345678");
  await expect(panel).toContainText("Währung unbekannt");
  await expect(panel).toContainText("Europe/Berlin");
  await expect(panel).toContainText("2026-09-11");
  // Neither a calendar day nor an unknown execution currency creates a point.
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(5);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("unusable historical observations show an empty state without offering empty ranges", async ({
  page,
}) => {
  const evidence = history();
  evidence.series = [];
  evidence.samples_available = evidence.samples_considered = 3;
  evidence.excluded = {
    TIMESTAMP_UNKNOWN: 1,
    TIME_INCONSISTENT: 1,
    REQUEST_FAILED: 1,
  };
  const requests = await setup(page, async (route, url) => {
    await route.fulfill({
      json: {
        ...evidence,
        window_start: url.searchParams.has("days")
          ? "2026-09-29T09:00:00Z"
          : null,
      },
    });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel).toContainText(
    "Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.",
  );
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(0);
  for (const days of ["7", "31", "90"]) {
    await expect(panel.locator(`option[value="${days}"]`)).toHaveJSProperty(
      "disabled",
      true,
    );
  }
  await expect(panel.locator('option[value="all"]')).toHaveJSProperty(
    "disabled",
    false,
  );
  expect(requests.reads).toHaveLength(1);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("available ranges use original quote times and remain keyboard selectable after a narrower read", async ({
  page,
}) => {
  const evidence = history();
  evidence.samples_available = evidence.samples_considered = 2;
  evidence.series[0].points.push({
    ...evidence.series[0].points[0],
    id: "within-31-days",
    observed_at: "2026-10-10T13:45:22Z",
    price: "0.2512345678",
  });
  const requests = await setup(page, async (route, url) => {
    const days = url.searchParams.get("days");
    const start = days
      ? Date.parse(evidence.window_end) - Number(days) * 86400000
      : null;
    await route.fulfill({
      json: {
        ...evidence,
        window_start: start === null ? null : new Date(start).toISOString(),
        series: evidence.series.map((item) => ({
          ...item,
          points: item.points.filter(
            (point) => start === null || Date.parse(point.observed_at) >= start,
          ),
        })),
      },
    });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(2);
  // Both observations were received today, but neither original quote is from
  // the last seven days. Receipt times must not enable a false recent history.
  await expect(panel.locator('option[value="7"]')).toHaveJSProperty(
    "disabled",
    true,
  );
  await expect(panel.locator('option[value="31"]')).toHaveJSProperty(
    "disabled",
    false,
  );
  await expect(panel.locator('option[value="90"]')).toHaveJSProperty(
    "disabled",
    false,
  );
  const range = panel.getByLabel("Zeitraum");
  await range.focus();
  await expect(range).toBeFocused();
  await range.press("ArrowDown");
  await expect(range).toHaveValue("31");
  await expect.poll(() => requests.reads.length).toBe(2);
  expect(requests.reads[1].searchParams.get("days")).toBe("31");
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  await expect(panel.locator('option[value="7"]')).toHaveJSProperty(
    "disabled",
    true,
  );
  await expect(panel.locator('option[value="90"]')).toHaveJSProperty(
    "disabled",
    false,
  );
  await range.selectOption("all");
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(2);
  expect(requests.reads).toHaveLength(3);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("historical venue MICs and provider market identifiers remain distinct and unknown venues are not inferred", async ({
  page,
}) => {
  const evidence = history();
  evidence.samples_available = evidence.samples_considered = 4;
  evidence.series = [
    {
      ...series("stuttgart", "EUR", "SYNTHETIC_PROVIDER"),
      venue_mic: "XSTU",
      provider_exchange_code: "_STU",
    },
    {
      ...series("frankfurt", "EUR", "SYNTHETIC_PROVIDER"),
      venue_mic: "XFRA",
      provider_exchange_code: "_FRA",
    },
    {
      ...series("unknown-venue", "EUR", "SYNTHETIC_PROVIDER"),
      venue_mic: null,
      provider_exchange_code: null,
    },
    {
      ...series("issuer", "EUR", "SYNTHETIC_ISSUER"),
      venue_mic: null,
      provider_exchange_code: "ISSUER",
      source_mode: "OFFICIAL_ISSUER_INDICATION",
    },
  ];
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(4);
  const legend = panel.getByRole("list", { name: "Kursquellen EUR" });
  await expect(legend).toContainText("Handelsplatz: XSTU (MIC)");
  await expect(legend).toContainText("Handelsplatz: XFRA (MIC)");
  await panel.getByText("Kursdaten und Quellen", { exact: true }).click();
  const table = panel.getByRole("region", { name: "Historische Kursdaten" });
  const stuttgart = table
    .getByRole("row")
    .filter({ hasText: "listing-stuttgart" });
  await expect(stuttgart).toContainText("Handelsplatz: XSTU (MIC)");
  await expect(stuttgart).toContainText("Providersegment: _STU");
  await expect(stuttgart).not.toContainText("XFRA");
  const frankfurt = table
    .getByRole("row")
    .filter({ hasText: "listing-frankfurt" });
  await expect(frankfurt).toContainText("Handelsplatz: XFRA (MIC)");
  await expect(frankfurt).toContainText("Providersegment: _FRA");
  const unknown = table
    .getByRole("row")
    .filter({ hasText: "listing-unknown-venue" });
  await expect(unknown).toContainText("Handelsplatz nicht belegt");
  await expect(unknown).not.toContainText("(MIC)");
  const issuer = table.getByRole("row").filter({ hasText: "listing-issuer" });
  await expect(issuer).toContainText(
    "Emittentenquelle · kein Börsenhandelsplatz",
  );
  await expect(issuer).not.toContainText("(MIC)");
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`closed trade keeps its historical chart, partial sale and final sale in the existing detail at ${width}px`, async ({
    page,
  }, testInfo) => {
    const evidence = history("trade-managed");
    evidence.samples_available = evidence.samples_considered = 2;
    evidence.series[0].points.push({
      ...evidence.series[0].points[0],
      id: "before-final-sale",
      observed_at: "2026-09-12T13:45:22Z",
      price: "0.2712345678",
    });
    evidence.events = [
      {
        id: "managed-buy",
        side: "BUY",
        occurred_at: "2026-09-10T13:30:00Z",
        executed_on: null,
        execution_timezone: null,
        price: "0.22",
        currency: "EUR",
        currency_source: "USER_CONFIRMED",
        quantity: 10,
        plottable: true,
        reason: null,
      },
      {
        id: "managed-partial-sale",
        side: "SELL",
        occurred_at: "2026-09-11T14:00:00Z",
        executed_on: null,
        execution_timezone: null,
        price: "0.26",
        currency: "EUR",
        currency_source: "USER_CONFIRMED",
        quantity: 4,
        plottable: true,
        reason: null,
      },
      {
        id: "managed-final-sale",
        side: "SELL",
        occurred_at: "2026-09-12T14:00:00Z",
        executed_on: null,
        execution_timezone: null,
        price: "0.27",
        currency: "EUR",
        currency_source: "USER_CONFIRMED",
        quantity: 6,
        plottable: true,
        reason: null,
      },
    ];
    const requests = await setup(
      page,
      async (route) => {
        await route.fulfill({ json: evidence });
      },
      "CLOSED",
    );
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/trade-management?trade_id=trade-managed");
    await expect(
      page.getByRole("heading", { name: "CLOSED", exact: true }),
    ).toBeVisible();
    const detail = page.getByRole("region", {
      name: "Trade und Position",
      exact: true,
    });
    const panel = detail.getByRole("region", {
      name: "Positionskursverlauf",
      exact: true,
    });
    await expect(panel).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Positionskursverlauf", exact: true }),
    ).toHaveCount(1);
    await expect(panel.getByLabel("Zeitraum")).toHaveValue("all");
    await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(5);
    await expect(
      panel.locator(".recharts-line-curve, .recharts-scatter-line"),
    ).toHaveCount(0);
    await expect(panel).toContainText(
      "Buchungspreise sind keine Marktbeobachtungen",
    );
    await expect(panel.locator('option[value="7"]')).toHaveJSProperty(
      "disabled",
      true,
    );
    await expect(panel.locator('option[value="31"]')).toHaveJSProperty(
      "disabled",
      true,
    );
    await expect(panel.locator('option[value="90"]')).toHaveJSProperty(
      "disabled",
      false,
    );
    await panel
      .getByText("Kauf- und Verkaufsereignisse", { exact: true })
      .click();
    await expect(
      panel.getByText("Kauf · 10 Stück · 0,22 EUR", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByText("Verkauf · 4 Stück · 0,26 EUR", { exact: true }),
    ).toBeVisible();
    await expect(
      panel.getByText("Verkauf · 6 Stück · 0,27 EUR", { exact: true }),
    ).toBeVisible();
    await expect(
      detail
        .getByText("Offene Menge", { exact: true })
        .locator("..")
        .locator("dd"),
    ).toHaveText("0");
    await expect.poll(() => requests.reads.length).toBe(1);
    expect(requests.reads[0].pathname).toMatch(
      /\/trades\/trade-managed\/price-history$/,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const screenshot = testInfo.outputPath(
      `closed-position-price-history-${width}.png`,
    );
    await panel.screenshot({ path: screenshot });
    await testInfo.attach(`closed-position-price-history-${width}-synthetic`, {
      path: screenshot,
      contentType: "image/png",
    });
    expect(requests.writes).toEqual([]);
    expect(requests.browserErrors).toEqual([]);
  });
}

test("reloading the same managed position refreshes its historical evidence without writing", async ({
  page,
}) => {
  let price = "0.2312345678";
  const requests = await setup(
    page,
    async (route) => {
      const evidence = history("trade-managed");
      evidence.series[0].points[0].price = price;
      await route.fulfill({ json: evidence });
    },
    "CLOSED",
  );
  await page.goto("/trade-management?trade_id=trade-managed");
  const panel = page.getByRole("region", {
    name: "Positionskursverlauf",
    exact: true,
  });
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  await panel.getByText("Kursdaten und Quellen", { exact: true }).click();
  await expect(panel).toContainText("0,2312345678");
  price = "0.2912345678";
  await page.getByRole("button", { name: "Laden", exact: true }).click();
  await expect.poll(() => requests.reads.length).toBe(2);
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  // The evidence table may be re-mounted as part of invalidating the old view.
  const summary = panel.getByText("Kursdaten und Quellen", { exact: true });
  if ((await summary.locator("..").getAttribute("open")) === null)
    await summary.click();
  await expect(panel).toContainText("0,2912345678");
  await expect(panel).not.toContainText("0,2312345678");
  await expect(
    page.getByRole("heading", { name: "CLOSED", exact: true }),
  ).toBeVisible();
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("a cancelled trade keeps its audit context without requesting or showing a position chart", async ({
  page,
}) => {
  const requests = await setup(
    page,
    async (route) => {
      await route.fulfill({ json: history("trade-managed") });
    },
    "CANCELLED",
  );
  await page.goto("/trade-management?trade_id=trade-managed");
  await expect(
    page.getByRole("heading", { name: "CANCELLED", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Trade und Position", exact: true }),
  ).toContainText("Storniert – kein Bestand");
  await expect(
    page.getByRole("region", { name: "Positionskursverlauf", exact: true }),
  ).toHaveCount(0);
  expect(requests.reads).toEqual([]);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("a bounded stored sample is explicitly incomplete while preserving its real point", async ({
  page,
}) => {
  const evidence = history();
  evidence.samples_available = 10001;
  evidence.samples_considered = 10000;
  evidence.truncated = true;
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel).toContainText(
    "Begrenzter Ausschnitt: 10000 von 10001 gespeicherten Stichproben geprüft",
  );
  await expect(panel).toContainText("Ältere Belege können fehlen");
  await expect(panel).toContainText(
    "Dieser Ausschnitt belegt keine vollständige Historie",
  );
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  await expect(
    panel.locator(".recharts-line-curve, .recharts-scatter-line"),
  ).toHaveCount(0);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("loading failure is distinct from no data and retry reads stored evidence", async ({
  page,
}) => {
  let calls = 0;
  const requests = await setup(page, async (route) => {
    calls += 1;
    await route.fulfill(
      calls === 1
        ? { status: 503, json: { message: "Synthetic unavailable storage" } }
        : { json: history() },
    );
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel.getByRole("alert")).toContainText(
    "Kursverlauf konnte nicht geladen werden.",
  );
  await expect(panel).not.toContainText(
    "Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.",
  );
  await panel.getByRole("button", { name: "Kursverlauf erneut laden" }).click();
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  await expect(panel.getByRole("alert")).toHaveCount(0);
  expect(requests.reads).toHaveLength(2);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("a late response for position A cannot overwrite the opened position B", async ({
  page,
}) => {
  let releaseA: () => void = () => {};
  const waitingForA = new Promise<void>((resolve) => {
    releaseA = resolve;
  });
  let aStarted = false;
  let aFinished = false;
  const requests = await setup(page, async (route, url) => {
    if (url.pathname.includes("/trade-a/")) {
      aStarted = true;
      await waitingForA;
      const evidence = history();
      evidence.series = [series("late-a", "EUR", "LATE_A_PROVIDER")];
      await route.fulfill({ json: evidence });
      aFinished = true;
    } else {
      const evidence = history("trade-b");
      evidence.series = [series("b", "EUR", "CURRENT_B_PROVIDER")];
      await route.fulfill({ json: evidence });
    }
  });
  const panel = page.getByRole("region", {
    name: "Positionskursverlauf",
    exact: true,
  });
  try {
    await page.goto("/workspace");
    await openPosition(page);
    await expect.poll(() => aStarted).toBe(true);
    await openPosition(page, "b");
    await expect(panel).toContainText("CURRENT_B_PROVIDER");
  } finally {
    releaseA();
  }
  await expect.poll(() => aFinished).toBe(true);
  await expect(
    page.getByRole("region", {
      name: "Details Stored position B",
      exact: true,
    }),
  ).toBeVisible();
  await expect(panel).toContainText("CURRENT_B_PROVIDER");
  await expect(panel).not.toContainText("LATE_A_PROVIDER");
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(1);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

// Explicit synthetic stress evidence: different historical source identities
// share original coordinates. These values are never user/provider history.
function manySourceHistory(
  withEarlierPoints = false,
): PositionPriceHistoryReport {
  const evidence: PositionPriceHistoryReport = history();
  const exactPrice = "0.231234567890123456789";
  const kinds = ["BID", "ASK", "LAST_TRADE", "PREVIOUS_CLOSE"] as const;
  const modes = [
    "OFFICIAL_WEBSITE",
    "OFFICIAL_ISSUER_INDICATION",
    "SYNTHETIC_HISTORICAL_MODE",
    null,
  ];
  evidence.series = Array.from({ length: 14 }, (_, index) => ({
    ...series(
      "synthetic-source-" + index + "-" + "x".repeat(80),
      "EUR",
      "SYNTHETIC_PROVIDER_" + (index % 3) + "_MIT_LANGER_QUELLENKENNUNG",
      exactPrice,
    ),
    price_kind: kinds[index % kinds.length],
    source_mode: modes[index % modes.length],
    venue_mic: index % 4 < 2 ? ["XFRA", "XSTU"][index % 4] : null,
    provider_exchange_code:
      index % 4 === 2 ? "ISSUER" : index % 4 === 3 ? null : "_FRA_" + index,
  }));
  if (withEarlierPoints) {
    const first = evidence.series[0];
    first.points = [
      ...Array.from({ length: 55 }, (_, index) => ({
        ...first.points[0],
        id: "earlier-synthetic-point-" + index,
        observed_at: new Date(
          Date.parse(observedAt) - (55 - index) * 3600000,
        ).toISOString(),
        price: "0.20",
      })),
      first.points[0],
    ];
  }
  evidence.series.push(
    series("separate-usd-source", "USD", "SYNTHETIC_USD_PROVIDER", "0.25"),
  );
  evidence.events = [
    {
      id: "synthetic-overlap-buy",
      side: "BUY",
      occurred_at: observedAt,
      executed_on: null,
      execution_timezone: null,
      price: exactPrice,
      currency: "EUR",
      currency_source: "USER_CONFIRMED",
      quantity: 10,
      plottable: true,
      reason: null,
    },
    {
      id: "synthetic-overlap-sell",
      side: "SELL",
      occurred_at: observedAt,
      executed_on: null,
      execution_timezone: null,
      price: exactPrice,
      currency: "EUR",
      currency_source: "HISTORICAL_LISTING",
      quantity: 2,
      plottable: true,
      reason: null,
    },
    {
      id: "synthetic-calendar-sale",
      side: "SELL",
      occurred_at: null,
      executed_on: "2026-09-11",
      execution_timezone: "Europe/Berlin",
      price: "0.271234567890123456789",
      currency: "EUR",
      currency_source: "USER_CONFIRMED",
      quantity: 1,
      plottable: false,
      reason: "DATE_ONLY",
    },
  ];
  evidence.samples_considered = 10000;
  evidence.samples_available = 10001;
  evidence.truncated = true;
  return evidence;
}

for (const width of [320, 390, 1280]) {
  test(
    "UX4-B synthetic many-source legend supports keyboard hiding and restoration at " +
      width +
      "px",
    async ({ page }, testInfo) => {
      const evidence = manySourceHistory();
      const apiRequests: string[] = [];
      page.on("request", (request) => {
        if (new URL(request.url()).pathname.startsWith("/api/"))
          apiRequests.push(request.method() + " " + request.url());
      });
      const requests = await setup(page, async (route) => {
        await route.fulfill({ json: evidence });
      });
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/workspace");
      const panel = await openPosition(page);
      const euros = panel.getByRole("region", {
        name: "Kursbeobachtungen EUR",
        exact: true,
      });
      const sourceSummary = euros.getByText(
        "Kursquellen EUR ein-/ausblenden (14)",
        { exact: true },
      );
      await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(17);
      const compactScreenshot = testInfo.outputPath(
        "ux4-b-compact-chart-" + width + "-synthetic.png",
      );
      await euros.screenshot({ path: compactScreenshot });
      await testInfo.attach("UX4-B synthetic compact chart " + width + "px", {
        path: compactScreenshot,
        contentType: "image/png",
      });
      await sourceSummary.focus();
      await page.keyboard.press("Enter");
      const legend = euros.getByRole("list", { name: "Kursquellen EUR" });
      await expect(legend.getByRole("checkbox")).toHaveCount(14);
      await expect(panel.getByRole("checkbox")).toHaveCount(15);
      await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(17);
      for (const kind of [
        "Geldkurs",
        "Briefkurs",
        "Letzter Handel",
        "Vorheriger Schlusskurs",
      ]) {
        await expect(legend).toContainText(kind);
      }
      await expect(legend).toContainText("Handelsplatz nicht belegt");
      await expect(legend).toContainText(
        "Emittentenquelle · kein Börsenhandelsplatz",
      );
      await expect(panel).toContainText(
        "Zur Anzeige ausgewählt: 15 von 15 gelieferten Marktkurspunkten.",
      );
      await expect(panel).toContainText(
        "Belegte Kurszeiten aller gelieferten Quellen:",
      );
      await expect(panel).toContainText(
        "10000 von 10001 gespeicherten Stichproben",
      );
      await page.waitForLoadState("networkidle");
      const originalRequests = [...apiRequests];

      const firstSource = legend.getByRole("checkbox").first();
      await firstSource.focus();
      await page.keyboard.press("Space");
      await expect(firstSource).not.toBeChecked();
      await expect(firstSource).toBeFocused();
      expect(
        await firstSource.evaluate((element) => {
          const style = getComputedStyle(element);
          return (
            element.matches(":focus-visible") &&
            style.outlineStyle !== "none" &&
            parseFloat(style.outlineWidth) >= 2
          );
        }),
      ).toBe(true);
      await expect(panel).toContainText(
        "Zur Anzeige ausgewählt: 14 von 15 gelieferten Marktkurspunkten.",
      );
      await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(16);

      const sourceDetails = legend.getByText("Quellenkennung 1", {
        exact: true,
      });
      await page.keyboard.press("Tab");
      await expect(sourceDetails).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(
        legend.getByText("Serie: " + evidence.series[0].id, { exact: true }),
      ).toBeVisible();
      await page.keyboard.press("Enter");
      await page.keyboard.press("Shift+Tab");
      await expect(firstSource).toBeFocused();

      // Every native checkbox remains operable even after its plot is empty.
      const boxes = panel.getByRole("checkbox");
      for (let index = 1; index < (await boxes.count()); index += 1) {
        await boxes.nth(index).focus();
        await page.keyboard.press("Space");
        await expect(boxes.nth(index)).not.toBeChecked();
      }
      await expect(panel.getByRole("status")).toContainText(
        "Alle Kursquellen sind für das Diagramm ausgeblendet.",
      );
      await expect(panel).not.toContainText(
        "Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.",
      );
      await expect(panel).toContainText(
        "Zur Anzeige ausgewählt: 0 von 15 gelieferten Marktkurspunkten.",
      );
      // BUY and SELL keep their owner-qualified markers after all market sources hide.
      await expect(euros.locator(".recharts-scatter-symbol")).toHaveCount(2);
      const eventSummary = panel.getByText("Kauf- und Verkaufsereignisse", {
        exact: true,
      });
      await eventSummary.focus();
      await page.keyboard.press("Enter");
      await expect(
        panel.getByText("Kauf · 10 Stück · 0,231234567890123456789 EUR", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        panel.getByText("Verkauf · 2 Stück · 0,231234567890123456789 EUR", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(panel).toContainText("Nur Ausführungsdatum bekannt");
      await expect(panel).toContainText("Europe/Berlin");
      const tableSummary = panel.getByText("Kursdaten und Quellen", {
        exact: true,
      });
      await tableSummary.focus();
      await page.keyboard.press("Space");
      const table = panel.getByRole("region", {
        name: "Historische Kursdaten",
        exact: true,
      });
      await expect(table.getByRole("row")).toHaveCount(16);
      await expect(table).toContainText(evidence.series[0].id);
      await expect(table).toContainText("0,231234567890123456789");
      await expect(
        table.getByRole("columnheader", { name: "Kurs", exact: true }),
      ).toBeVisible();
      expect(
        await table.evaluate((element) => getComputedStyle(element).overflowX),
      ).toBe("auto");

      const restore = panel.getByRole("button", {
        name: "Alle Kursquellen anzeigen",
        exact: true,
      });
      await restore.focus();
      await page.keyboard.press("Enter");
      await expect(restore).toBeFocused();
      await expect(panel.getByRole("status")).toHaveCount(0);
      await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(17);
      for (let index = 0; index < (await boxes.count()); index += 1) {
        await expect(boxes.nth(index)).toBeChecked();
      }
      await firstSource.focus();
      await expect(firstSource).toBeFocused();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth + 1,
          ),
        )
        .toBe(true);
      const screenshot = testInfo.outputPath(
        "ux4-b-many-sources-" + width + "-synthetic.png",
      );
      await euros.screenshot({ path: screenshot });
      await testInfo.attach(
        "UX4-B synthetic sources and keyboard focus " + width + "px",
        {
          path: screenshot,
          contentType: "image/png",
        },
      );
      expect(apiRequests).toEqual(originalRequests);
      expect(requests.reads).toHaveLength(1);
      expect(requests.writes).toEqual([]);
      expect(requests.browserErrors).toEqual([]);
    },
  );
}

test("UX4-B overlapping market and execution points retain every exact original and focus table page two", async ({
  page,
}, testInfo) => {
  const evidence = manySourceHistory(true);
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  const euros = panel.getByRole("region", {
    name: "Kursbeobachtungen EUR",
    exact: true,
  });
  await expect(euros.locator(".recharts-scatter-symbol")).toHaveCount(71);
  await euros
    .getByText("Kursquellen EUR ein-/ausblenden (14)", { exact: true })
    .click();
  // Hide one source, then use the real topmost SELL marker at the shared coordinates.
  await euros.getByRole("checkbox").nth(1).uncheck();
  await euros.locator(".recharts-scatter-symbol").last().click();
  const overlap = euros.getByRole("heading", {
    name: "Belege an diesem Diagrammpunkt: 16",
    exact: true,
  });
  await expect(overlap).toBeFocused();
  const choices = euros.getByRole("list", {
    name: "Einzelbelege EUR",
    exact: true,
  });
  await expect(choices.getByRole("button")).toHaveCount(16);
  await expect(choices).toContainText("Quelle im Diagramm ausgeblendet");

  for (let source = 0; source < 14; source += 1) {
    const point = evidence.series[source].points.at(-1)!;
    const button = choices.getByRole("button", {
      name: new RegExp("^Quelle " + (source + 1) + ", Kurspunkt "),
    });
    await button.focus();
    await page.keyboard.press(source % 2 === 0 ? "Enter" : "Space");
    const original = panel.getByRole("region", {
      name: "Ausgewählter Originalkursbeleg",
      exact: true,
    });
    await expect(original).toBeFocused();
    await expect(original).toContainText("0,231234567890123456789 EUR");
    await expect(
      original.locator('time[datetime="' + observedAt + '"]'),
    ).toBeVisible();
    const technical = original.getByText(
      "Technische Angaben zum ausgewählten Kursbeleg",
      { exact: true },
    );
    if ((await technical.locator("..").getAttribute("open")) === null) {
      await technical.focus();
      await page.keyboard.press("Enter");
    }
    await expect(original).toContainText(
      "Serien-ID: " + evidence.series[source].id,
    );
    await expect(original).toContainText("Punkt-ID: " + point.id);
    await expect(panel.getByText("Seite 2 / 2", { exact: true })).toBeVisible();
    const row = panel
      .getByRole("region", { name: "Historische Kursdaten", exact: true })
      .getByRole("row")
      .filter({ hasText: "Punkt-ID: " + point.id });
    await expect(row).toHaveCount(1);
    await expect(row).toContainText("Serien-ID: " + evidence.series[source].id);
  }
  for (const [side, id, quantity, source] of [
    ["Kauf", "synthetic-overlap-buy", "10", "USER_CONFIRMED"],
    ["Verkauf", "synthetic-overlap-sell", "2", "HISTORICAL_LISTING"],
  ]) {
    const button = choices.getByRole("button", {
      name: new RegExp("^" + side + ", Buchung "),
    });
    await button.focus();
    await page.keyboard.press("Enter");
    const event = panel
      .getByRole("listitem")
      .filter({ hasText: "Buchung " + id + " · Währungsherkunft:" });
    await expect(event).toHaveCount(1);
    await expect(event).toBeFocused();
    await expect(event).toContainText(
      side + " · " + quantity + " Stück · 0,231234567890123456789 EUR",
    );
    await expect(event).toContainText(source);
    await expect(
      event.locator('time[datetime="' + observedAt + '"]'),
    ).toBeVisible();
  }
  await expect(
    panel.locator(".recharts-line-curve, .recharts-scatter-line"),
  ).toHaveCount(0);
  await expect(panel).toContainText("Nur Ausführungsdatum bekannt");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
  const screenshot = testInfo.outputPath(
    "ux4-b-overlap-originals-390-synthetic.png",
  );
  await choices.screenshot({ path: screenshot });
  await testInfo.attach(
    "UX4-B synthetic overlapping original evidence at 390px",
    {
      path: screenshot,
      contentType: "image/png",
    },
  );
  expect(requests.reads).toHaveLength(1);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("UX4-B a chart render failure preserves keyboard access to every original quote and execution", async ({
  page,
}) => {
  const evidence: PositionPriceHistoryReport = history();
  const original = evidence.series[0].points[0];
  evidence.series[0].points = Array.from({ length: 51 }, (_, index) => ({
    ...original,
    id: "synthetic-chart-failure-point-" + index,
    observed_at: new Date(Date.parse(observedAt) + index * 60000).toISOString(),
    price: "0.231234567890123456789",
  }));
  evidence.samples_available = evidence.samples_considered = 51;
  evidence.events = [
    ...manySourceHistory().events,
    {
      id: "synthetic-chart-failure-currency-unknown",
      side: "SELL",
      occurred_at: observedAt,
      executed_on: null,
      execution_timezone: null,
      price: "0.281234567890123456789",
      currency: null,
      currency_source: "UNKNOWN",
      quantity: 1,
      plottable: false,
      reason: "CURRENCY_UNKNOWN",
    },
  ];
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/"))
      apiRequests.push(request.method() + " " + request.url());
  });
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  let replacedChartChunks = 0;
  // Isolate a genuine render exception at the optional production module
  // boundary. The stored API evidence itself remains valid and unmodified.
  await page.route(
    /\/assets\/PositionPricePlot-[^/]+\.js(?:\?.*)?$/,
    async (route) => {
      replacedChartChunks += 1;
      await route.fulfill({
        contentType: "application/javascript",
        body: 'export function PositionPricePlot() { throw new Error("Synthetic chart render failure"); }',
      });
    },
  );
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel.getByRole("alert")).toHaveCount(1);
  await expect(panel.getByRole("alert")).toContainText(
    "Das Diagramm konnte nicht dargestellt werden.",
  );
  await expect(panel).not.toContainText(
    "Das Diagramm konnte nicht geladen werden.",
  );
  expect(replacedChartChunks).toBe(1);
  await expect(panel).not.toContainText(
    "Kursverlauf konnte nicht geladen werden.",
  );
  await expect(panel).not.toContainText(
    "Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.",
  );
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  const originalRequests = [...apiRequests];

  const tableSummary = panel.getByText("Kursdaten und Quellen", {
    exact: true,
  });
  await tableSummary.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  const table = panel.getByRole("region", {
    name: "Historische Kursdaten",
    exact: true,
  });
  await expect(table).toBeFocused();
  expect(
    await table.evaluate((element) => {
      const style = getComputedStyle(element);
      return (
        element.matches(":focus-visible") &&
        style.outlineStyle !== "none" &&
        parseFloat(style.outlineWidth) >= 2 &&
        style.overflowX === "auto"
      );
    }),
  ).toBe(true);
  await expect(table.getByRole("row")).toHaveCount(51);
  await expect(table).toContainText("0,231234567890123456789 EUR");
  await expect(table).toContainText(
    "Punkt-ID: synthetic-chart-failure-point-0",
  );
  await expect(table).toContainText(
    "Punkt-ID: synthetic-chart-failure-point-49",
  );
  await page.keyboard.press("ArrowRight");
  await expect
    .poll(() => table.evaluate((element) => element.scrollLeft))
    .toBeGreaterThan(0);
  await page.keyboard.press("Tab");
  const nextPage = panel.getByRole("button", {
    name: "Weitere Kurspunkte",
    exact: true,
  });
  await expect(nextPage).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(panel.getByText("Seite 2 / 2", { exact: true })).toBeVisible();
  await expect(table.getByRole("row")).toHaveCount(2);
  await expect(table).toContainText(
    "Punkt-ID: synthetic-chart-failure-point-50",
  );
  await expect(table).toContainText("Serien-ID: " + evidence.series[0].id);
  await expect(table).toContainText("0,231234567890123456789 EUR");

  const eventsSummary = panel.getByText("Kauf- und Verkaufsereignisse", {
    exact: true,
  });
  await eventsSummary.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("Tab");
  const sourceSummaries = panel.getByText(
    "Buchungsbeleg und Währungsherkunft",
    { exact: true },
  );
  await expect(sourceSummaries.first()).toBeFocused();
  for (let index = 0; index < evidence.events.length; index += 1) {
    if (index > 0) await page.keyboard.press("Tab");
    await expect(sourceSummaries.nth(index)).toBeFocused();
    await page.keyboard.press("Enter");
    const event = evidence.events[index];
    await expect(
      panel.getByText(
        "Buchung " + event.id + " · Währungsherkunft: " + event.currency_source,
        {
          exact: true,
        },
      ),
    ).toBeVisible();
  }
  await expect(panel).toContainText(
    "Kauf · 10 Stück · 0,231234567890123456789 EUR",
  );
  await expect(panel).toContainText(
    "Verkauf · 2 Stück · 0,231234567890123456789 EUR",
  );
  await expect(panel).toContainText(
    "Ausgeführt am 2026-09-11 · Uhrzeit unbekannt · Europe/Berlin",
  );
  await expect(panel).toContainText(
    "Kein Diagrammmarker: Nur Ausführungsdatum bekannt.",
  );
  await expect(panel).toContainText(
    "Verkauf · 1 Stück · 0,281234567890123456789 Währung unbekannt",
  );
  await expect(panel).toContainText(
    "Kein Diagrammmarker: Währung nicht belegt.",
  );
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
  expect(apiRequests).toEqual(originalRequests);
  expect(requests.reads).toHaveLength(1);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});

test("UX4-B uses actual Chromium 200 and 400 percent page zoom with keyboard evidence and no additional reads", async ({
  baseURL,
}, testInfo) => {
  // Test-only MV3 extension exercises the browser's native page-zoom API.
  // No CSS zoom, device scaling or viewport substitution qualifies this check.
  const extension = testInfo.outputPath("synthetic-zoom-extension");
  await mkdir(extension, { recursive: true });
  await writeFile(
    extension + "/manifest.json",
    JSON.stringify({
      manifest_version: 3,
      name: "Synthetic UX4-B native browser zoom test",
      version: "1.0",
      permissions: ["tabs"],
      background: { service_worker: "worker.js" },
    }),
  );
  await writeFile(
    extension + "/worker.js",
    "chrome.runtime.onInstalled.addListener(() => {});\n",
  );
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const context = await chromium.launchPersistentContext(
    testInfo.outputPath("synthetic-zoom-profile"),
    {
      ...(executablePath ? { executablePath } : {}),
      headless: false,
      viewport: { width: 1280, height: 900 },
      args: [
        "--headless=new",
        "--disable-extensions-except=" + extension,
        "--load-extension=" + extension,
      ],
    },
  );
  try {
    const worker =
      context.serviceWorkers()[0] ??
      (await context.waitForEvent("serviceworker"));
    const page = context.pages()[0] ?? (await context.newPage());
    await page.bringToFront();
    const evidence = manySourceHistory();
    evidence.excluded = { TIMESTAMP_UNKNOWN: 2 };
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.startsWith("/api/"))
        apiRequests.push(request.method() + " " + request.url());
    });
    const requests = await setup(page, async (route) => {
      await route.fulfill({ json: evidence });
    });
    await page.goto((baseURL ?? "http://127.0.0.1:8080") + "/workspace");
    const panel = await openPosition(page);
    await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(17);
    const before = await page.evaluate(() => ({
      width: window.innerWidth,
      ratio: window.devicePixelRatio,
    }));
    const setPageZoom = (factor: number) =>
      worker.evaluate(
        async ({ origin, factor }) => {
          const tabs = (
            globalThis as unknown as {
              chrome: {
                tabs: {
                  query: (query: {
                    url: string;
                  }) => Promise<Array<{ id: number }>>;
                  setZoom: (id: number, factor: number) => Promise<void>;
                  getZoom: (id: number) => Promise<number>;
                };
              };
            }
          ).chrome.tabs;
          const matches = await tabs.query({ url: origin + "/*" });
          if (matches.length !== 1)
            throw new Error("Expected one synthetic application tab");
          await tabs.setZoom(matches[0].id, factor);
          return tabs.getZoom(matches[0].id);
        },
        { origin: new URL(page.url()).origin, factor },
      );
    const zoom = await setPageZoom(2);
    expect(zoom).toBe(2);
    await expect
      .poll(() => page.evaluate(() => window.innerWidth))
      .toBe(before.width / 2);
    await expect
      .poll(() => page.evaluate(() => window.devicePixelRatio))
      .toBe(before.ratio * 2);
    await page.waitForLoadState("networkidle");
    expect(requests.reads).toHaveLength(1);
    const originalRequests = [...apiRequests];

    const euros = panel.getByRole("region", {
      name: "Kursbeobachtungen EUR",
      exact: true,
    });
    const sourceSummary = euros.getByText(
      "Kursquellen EUR ein-/ausblenden (14)",
      { exact: true },
    );
    await sourceSummary.focus();
    await page.keyboard.press("Enter");
    const source = euros.getByRole("checkbox").first();
    await source.focus();
    await page.keyboard.press("Space");
    await expect(source).not.toBeChecked();
    await expect(source).toBeFocused();
    await expect(panel).toContainText(
      "Zur Anzeige ausgewählt: 14 von 15 gelieferten Marktkurspunkten.",
    );
    await sourceSummary.focus();
    await page.keyboard.press("Enter");
    const picker = euros.getByText("Punkte und Buchungen auswählen (EUR)", {
      exact: true,
    });
    await picker.focus();
    await page.keyboard.press("Enter");
    const choice = euros.getByRole("button", {
      name: /^Quelle 2, Kurspunkt 1:/,
    });
    await choice.focus();
    await page.keyboard.press("Space");
    const selected = panel.getByRole("region", {
      name: "Ausgewählter Originalkursbeleg",
      exact: true,
    });
    await expect(selected).toBeFocused();
    await expect(selected).toContainText("0,231234567890123456789 EUR");
    await expect(selected).toContainText("Briefkurs");
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);
    const screenshot = testInfo.outputPath(
      "ux4-b-native-200-percent-synthetic.png",
    );
    // Native zoom changes compositor coordinates. Capture the browser viewport
    // directly instead of asking Playwright to clip an unzoomed element box.
    await selected.evaluate((element) =>
      element.scrollIntoView({ block: "center" }),
    );
    await page.evaluate(
      () =>
        new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        }),
    );
    const captureSession = await context.newCDPSession(page);
    const capture = await captureSession.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: false,
      captureBeyondViewport: false,
    });
    await writeFile(screenshot, Buffer.from(capture.data, "base64"));
    await captureSession.detach();
    await testInfo.attach(
      "UX4-B synthetic original evidence at verified native 200% browser zoom",
      {
        path: screenshot,
        contentType: "image/png",
      },
    );
    const measurements = testInfo.outputPath(
      "ux4-b-native-zoom-measurements.json",
    );
    await writeFile(
      measurements,
      JSON.stringify(
        {
          before,
          nativeZoomFactor: zoom,
          after: await page.evaluate(() => ({
            width: window.innerWidth,
            ratio: window.devicePixelRatio,
            documentWidth: document.documentElement.scrollWidth,
          })),
        },
        null,
        2,
      ),
    );
    await testInfo.attach("Native browser zoom measurements", {
      path: measurements,
      contentType: "application/json",
    });

    // V12 / Q24 additionally qualify the compact, evidence-bound notices at
    // native 400% zoom. The complete 200% journey and its artifacts stay intact.
    const noticeZoom = await setPageZoom(4);
    // Chromium's logarithmic zoom conversion returns 3.9999999999999996 for
    // setZoom(4). Preserve that raw evidence and compare within IEEE precision.
    expect(noticeZoom).toBeCloseTo(4, 12);
    await expect
      .poll(() => page.evaluate(() => window.innerWidth))
      .toBe(before.width / 4);
    await expect
      .poll(() => page.evaluate(() => window.devicePixelRatio))
      .toBeCloseTo(before.ratio * 4, 12);
    const truncation = panel.getByText(/^Begrenzter Ausschnitt:/);
    const exclusion = panel.getByText("Originalkurszeit unbekannt: 2", {
      exact: true,
    });
    await expect(truncation).toContainText("10000 von 10001");
    await expect(truncation).toContainText("Ältere Belege können fehlen");
    await expect(exclusion).toBeVisible();
    const eventSummary = panel.getByText("Kauf- und Verkaufsereignisse", {
      exact: true,
    });
    await eventSummary.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    await expect(
      panel
        .getByText("Buchungsbeleg und Währungsherkunft", { exact: true })
        .first(),
    ).toBeFocused();
    const dateEvent = panel
      .getByRole("listitem")
      .filter({ hasText: "Ausgeführt am 2026-09-11" });
    await expect(dateEvent).toHaveCount(1);
    await expect(dateEvent).toContainText("Uhrzeit unbekannt · Europe/Berlin");
    await expect(dateEvent).toContainText("Präzision: Datum ohne Uhrzeit");
    const missingTime = dateEvent.getByText(
      "Kein Diagrammmarker: Nur Ausführungsdatum bekannt.",
      {
        exact: true,
      },
    );
    const dateSource = dateEvent.getByText(
      "Buchungsbeleg und Währungsherkunft",
      { exact: true },
    );
    await dateSource.focus();
    await page.keyboard.press("Space");
    await expect(dateSource).toBeFocused();
    await expect(dateEvent).toContainText("Buchung synthetic-calendar-sale");
    expect(
      await dateSource.evaluate((element) => {
        const style = getComputedStyle(element);
        return (
          element.matches(":focus-visible") &&
          style.outlineStyle !== "none" &&
          parseFloat(style.outlineWidth) >= 2
        );
      }),
    ).toBe(true);

    for (const notice of [truncation, exclusion, missingTime]) {
      await notice.scrollIntoViewIfNeeded();
      await expect(notice).toBeVisible();
      expect(
        await notice.evaluate((element) => {
          const bounds = element.getBoundingClientRect();
          return (
            bounds.left >= 0 &&
            bounds.right <= window.innerWidth + 1 &&
            element.scrollWidth <= element.clientWidth + 1
          );
        }),
      ).toBe(true);
    }
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);

    const noticeCaptureSession = await context.newCDPSession(page);
    for (const [name, target] of [
      ["limits", truncation],
      ["date-only", missingTime],
    ] as const) {
      await target.evaluate((element) =>
        element.scrollIntoView({ block: "center" }),
      );
      await page.evaluate(
        () =>
          new Promise<void>((resolve) => {
            requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
          }),
      );
      const noticeCapture = await noticeCaptureSession.send(
        "Page.captureScreenshot",
        {
          format: "png",
          fromSurface: false,
          captureBeyondViewport: false,
        },
      );
      const noticeScreenshot = testInfo.outputPath(
        "ux4-b-native-400-percent-" + name + "-synthetic.png",
      );
      await writeFile(
        noticeScreenshot,
        Buffer.from(noticeCapture.data, "base64"),
      );
      await testInfo.attach(
        "UX4-B synthetic " + name + " notice at native 400% browser zoom",
        {
          path: noticeScreenshot,
          contentType: "image/png",
        },
      );
    }
    await noticeCaptureSession.detach();
    const noticeMeasurements = testInfo.outputPath(
      "ux4-b-native-400-zoom-measurements.json",
    );
    await writeFile(
      noticeMeasurements,
      JSON.stringify(
        {
          before,
          nativeZoomFactor: noticeZoom,
          after: await page.evaluate(() => ({
            width: window.innerWidth,
            ratio: window.devicePixelRatio,
            documentWidth: document.documentElement.scrollWidth,
          })),
        },
        null,
        2,
      ),
    );
    await testInfo.attach("Native 400% browser zoom measurements", {
      path: noticeMeasurements,
      contentType: "application/json",
    });
    expect(apiRequests).toEqual(originalRequests);
    expect(requests.reads).toHaveLength(1);
    expect(requests.writes).toEqual([]);
    expect(requests.browserErrors).toEqual([]);
  } finally {
    await context.close();
  }
});

test("UX4-B preserves existing chart arrows while exact evidence remains a separate keyboard action", async ({
  page,
}) => {
  const evidence = history();
  evidence.series[0].points[0].price = "0.211111111111111111";
  evidence.series[0].points.push({
    ...evidence.series[0].points[0],
    id: "synthetic-next-second",
    observed_at: "2026-09-10T13:45:23Z",
    price: "0.311111111111111111",
  });
  const requests = await setup(page, async (route) => {
    await route.fulfill({ json: evidence });
  });
  await page.goto("/workspace");
  const panel = await openPosition(page);
  await expect(panel.locator(".recharts-scatter-symbol")).toHaveCount(2);
  const chart = panel.getByRole("application");
  await chart.focus();
  await page.keyboard.press("ArrowRight");
  const tooltip = panel.locator(".recharts-tooltip-wrapper");
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toContainText("0,311111111111111111 EUR");
  await expect(
    tooltip.locator('time[datetime="2026-09-10T13:45:23Z"]'),
  ).toBeVisible();
  await expect(chart).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(tooltip).toContainText("0,211111111111111111 EUR");
  await expect(
    tooltip.locator('time[datetime="' + observedAt + '"]'),
  ).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(tooltip).not.toBeVisible();
  await expect(chart).toBeFocused();
  await expect(
    panel.getByRole("heading", {
      name: "Angezeigte Punkte und Buchungen: 2",
      exact: true,
    }),
  ).not.toBeVisible();
  const summary = panel.getByText("Punkte und Buchungen auswählen (EUR)", {
    exact: true,
  });
  await summary.focus();
  await page.keyboard.press("Enter");
  await panel.getByRole("button", { name: /^Quelle 1, Kurspunkt 2:/ }).focus();
  await page.keyboard.press("Enter");
  const selected = panel.getByRole("region", {
    name: "Ausgewählter Originalkursbeleg",
    exact: true,
  });
  await expect(selected).toBeFocused();
  await expect(selected).toContainText("0,311111111111111111 EUR");
  expect(requests.reads).toHaveLength(1);
  expect(requests.writes).toEqual([]);
  expect(requests.browserErrors).toEqual([]);
});
