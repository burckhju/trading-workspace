import { expect, test, type Page, type Route } from "@playwright/test";
import { position } from "../../frontend/src/test/positionFixture";

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
