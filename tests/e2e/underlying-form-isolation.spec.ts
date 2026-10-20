import {
  expect,
  test,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

const firstId = "11111111-1111-4111-8111-111111111111";
const secondId = "22222222-2222-4222-8222-222222222222";
const createdId = "33333333-3333-4333-8333-333333333333";
const venueId = "00000000-0000-4000-8001-000000000001";
const now = "2026-10-17T06:45:00Z";
const detail = (id: string) => ({
  id,
  name:
    id === firstId
      ? "Testwert A"
      : id === secondId
        ? "Testwert B"
        : "Neuer Testwert",
  type: "STOCK",
  isin: null,
  wkn: null,
  lifecycle_status: "ACTIVE",
  quality_status: "DRAFT",
  version: id === firstId ? 7 : id === secondId ? 3 : 1,
  created_at: now,
  updated_at: now,
  primary_listing: null,
  listings: [],
});

type Write = { method: string; path: string; body: unknown };
type ApiOptions = {
  holdReads?: string[];
  failLoad?: boolean;
  holdWrites?: boolean;
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

// A rendered frame follows the controlled response/submit event; no timed sleep.
async function renderedFrame(page: Page) {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

async function installApi(
  page: Page,
  baseURL: string | undefined,
  options: ApiOptions = {},
) {
  if (!baseURL)
    throw new Error("The test frontend baseURL must be configured.");
  const frontendOrigin = new URL(baseURL).origin;
  // CI declares VITE_API_BASE_URL; custom builds must pass their same explicit
  // build value here. The fallback mirrors run-e2e.sh's existing Compose default.
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const buildApiBaseUrl =
    process.env.E2E_VITE_API_BASE_URL ??
    process.env.VITE_API_BASE_URL ??
    `http://localhost:${frontendPort || "8080"}/api`;
  const apiBase = new URL(buildApiBaseUrl).toString().replace(/\/$/, "");
  const apiOrigin = new URL(apiBase).origin;
  const apiPrefix = `${new URL(apiBase).pathname.replace(/\/$/, "")}/api/v1`;
  const endpoint = (id?: string) =>
    `${apiPrefix}/underlyings${id ? `/${id}` : ""}`;
  const reads: string[] = [];
  const writes: Write[] = [];
  const observations: { method: string; url: string; prefix: string | null }[] =
    [];
  const unexpected: string[] = [];
  const heldReadIds = new Set(options.holdReads);
  const heldReads = new Map<string, Route[]>();
  const heldWrites = new Map<string, Route[]>();
  const ids = [firstId, secondId, createdId];

  async function unexpectedRequest(route: Route) {
    const request = route.request();
    const description = `${request.method()} ${request.url()}`;
    unexpected.push(description);
    return json(
      route,
      {
        code: "E2E_UNEXPECTED_REQUEST",
        message: description,
        details: [],
        timestamp: now,
      },
      500,
    );
  }

  // Only frontend documents/assets reach the disposable static server. Every
  // API, fetch/XHR, mutation and external request is fulfilled here, including
  // unexpected paths, so a broken assertion cannot cause a real backend write.
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    if (
      method === "GET" &&
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

    const observedPrefix =
      url.pathname.match(/^(.*\/api\/v1)(?:\/|$)/)?.[1] ?? null;
    observations.push({ method, url: url.toString(), prefix: observedPrefix });
    if (method !== "GET") {
      writes.push({ method, path: url.pathname, body: request.postDataJSON() });
    }
    if (url.origin !== apiOrigin || observedPrefix !== apiPrefix) {
      return unexpectedRequest(route);
    }

    if (method === "GET") {
      reads.push(url.pathname);
      if (
        !url.search &&
        url.pathname === `${apiPrefix}/market-reference-data/trading-venues`
      ) {
        return json(route, {
          items: [
            {
              id: venueId,
              mic: "XETR",
              name: "Xetra",
              country_code: "DE",
              timezone: "Europe/Berlin",
              reference_version: "TEST",
            },
          ],
        });
      }
      if (
        !url.search &&
        url.pathname === `${apiPrefix}/market-reference-data/currencies`
      ) {
        return json(route, {
          items: [
            {
              code: "EUR",
              name: "Euro",
              minor_unit: 2,
              reference_version: "TEST",
            },
          ],
        });
      }
      const id = ids.find((candidate) => url.pathname === endpoint(candidate));
      if (id && !url.search) {
        if (id === firstId && options.failLoad) {
          return json(
            route,
            {
              code: "TEST_LOAD_FAILED",
              message: "Test: Basiswert nicht erreichbar.",
              details: [],
              timestamp: now,
            },
            503,
          );
        }
        if (heldReadIds.has(id)) {
          heldReads.set(id, [...(heldReads.get(id) ?? []), route]);
          return;
        }
        return json(route, detail(id));
      }
      if (
        !url.search &&
        ids.some((id) => url.pathname === `${endpoint(id)}/usages`)
      ) {
        return json(route, { items: [] });
      }
      if (
        url.search === "?limit=50" &&
        ids.some((id) => url.pathname === `${endpoint(id)}/audit-events`)
      ) {
        return json(route, { items: [], total: 0, offset: 0, limit: 50 });
      }
      return unexpectedRequest(route);
    }

    const target =
      method === "POST" && url.pathname === endpoint()
        ? createdId
        : method === "PATCH"
          ? [firstId, secondId].find((id) => url.pathname === endpoint(id))
          : undefined;
    if (!target || url.search) return unexpectedRequest(route);
    if (options.holdWrites) {
      heldWrites.set(target, [...(heldWrites.get(target) ?? []), route]);
      return;
    }
    return json(route, {
      ...detail(target),
      version: detail(target).version + 1,
    });
  });

  async function release(route: Route, body: unknown, status = 200) {
    const response = page.waitForResponse(
      (candidate) => candidate.request() === route.request(),
    );
    await json(route, body, status);
    await (await response).finished();
  }

  return {
    reads,
    writes,
    endpoint,
    hasHeldRead: (id: string) => heldReads.has(id),
    releaseRead: async (id: string) => {
      const routes = heldReads.get(id);
      if (!routes?.length) throw new Error(`Expected a held read for ${id}.`);
      heldReadIds.delete(id);
      heldReads.delete(id);
      for (const route of routes) await release(route, detail(id));
      await renderedFrame(page);
    },
    releaseWrite: async (
      id: string,
      outcome: "resolve" | "reject" = "resolve",
    ) => {
      const routes = heldWrites.get(id);
      if (!routes?.length) throw new Error(`Expected a held write for ${id}.`);
      heldWrites.delete(id);
      for (const route of routes) {
        await release(
          route,
          outcome === "resolve"
            ? {
                ...detail(id),
                version: id === createdId ? 1 : detail(id).version + 1,
              }
            : {
                code: "TEST_SAVE_FAILED",
                message: "Test: Alter Speichervorgang fehlgeschlagen.",
                details: [],
                timestamp: now,
              },
          outcome === "resolve" ? 200 : 503,
        );
      }
      await renderedFrame(page);
    },
    assertContract: async (info: TestInfo) => {
      await renderedFrame(page);
      await info.attach("observed-api-contract", {
        body: Buffer.from(
          JSON.stringify(
            { buildApiBaseUrl, apiPrefix, observations, writes, unexpected },
            null,
            2,
          ),
        ),
        contentType: "application/json",
      });
      expect(unexpected).toEqual([]);
      expect([
        ...new Set(observations.map((request) => request.prefix)),
      ]).toEqual([apiPrefix]);
      expect([...heldReads.keys()]).toEqual([]);
      expect([...heldWrites.keys()]).toEqual([]);
    },
  };
}

// Exercise an in-place React Router history transition, without a document reload.
async function changeFormRoute(page: Page, path: string) {
  await page.evaluate((destination) => {
    window.history.pushState(null, "", destination);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
}

async function screenshot(page: Page, info: TestInfo, name: string) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await info.attach(name, {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
}

async function expectSaving(page: Page, creation = false) {
  for (const label of [
    "Name *",
    "Basiswertart",
    "ISIN",
    "WKN",
    ...(creation ? ["Ticker *", "Währung *"] : []),
  ]) {
    const field =
      label === "Basiswertart" || label === "Währung *"
        ? page.getByRole("combobox", { name: label, exact: true })
        : page.getByLabel(label, { exact: true });
    await expect(field).toBeDisabled();
  }
  await expect(
    page.getByRole("button", { name: "Speichern …", exact: true }),
  ).toBeDisabled();
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const order of ["B-first", "A-first"] as const) {
      test(
        order === "B-first"
          ? "ignores a late load and submits only the current record and version"
          : "keeps B loading when A responds first and saves only B and its version",
        async ({ page, baseURL }, info) => {
          const api = await installApi(page, baseURL, {
            holdReads: [firstId, secondId],
          });
          await page.goto(`/underlyings/${firstId}/edit`);
          await expect(page.getByRole("status")).toHaveText(
            "Formular wird vorbereitet …",
          );
          await expect.poll(() => api.hasHeldRead(firstId)).toBe(true);
          await changeFormRoute(page, `/underlyings/${secondId}/edit`);
          await expect.poll(() => api.hasHeldRead(secondId)).toBe(true);
          expect(api.reads).toContain(api.endpoint(firstId));
          expect(api.reads).toContain(api.endpoint(secondId));
          if (order === "A-first") {
            await api.releaseRead(firstId);
            await expect(page).toHaveURL(
              new RegExp(`/underlyings/${secondId}/edit$`),
            );
            await expect(page.getByRole("status")).toHaveText(
              "Formular wird vorbereitet …",
            );
            await expect(page.getByLabel("Name *")).toHaveCount(0);
            await expect(page.getByRole("alert")).toHaveCount(0);
            expect(api.writes).toEqual([]);
            await screenshot(page, info, `${viewport.name}-loading-B-after-A`);
          }
          await api.releaseRead(secondId);
          await expect(page.getByLabel("Name *")).toHaveValue("Testwert B");
          if (order === "B-first") await api.releaseRead(firstId);
          await expect(page).toHaveURL(
            new RegExp(`/underlyings/${secondId}/edit$`),
          );
          await expect(page.getByLabel("Name *")).toHaveValue("Testwert B");
          await expect(page.getByRole("alert")).toHaveCount(0);
          await expect(
            page.getByRole("button", { name: "Speichern", exact: true }),
          ).toBeEnabled();
          await screenshot(page, info, `${viewport.name}-current-form`);
          await page.getByLabel("Name *").fill("Testwert B bearbeitet");
          await page
            .getByRole("button", { name: "Speichern", exact: true })
            .click();
          const expectedWrites = [
            {
              method: "PATCH",
              path: api.endpoint(secondId),
              body: {
                version: 3,
                name: "Testwert B bearbeitet",
                isin: null,
                wkn: null,
              },
            },
          ];
          await expect.poll(() => api.writes).toEqual(expectedWrites);
          await expect(page).toHaveURL(new RegExp(`/underlyings/${secondId}$`));
          await api.assertContract(info);
          expect(api.writes).toEqual(expectedWrites);
        },
      );
    }

    test("explains a failed edit load and cannot fall through to creation", async ({
      page,
      baseURL,
    }, info) => {
      const api = await installApi(page, baseURL, { failLoad: true });
      await page.goto(`/underlyings/${firstId}/edit`);
      await expect(page.getByRole("alert")).toHaveText(
        "Test: Basiswert nicht erreichbar.",
      );
      await expect(
        page.getByText(/Speichern ist gesperrt, weil das Formular/),
      ).toBeVisible();
      await expect(page.getByLabel("Name *")).toBeDisabled();
      await expect(
        page.getByRole("button", { name: "Speichern", exact: true }),
      ).toBeDisabled();
      await page.locator("form").evaluate((form) => {
        form.dispatchEvent(
          new Event("submit", { bubbles: true, cancelable: true }),
        );
      });
      await renderedFrame(page);
      await expect(page).toHaveURL(new RegExp(`/underlyings/${firstId}/edit$`));
      expect(api.writes).toEqual([]);
      await screenshot(page, info, `${viewport.name}-load-error`);
      await api.assertContract(info);
      expect(api.writes).toEqual([]);
    });

    for (const outcome of ["resolve", "reject"] as const) {
      test(`ignores a late A save ${outcome} while B is saving`, async ({
        page,
        baseURL,
      }, info) => {
        const api = await installApi(page, baseURL, { holdWrites: true });
        await page.goto(`/underlyings/${firstId}/edit`);
        await expect(page.getByLabel("Name *")).toHaveValue("Testwert A");
        await page.getByLabel("Name *").fill("Testwert A bearbeitet");
        await page
          .getByRole("button", { name: "Speichern", exact: true })
          .click();
        await expect.poll(() => api.writes).toHaveLength(1);
        await expectSaving(page);
        await changeFormRoute(page, `/underlyings/${secondId}/edit`);
        await expect(page.getByLabel("Name *")).toHaveValue("Testwert B");
        await page.getByLabel("Name *").fill("Testwert B bearbeitet");
        await page
          .getByRole("button", { name: "Speichern", exact: true })
          .click();
        const expectedWrites = [
          {
            method: "PATCH",
            path: api.endpoint(firstId),
            body: {
              version: 7,
              name: "Testwert A bearbeitet",
              isin: null,
              wkn: null,
            },
          },
          {
            method: "PATCH",
            path: api.endpoint(secondId),
            body: {
              version: 3,
              name: "Testwert B bearbeitet",
              isin: null,
              wkn: null,
            },
          },
        ];
        await expect.poll(() => api.writes).toEqual(expectedWrites);
        await expectSaving(page);
        await api.releaseWrite(firstId, outcome);
        await expect(page).toHaveURL(
          new RegExp(`/underlyings/${secondId}/edit$`),
        );
        await expect(page.getByLabel("Name *")).toHaveValue(
          "Testwert B bearbeitet",
        );
        await expect(page.getByRole("alert")).toHaveCount(0);
        await expectSaving(page);
        expect(api.writes).toEqual(expectedWrites);
        await screenshot(
          page,
          info,
          `${viewport.name}-saving-B-after-A-${outcome}`,
        );
        await api.releaseWrite(secondId);
        await expect(page).toHaveURL(new RegExp(`/underlyings/${secondId}$`));
        await api.assertContract(info);
        expect(api.writes).toEqual(expectedWrites);
      });
    }

    test("creates once after synchronous duplicate submits and navigates to the created record", async ({
      page,
      baseURL,
    }, info) => {
      const api = await installApi(page, baseURL, { holdWrites: true });
      await page.goto("/underlyings/new");
      await page.getByLabel("Name *").fill("Neuer Testwert");
      await page.getByLabel("ISIN", { exact: true }).fill("de0007236101");
      await page.getByLabel("WKN", { exact: true }).fill("723610");
      await page.getByLabel("Ticker *").fill("test");
      await page.locator("form").evaluate((form) => {
        // Both submit handlers run in the same browser task, before another render.
        form.dispatchEvent(
          new Event("submit", { bubbles: true, cancelable: true }),
        );
        form.dispatchEvent(
          new Event("submit", { bubbles: true, cancelable: true }),
        );
      });
      const expectedWrites = [
        {
          method: "POST",
          path: api.endpoint(),
          body: {
            name: "Neuer Testwert",
            type: "STOCK",
            isin: "DE0007236101",
            wkn: "723610",
            primary_listing: {
              trading_venue_id: venueId,
              ticker: "TEST",
              currency_code: "EUR",
              is_primary: true,
            },
          },
        },
      ];
      await expect.poll(() => api.writes).toEqual(expectedWrites);
      await expect(page).toHaveURL(/\/underlyings\/new$/);
      await expectSaving(page, true);
      await expect(page.getByRole("alert")).toHaveCount(0);
      await screenshot(page, info, `${viewport.name}-create-saving`);
      expect(api.writes).toEqual(expectedWrites);
      await api.releaseWrite(createdId);
      await expect(page).toHaveURL(new RegExp(`/underlyings/${createdId}$`));
      await expect(
        page.getByRole("heading", { name: "Neuer Testwert", exact: true }),
      ).toBeVisible();
      await api.assertContract(info);
      expect(api.writes).toEqual(expectedWrites);
    });
  });
}
