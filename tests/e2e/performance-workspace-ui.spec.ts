import { expect, test, type Page, type Route } from "@playwright/test";
import { closedTradeReport } from "../../frontend/src/test/closedTradesFixtures";
import {
  realizedGrossReport,
  reportItem,
} from "../../frontend/src/test/realizedGrossFixtures";

test.use({ serviceWorkers: "block" });

type ReportKind = "realized-gross" | "closed-trades";

const reportQuery = (kind: ReportKind, extra: Record<string, string> = {}) =>
  new URLSearchParams({
    report_context: kind,
    from_date: "2026-10-01",
    to_date: "2026-10-31",
    report_currency: "EUR",
    report_timezone: "Europe/Berlin",
    report_view: "candidates",
    report_page: "1",
    ...extra,
  });

async function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

// Presentation-only responses reuse the existing backend-shaped fixtures. These
// cases prove browser behavior, not PostgreSQL or financial calculation.
async function installReports(page: Page, baseURL: string | undefined) {
  if (!baseURL) throw new Error("An explicit frontend baseURL is required.");
  const frontendOrigin = new URL(baseURL).origin;
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const configuredApi =
    process.env.E2E_VITE_API_BASE_URL ??
    process.env.VITE_API_BASE_URL ??
    `http://localhost:${frontendPort || "8080"}/api`;
  const apiBase = new URL(configuredApi);
  const apiPrefix = `${apiBase.pathname.replace(/\/$/, "")}/api/v1`;
  const reads: Array<{ kind: ReportKind; filters: Record<string, string> }> =
    [];
  const unexpected: string[] = [];
  const errors: string[] = [];
  let largeSales = false;
  page.on("pageerror", (error) => errors.push(error.message));

  // Only static frontend resources pass through. Every API, mutation, provider
  // request and unknown fetch is intercepted before it can reach a real service.
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      request.method() === "GET" &&
      url.origin === frontendOrigin &&
      !url.pathname.includes("/api/") &&
      ([
        "document",
        "script",
        "stylesheet",
        "image",
        "font",
        "manifest",
      ].includes(request.resourceType()) ||
        url.pathname === "/favicon.ico")
    ) {
      return route.continue();
    }
    const kind = (["realized-gross", "closed-trades"] as const).find(
      (candidate) => url.pathname === `${apiPrefix}/performance/${candidate}`,
    );
    if (request.method() !== "GET" || url.origin !== apiBase.origin || !kind) {
      unexpected.push(`${request.method()} ${url}`);
      return json(
        route,
        { code: "UNEXPECTED_TEST_REQUEST", message: "Unexpected request" },
        500,
      );
    }
    const filters = {
      from_date: url.searchParams.get("from_date") ?? "",
      to_date: url.searchParams.get("to_date") ?? "",
      report_currency: url.searchParams.get("report_currency") ?? "",
      report_timezone: url.searchParams.get("report_timezone") ?? "",
    };
    reads.push({ kind, filters });
    if (kind === "closed-trades")
      return json(route, closedTradeReport({ filters }));
    const report = realizedGrossReport({ filters });
    report.basis.id = "b".repeat(64);
    if (largeSales) {
      report.items = Array.from({ length: 2001 }, (_, index) =>
        reportItem(`unresolved-${index + 1}`, {
          status: "NOT_COMPUTABLE",
          reasons: ["CURRENCY_UNKNOWN"],
          currency_code: null,
          realized_gross_pnl_delta: null,
          realized_gross_pnl_delta_display: null,
        }),
      );
      report.sources = [];
      report.counts = {
        ...report.counts,
        examined: 2001,
        in_period: 2001,
        candidates: 2001,
        usable: 0,
        unresolved: 2001,
      };
      report.summary = {
        status: "NOT_COMPUTABLE",
        total: null,
        total_display: null,
        subtotal: null,
        subtotal_display: null,
        rounding_difference: null,
        rounding_difference_display: null,
      };
    }
    return json(route, report);
  });
  return {
    reads,
    unexpected,
    errors,
    setLargeSales: (value: boolean) => {
      largeSales = value;
    },
  };
}

const reportButton = (page: Page, kind: ReportKind) =>
  page.getByRole("button", {
    name:
      kind === "realized-gross"
        ? "Verkäufe im Zeitraum"
        : "Trades mit Vollabschluss im Zeitraum",
    exact: true,
  });

