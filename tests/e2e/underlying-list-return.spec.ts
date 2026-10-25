import { expect, test, type Page, type TestInfo } from "@playwright/test";

// UI navigation contract only: every API call is intercepted with synthetic data.
// These PATCHes do not reach the backend or mutate user/reference data.
const venueId = "00000000-0000-4000-8001-000000000001";
const itemName = (index: number) =>
  `Testbasiswert ${String(index).padStart(2, "0")}`;
async function installApi(
  page: Page,
  baseURL: string | undefined,
  count = 60,
  holdUpdates = false,
) {
  if (!baseURL)
    throw new Error("The test frontend baseURL must be configured.");
  const frontendOrigin = new URL(baseURL).origin;
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const buildApiBaseUrl =
    process.env.E2E_VITE_API_BASE_URL ??
    process.env.VITE_API_BASE_URL ??
    `http://localhost:${frontendPort || "8080"}/api`;
  const apiBase = new URL(buildApiBaseUrl);
  const apiPrefix = `${apiBase.pathname.replace(/\/$/, "")}/api/v1`;
  const endpoint = (id?: string) =>
    `${apiPrefix}/underlyings${id ? `/${id}` : ""}`;
  const writes: { method: string; path: string; body: unknown }[] = [];
  const reads: string[] = [];
  const pendingUpdates: (() => Promise<void>)[] = [];
  const listReads: Record<string, string>[] = [];
  const unexpected: string[] = [];
  const items = Array.from({ length: count }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    type: "STOCK",
    name: itemName(index + 1),
    isin: null,
    wkn: null,
    lifecycle_status: "ACTIVE",
    quality_status: "COMPLETE",
    version: 1,
    created_at: "2026-09-01T12:00:00Z",
    updated_at: "2026-09-01T12:00:00Z",
    primary_listing: null,
    listings: [],
  }));
  // Only static frontend documents/assets leave this fixture. All APIs, writes,
  // fetch/XHR and external requests are fulfilled synthetically, even on errors.
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    if (
      method === "GET" &&
      url.origin === frontendOrigin &&
      !path.includes("/api/") &&
      ([
        "document",
        "script",
        "stylesheet",
        "image",
        "font",
        "manifest",
      ].includes(request.resourceType()) ||
        path === "/favicon.ico")
    ) {
      return route.continue();
    }
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    const reject = () => {
      unexpected.push(`${method} ${url}`);
      return json({ message: `Unmapped test API: ${method} ${url}` }, 500);
    };
    if (url.origin !== apiBase.origin) return reject();
    if (method === "GET") reads.push(path);
    if (
      method === "GET" &&
      path === `${apiPrefix}/market-reference-data/trading-venues`
    )
      return json({
        items: [
          {
            id: venueId,
            mic: "XETR",
            name: "Xetra",
            country_code: "DE",
            timezone: "Europe/Berlin",
            reference_version: "test",
          },
        ],
      });
    if (
      method === "GET" &&
      path === `${apiPrefix}/market-reference-data/currencies`
    )
      return json({
        items: [
          {
            code: "EUR",
            name: "Euro",
            minor_unit: 2,
            reference_version: "test",
          },
        ],
      });
    if (
      method === "GET" &&
      items.some((item) => path === `${endpoint(item.id)}/audit-events`)
    )
      return json({ items: [], total: 0, limit: 50, offset: 0 });
    if (
      method === "GET" &&
      items.some((item) => path === `${endpoint(item.id)}/usages`)
    )
      return json({ items: [] });
    if (path === endpoint() && method === "GET") {
      listReads.push(Object.fromEntries(url.searchParams));
      const offset = Number(url.searchParams.get("offset") ?? 0);
      return json({
        items: items.slice(offset, offset + 25),
        total: items.length,
        offset,
        limit: 25,
      });
    }
    const item = items.find((item) => path === endpoint(item.id));
    if (item && method === "GET") return json(item);
    if (item && method === "PATCH") {
      const body = request.postDataJSON();
      writes.push({ method, path, body });
      const reply = async () => {
        item.name = body.name;
        item.version += 1;
        await json(item);
      };
      if (holdUpdates) {
        pendingUpdates.push(reply);
        return;
      }
      return reply();
    }
    if (item && method === "DELETE") {
      writes.push({ method, path, body: Object.fromEntries(url.searchParams) });
      items.splice(items.indexOf(item), 1);
      return route.fulfill({ status: 204 });
    }
    return reject();
  });
  return {
    writes,
    reads,
    items,
    endpoint,
    listReads,
    releaseUpdate: async () => {
      const reply = pendingUpdates.shift();
      expect(reply).toBeDefined();
      await reply!();
    },
    assertContract: async (info: TestInfo) => {
      await info.attach("navigation-api-contract", {
        body: Buffer.from(
          JSON.stringify({
            buildApiBaseUrl,
            apiPrefix,
            reads,
            listReads,
            writes,
            unexpected,
          }),
        ),
        contentType: "application/json",
      });
      expect(unexpected).toEqual([]);
    },
  };
}

