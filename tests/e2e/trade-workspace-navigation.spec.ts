import { expect, test, type Page, type Route } from "@playwright/test";

import type {
  TradeResponse,
  TradeTimelineEntryResponse,
} from "../../frontend/src/features/trade/types/api";

// Read-only browser fixtures: every API request is intercepted. No real trade,
// provider, approval, execution or journal is created by these navigation tests.
test.use({ timezoneId: "Europe/Berlin" });

const tradeId = "51000000-0000-4000-8000-000000000001";
const productId = "52000000-0000-4000-8000-000000000001";
const positionId = "53000000-0000-4000-8000-000000000001";
const buyId = "54000000-0000-4000-8000-000000000001";
const journalVersionId = "55000000-0000-4000-8000-000000000001";
const now = "2026-10-31T09:00:00Z";
const productName = "Synthetic UX2 navigation warrant";

type Status = "OPEN" | "CLOSED" | "CANCELLED";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, json: body });
}

async function fixture(
  page: Page,
  options: { status?: Status; missingPosition?: boolean } = {},
) {
  const status = options.status ?? "OPEN";
  const trade: TradeResponse = {
    id: tradeId,
    product_id: productId,
    origin: "EXTERNAL",
    trade_plan_id: null,
    trade_plan_version_id: null,
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
    currency_resolution: {
      currency_code: null,
      source: "UNKNOWN",
      source_execution_ids: [],
      confirmation_ids: [],
    },
  };
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
        open_quantity: status === "OPEN" ? 10 : 0,
        cost_basis: status === "OPEN" ? "20.00" : "0.00",
        average_entry_price: "2.00",
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
    if (path.endsWith("/timeline")) return json(route, [buy]);
    if (path.endsWith("/currency-confirmations"))
      return json(route, {
        current: null,
        history: [],
        currency_resolution: buy.currency_resolution,
      });
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
      return json(route, {
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
      });
    if (path.endsWith(`/alerts/trades/${tradeId}`)) return json(route, []);
    if (path.endsWith("/sources"))
      return json(
        route,
        snapshot({
          trade,
          product_name: productName,
          state: status,
          open_quantity: status === "OPEN" ? 10 : 0,
          timeline: [buy],
          currency_history: [],
        }),
      );
    if (path.endsWith("/sources/plan")) return json(route, snapshot(null));
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

async function loaded(page: Page) {
  await expect(
    page.getByRole("heading", { name: new RegExp(productName) }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Laden", exact: true }),
  ).toBeEnabled();
  await expect(
    page
      .getByRole("region", { name: "Kauf- und Verkaufsdaten" })
      .getByRole("article"),
  ).toHaveCount(1);
  await page.waitForLoadState("networkidle");
}

for (const width of [390, 1280]) {
  test(`one trade keeps both drafts and read owners through keyboard section changes at ${width}px`, async ({
    page,
  }, testInfo) => {
    const observed = await fixture(page);
    await page.setViewportSize({ width, height: 844 });
    // Preserve the exact spelling and ordering of supported context parameters.
    // URLSearchParams normalisation would change both and trigger a dirty guard.
    const query = `?journal_version_id=${journalVersionId}&trade_id=%35${tradeId.slice(1)}`;
    await page.goto(`/trade-management${query}#trade-overview`);
    await loaded(page);
    await expect(page.locator("#trade-overview")).toBeFocused();

    await page.getByLabel("Verkaufsmenge", { exact: true }).fill("3");
    await page.getByLabel("Verkaufspreis", { exact: true }).fill("2.50");
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
    const originalReads = [...observed.reads];

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