test("performance workspace: one keyboard-operated selection, both reports and router history", async ({
  page,
  baseURL,
}, testInfo) => {
  const api = await installReports(page, baseURL);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/performance");
  await expect(page).toHaveURL(/\/performance\/realized-gross$/);
  await expect(page.getByRole("form")).toHaveCount(1);
  await expect(
    page.getByRole("form", { name: "Performance-Zeitraum auswählen" }),
  ).toBeVisible();
  const mainNavigation = page.getByRole("navigation", {
    name: "Hauptnavigation",
    exact: true,
  });
  await expect(
    mainNavigation.getByRole("link", { name: "Performance", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    mainNavigation.getByRole("link", { name: /Verkäufe|Vollabschluss/ }),
  ).toHaveCount(0);
  expect(api.reads).toHaveLength(0);
  await reportButton(page, "closed-trades").focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Von (einschließlich)")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(reportButton(page, "closed-trades")).toBeFocused();
  await page.getByLabel("Von (einschließlich)").fill("2026-10-01");
  await page.getByLabel("Bis (einschließlich)").fill("2026-10-31");
  await page.getByLabel("Berichtszeitzone (IANA)").fill("Asia/Tokyo");
  await expect(page.getByLabel("Berichtswährung", { exact: true })).toHaveValue(
    "EUR",
  );
  await expect(
    page.getByLabel("Berichtswährung", { exact: true }),
  ).not.toBeEditable();
  expect(api.reads).toHaveLength(0);
  const readButton = page.getByRole("button", {
    name: "Bericht lesen",
    exact: true,
  });
  await readButton.focus();
  await expect(readButton).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  expect(api.reads).toHaveLength(1);
  await expect(page.getByTestId("closed-trades-total")).toHaveCount(0);
  const salesUrl = page.url();
  await reportButton(page, "closed-trades").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  await expect(reportButton(page, "closed-trades")).toBeFocused();
  await expect(reportButton(page, "closed-trades")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(reportButton(page, "realized-gross")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Asia/Tokyo",
  );
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  await expect(page.getByRole("form")).toHaveCount(1);
  await expect(
    page.getByRole("region", {
      name: "Ergebnis und Datenabdeckung",
      exact: true,
    }),
  ).toHaveCount(1);
  await expect(
    page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    }),
  ).toHaveCount(1);
  expect(api.reads.map((read) => read.kind)).toEqual([
    "realized-gross",
    "closed-trades",
  ]);
  expect(api.reads[1].filters).toEqual(api.reads[0].filters);
  const closedUrl = page.url();
  await page.goBack();
  await expect(page).toHaveURL(salesUrl);
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  await expect(
    page.getByRole("region", {
      name: "Basisstatistiken des Abschlussberichts",
      exact: true,
    }),
  ).toHaveCount(0);
  expect(api.reads).toHaveLength(3);
  await page.getByLabel("Von (einschließlich)").fill("2026-09-15");
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  expect(api.reads).toHaveLength(3);
  await page.goForward();
  await expect(page).toHaveURL(closedUrl);
  await expect(page.getByLabel("Von (einschließlich)")).toHaveValue(
    "2026-10-01",
  );
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  expect(api.reads).toHaveLength(4);
  await page.reload();
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Asia/Tokyo",
  );
  expect(api.reads).toHaveLength(5);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("performance-shared-filter-mobile.png"),
    fullPage: true,
  });
  expect(api.unexpected).toEqual([]);
  expect(api.errors).toEqual([]);
  await testInfo.attach("performance-ui-read-observations", {
    body: JSON.stringify(api.reads, null, 2),
    contentType: "application/json",
  });
});