for (const pageNumber of [2, 3]) {
  test(`returns to underlying page ${pageNumber} after saving, including reload and filters`, async ({
    page,
    baseURL,
  }, info) => {
    const api = await installApi(page, baseURL);
    const { writes, items } = api;
    await page.goto("/underlyings");
    await expect(
      page.getByRole("link", { name: itemName(1), exact: true }),
    ).toBeVisible();
    await page
      .getByRole("textbox", { name: "Suche", exact: true })
      .fill("Test");
    await page.getByRole("button", { name: "Suchen", exact: true }).click();
    await page
      .getByRole("combobox", { name: "Status", exact: true })
      .selectOption("ACTIVE");
    await page
      .getByRole("combobox", { name: "Markt", exact: true })
      .selectOption(venueId);
    await page
      .getByRole("combobox", { name: "Währung", exact: true })
      .selectOption("EUR");
    for (let current = 1; current < pageNumber; current++) {
      await page.getByRole("button", { name: "Weiter", exact: true }).click();
      await expect(
        page.getByRole("link", {
          name: itemName(current * 25 + 1),
          exact: true,
        }),
      ).toBeVisible();
    }
    await expect(page).toHaveURL(
      `/underlyings?query=Test&lifecycle=ACTIVE&venue=${venueId}&currency=EUR&offset=${(pageNumber - 1) * 25}`,
    );
    const listUrl = page.url();
    await page.reload();
    const firstIndex = (pageNumber - 1) * 25;
    await page
      .getByRole("link", { name: itemName(firstIndex + 1), exact: true })
      .click();
    await page.getByRole("link", { name: "Bearbeiten", exact: true }).click();
    await page.reload();
    await page
      .getByRole("textbox", { name: "Name *", exact: true })
      .fill("Testbasiswert gepflegt");
    expect(writes).toHaveLength(0);
    await page.getByRole("button", { name: "Speichern", exact: true }).click();
    await expect(page).toHaveURL(listUrl);
    await expect(
      page.getByRole("link", { name: "Testbasiswert gepflegt", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("status")).toHaveText(
      `60 Treffer · Seite ${pageNumber} von 3`,
    );
    await expect(
      page.getByRole("textbox", { name: "Suche", exact: true }),
    ).toHaveValue("Test");
    await expect(
      page.getByRole("combobox", { name: "Status", exact: true }),
    ).toHaveValue("ACTIVE");
    await expect(
      page.getByRole("combobox", { name: "Markt", exact: true }),
    ).toHaveValue(venueId);
    await expect(
      page.getByRole("combobox", { name: "Währung", exact: true }),
    ).toHaveValue("EUR");
    expect(writes).toEqual([
      {
        method: "PATCH",
        path: api.endpoint(items[firstIndex].id),
        body: {
          version: 1,
          name: "Testbasiswert gepflegt",
          isin: null,
          wkn: null,
        },
      },
    ]);
    expect(api.listReads.at(-1)).toEqual({
      q: "Test",
      lifecycle_status: "ACTIVE",
      trading_venue_id: venueId,
      currency_code: "EUR",
      limit: "25",
      offset: String(firstIndex),
    });
    await info.attach(`return-page-${pageNumber}`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await api.assertContract(info);
  });
}

test("keeps return pages independent in two tabs and cancels without mutation", async ({
  page,
  context,
  baseURL,
}, info) => {
  const other = await context.newPage();
  const first = await installApi(page, baseURL);
  const second = await installApi(other, baseURL);
  const firstList = `/underlyings?query=Test&lifecycle=ACTIVE&venue=${venueId}&currency=EUR&offset=25`;
  const secondList = `/underlyings?query=Testbasiswert&lifecycle=ACTIVE&venue=${venueId}&currency=EUR&offset=50`;
  await page.goto(firstList);
  await other.goto(secondList);
  await page.getByRole("link", { name: itemName(26), exact: true }).click();
  await other.getByRole("link", { name: itemName(51), exact: true }).click();
  await page.getByRole("link", { name: "Bearbeiten", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Name *", exact: true })
    .fill("Nicht speichern");
  await page.getByRole("link", { name: "Abbrechen", exact: true }).click();
  await expect(
    page.getByRole("link", { name: itemName(26), exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(firstList);
  await other.getByRole("link", { name: "← Basiswerte", exact: true }).click();
  await expect(
    other.getByRole("link", { name: itemName(51), exact: true }),
  ).toBeVisible();
  await expect(other).toHaveURL(secondList);
  await page.reload();
  await other.reload();
  await expect(
    page.getByRole("textbox", { name: "Suche", exact: true }),
  ).toHaveValue("Test");
  await expect(
    other.getByRole("textbox", { name: "Suche", exact: true }),
  ).toHaveValue("Testbasiswert");
  await expect(page).toHaveURL(firstList);
  await expect(other).toHaveURL(secondList);
  expect(first.writes).toHaveLength(0);
  expect(second.writes).toHaveLength(0);
  await first.assertContract(info);
  await second.assertContract(info);
  await other.close();
});

test("returns from an emptied final page to the last filtered page without a loop", async ({
  page,
  baseURL,
}, info) => {
  const api = await installApi(page, baseURL, 51);
  const lastId = api.items[50].id;
  const filters = `query=Test&lifecycle=ACTIVE&venue=${venueId}&currency=EUR`;
  await page.goto(`/underlyings?${filters}&offset=50`);
  await page.getByRole("link", { name: itemName(51), exact: true }).click();
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Löschen", exact: true }).click();
  await expect(page).toHaveURL(`/underlyings?${filters}&offset=25`);
  await expect(
    page.getByRole("link", { name: itemName(26), exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toHaveText(
    "50 Treffer · Seite 2 von 2",
  );
  await expect(
    page.getByRole("button", { name: "Weiter", exact: true }),
  ).toBeDisabled();
  expect(api.listReads.map((read) => read.offset)).toEqual(["50", "50", "25"]);
  expect(api.writes).toEqual([
    { method: "DELETE", path: api.endpoint(lastId), body: { version: "1" } },
  ]);
  await api.assertContract(info);
});

test("browser back and forward retain the confirmed search and page", async ({
  page,
  baseURL,
}, info) => {
  const api = await installApi(page, baseURL);
  await page.goto("/underlyings?query=Test&offset=25");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("link", { name: itemName(51), exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Bearbeiten", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL("/underlyings?query=Test&offset=50");
  await expect(
    page.getByRole("link", { name: itemName(51), exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL("/underlyings?query=Test&offset=25");
  await expect(
    page.getByRole("link", { name: itemName(26), exact: true }),
  ).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL("/underlyings?query=Test&offset=50");
  await expect(
    page.getByRole("link", { name: itemName(51), exact: true }),
  ).toBeVisible();
  expect(api.writes).toEqual([]);
  await api.assertContract(info);
});

test("keeps invalid return targets on the direct edit path", async ({
  page,
  baseURL,
}, info) => {
  const api = await installApi(page, baseURL);
  for (const returnTo of [
    "https://evil.invalid",
    "//evil.invalid",
    "/trades",
    "/underlyings?returnTo=%2Funderlyings%3Foffset%3D50",
    "%2Funderlyings%3Foffset%3D25",
  ]) {
    await page.goto(
      `/underlyings/${api.items[0].id}/edit?${new URLSearchParams({ returnTo })}`,
    );
    await page.getByRole("button", { name: "Speichern", exact: true }).click();
    await expect(page).toHaveURL(`/underlyings/${api.items[0].id}`);
    await expect(
      page.getByRole("heading", { name: itemName(1), exact: true }),
    ).toBeVisible();
  }
  expect(api.writes).toEqual(
    Array.from({ length: 5 }, (_, index) => ({
      method: "PATCH",
      path: api.endpoint(api.items[0].id),
      body: { version: index + 1, name: itemName(1), isin: null, wkn: null },
    })),
  );
  await api.assertContract(info);
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name}: changing only returnTo preserves a pending edit and its payload`, async ({
    page,
    baseURL,
  }, info) => {
    await page.setViewportSize(viewport);
    const api = await installApi(page, baseURL, 60, true);
    const id = api.items[25].id;
    const firstList = `/underlyings?query=Test&lifecycle=ACTIVE&venue=${venueId}&currency=EUR&offset=25`;
    const nextList = `/underlyings?query=Test&lifecycle=ACTIVE&venue=${venueId}&currency=EUR&offset=50`;
    const editPath = (returnTo: string) =>
      `/underlyings/${id}/edit?${new URLSearchParams({ returnTo })}`;
    await page.goto(editPath(firstList));
    await page
      .getByRole("textbox", { name: "Name *", exact: true })
      .fill("Testbasiswert gepflegt");
    const expectedWrites = [
      {
        method: "PATCH",
        path: api.endpoint(id),
        body: {
          version: 1,
          name: "Testbasiswert gepflegt",
          isin: null,
          wkn: null,
        },
      },
    ];
    await page.getByRole("button", { name: "Speichern", exact: true }).click();
    await expect.poll(() => api.writes).toEqual(expectedWrites);
    const readsBefore = [...api.reads];
    await page.evaluate((destination) => {
      window.history.pushState(null, "", destination);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }, editPath(nextList));
    await expect(
      page.getByRole("link", { name: "← Zurück", exact: true }),
    ).toHaveAttribute("href", nextList);
    await expect(page).toHaveURL(editPath(nextList));
    await expect(
      page.getByRole("textbox", { name: "Name *", exact: true }),
    ).toHaveValue("Testbasiswert gepflegt");
    await expect(
      page.getByRole("button", { name: "Speichern …", exact: true }),
    ).toBeDisabled();
    await page.locator("form").evaluate((form) => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    expect(api.reads).toEqual(readsBefore);
    expect(api.writes).toEqual(expectedWrites);
    await info.attach(`${viewport.name}-pending-return-context`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await api.releaseUpdate();
    await expect(page).toHaveURL(nextList);
    await expect(
      page.getByRole("link", { name: itemName(51), exact: true }),
    ).toBeVisible();
    expect(api.writes).toEqual(expectedWrites);
    expect(api.listReads).toEqual([
      {
        q: "Test",
        lifecycle_status: "ACTIVE",
        trading_venue_id: venueId,
        currency_code: "EUR",
        offset: "50",
        limit: "25",
      },
    ]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await info.attach(`${viewport.name}-return-context-list`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await api.assertContract(info);
  });
}