test("performance workspace: invalid explicit links require submit and invalid drafts retain focus and values", async ({
  page,
  baseURL,
}) => {
  const api = await installReports(page, baseURL);
  const duplicate = reportQuery("realized-gross");
  duplicate.append("from_date", "2026-09-01");
  await page.goto(`/performance/realized-gross?${duplicate}`);
  await expect(page.getByRole("alert")).toContainText(
    /Ungültiger|mehrdeutiger/,
  );
  const invalidUrl = page.url();
  await page.getByLabel("Von (einschließlich)").fill("2026-10-01");
  await page.getByLabel("Bis (einschließlich)").fill("2026-10-31");
  await page.getByLabel("Berichtszeitzone (IANA)").fill("Etc/UTC");
  await reportButton(page, "closed-trades").click();
  await expect(page).toHaveURL(invalidUrl);
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue(
    "Etc/UTC",
  );
  expect(api.reads).toHaveLength(0);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  expect(api.reads).toHaveLength(1);
  await page.getByLabel("Berichtszeitzone (IANA)").fill("");
  await reportButton(page, "closed-trades").click();
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveValue("");
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await expect(page.getByLabel("Berichtszeitzone (IANA)")).toBeFocused();
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  await expect(page.getByTestId("closed-trades-total")).toHaveCount(0);
  expect(api.reads).toHaveLength(1);
  await page.getByLabel("Berichtszeitzone (IANA)").fill("Europe/Berlin");
  await reportButton(page, "closed-trades").click();
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  expect(api.reads).toHaveLength(2);
  await page.goto(
    `/performance/realized-gross?${reportQuery("realized-gross", { report_currency: "USD" })}`,
  );
  await expect(page.getByRole("alert")).toContainText("USD");
  await reportButton(page, "closed-trades").click();
  expect(api.reads).toHaveLength(2);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  expect(api.reads).toHaveLength(3);
  expect(api.reads[2].filters.report_currency).toBe("EUR");

  // Intl accepts bare offsets in modern browsers, but the report API requires
  // an IANA identifier. Editing must fail before any report request is sent.
  const zone = page.getByLabel("Berichtszeitzone (IANA)");
  const appliedUrl = page.url();
  await zone.fill("+01:00");
  await reportButton(page, "closed-trades").click();
  await expect(zone).toHaveValue("+01:00");
  await expect(zone).toHaveAttribute("aria-invalid", "true");
  await expect(zone).toBeFocused();
  await expect(page.getByRole("alert")).toContainText(
    "Berichtszeitzone (IANA)",
  );
  await expect(page).toHaveURL(appliedUrl);
  await expect(page.getByTestId("realized-gross-total")).toHaveCount(0);
  await expect(page.getByTestId("closed-trades-total")).toHaveCount(0);
  expect(api.reads).toHaveLength(3);
  await zone.fill("Etc/GMT+1");
  await reportButton(page, "closed-trades").click();
  await expect(page.getByTestId("closed-trades-total")).toHaveText("50,00 EUR");
  expect(api.reads).toHaveLength(4);
  expect(api.reads[3].filters.report_timezone).toBe("Etc/GMT+1");

  // Both direct routes reject the same bare offset. Fixing a field still needs
  // an explicit read; a report switch cannot silently repair an invalid link.
  for (const kind of ["realized-gross", "closed-trades"] as const) {
    const beforeOffsetLink = api.reads.length;
    await page.goto(
      `/performance/${kind}?${reportQuery(kind, { report_timezone: "+01:00" })}`,
    );
    const offsetUrl = page.url();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(zone).toHaveValue("+01:00");
    expect(api.reads).toHaveLength(beforeOffsetLink);
    const target =
      kind === "realized-gross" ? "closed-trades" : "realized-gross";
    await reportButton(page, target).click();
    await expect(zone).toHaveAttribute("aria-invalid", "true");
    await expect(zone).toBeFocused();
    await expect(page).toHaveURL(offsetUrl);
    expect(api.reads).toHaveLength(beforeOffsetLink);
    await zone.fill("Etc/GMT+1");
    await reportButton(page, target).click();
    await expect(page).toHaveURL(offsetUrl);
    await expect(zone).toHaveValue("Etc/GMT+1");
    expect(api.reads).toHaveLength(beforeOffsetLink);
    await page
      .getByRole("button", { name: "Bericht lesen", exact: true })
      .click();
    await expect(
      page.getByTestId(
        kind === "realized-gross"
          ? "realized-gross-total"
          : "closed-trades-total",
      ),
    ).toBeVisible();
    expect(api.reads).toHaveLength(beforeOffsetLink + 1);
    expect(api.reads.at(-1)).toMatchObject({
      kind,
      filters: { report_timezone: "Etc/GMT+1" },
    });
  }
  expect(api.unexpected).toEqual([]);
  expect(api.errors).toEqual([]);
});

test("performance workspace: SELL page 101 stays local and a shorter fresh snapshot explains its bounded page", async ({
  page,
  baseURL,
}) => {
  const api = await installReports(page, baseURL);
  api.setLargeSales(true);
  await page.goto(
    `/performance/realized-gross?${reportQuery("realized-gross", { report_view: "all", report_page: "101" })}`,
  );
  const pagination = page.getByRole("navigation", {
    name: "Berichtsseiten",
    exact: true,
  });
  await expect(pagination).toContainText("Seite 101 von 101");
  await expect(page.getByRole("article", { name: /^Verkauf / })).toHaveCount(1);
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "Nicht berechenbar",
  );
  expect(api.reads).toHaveLength(1);
  await page
    .getByRole("button", { name: "Vorherige Seite", exact: true })
    .click();
  await expect(pagination).toContainText("Seite 100 von 101");
  await expect(page.getByRole("article", { name: /^Verkauf / })).toHaveCount(
    20,
  );
  await page
    .getByRole("button", { name: "Nächste Seite", exact: true })
    .click();
  await expect(pagination).toContainText("Seite 101 von 101");
  await page
    .getByRole("button", { name: "Quellen und Berechnung", exact: true })
    .click();
  await expect(
    page.getByRole("region", {
      name: "Herkunft SELL unresolved-2001",
      exact: true,
    }),
  ).toBeVisible();
  expect(api.reads).toHaveLength(1);
  api.setLargeSales(false);
  await page
    .getByRole("button", { name: "Bericht lesen", exact: true })
    .click();
  await expect(
    page.getByText(
      /Die ursprüngliche Seite 101 ist im neu gelesenen Stand nicht mehr/,
    ),
  ).toBeVisible();
  await expect(pagination).toContainText("Seite 1 von 1");
  await expect(page.getByTestId("realized-gross-total")).toHaveText(
    "10,00 EUR",
  );
  await expect(
    page.getByRole("region", {
      name: "Herkunft SELL unresolved-2001",
      exact: true,
    }),
  ).toHaveCount(0);
  expect(api.reads).toHaveLength(2);
  await page.getByLabel("Zeilen anzeigen").selectOption("usable");
  await expect(page.getByLabel("Zeilen anzeigen")).toHaveValue("usable");
  expect(api.reads).toHaveLength(2);
  expect(api.unexpected).toEqual([]);
  expect(api.errors).toEqual([]);
});
