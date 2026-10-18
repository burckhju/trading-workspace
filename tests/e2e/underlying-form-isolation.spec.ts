import { expect, test, type Page, type Route } from "@playwright/test";

const firstId = "11111111-1111-4111-8111-111111111111";
const secondId = "22222222-2222-4222-8222-222222222222";
const now = "2026-10-10T10:00:00Z";
const detail = (id: string) => ({
  id,
  name: id === firstId ? "Testwert A" : "Testwert B",
  type: "STOCK",
  isin: null,
  wkn: null,
  lifecycle_status: "ACTIVE",
  quality_status: "DRAFT",
  version: id === firstId ? 7 : 3,
  created_at: now,
  updated_at: now,
  primary_listing: null,
  listings: [],
});

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page, failLoad: boolean) {
  let held: Route | undefined;
  let currentReadPath: string | undefined;
  const writes: { method: string; path: string; body: unknown }[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET") {
      writes.push({
        method: request.method(),
        path,
        body: request.postDataJSON(),
      });
      return json(route, detail(secondId));
    }
    if (path.endsWith("/market-reference-data/trading-venues")) {
      return json(route, {
        items: [
          {
            id: "00000000-0000-4000-8001-000000000001",
            mic: "XETR",
            name: "Xetra",
            country_code: "DE",
            timezone: "Europe/Berlin",
            reference_version: "TEST",
          },
        ],
      });
    }
    if (path.endsWith("/market-reference-data/currencies")) {
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
    if (path.endsWith(`/underlyings/${firstId}`)) {
      if (failLoad) {
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
      // Release explicitly after the router has committed the next form.
      held = route;
      return;
    }
    if (path.endsWith(`/underlyings/${secondId}`)) {
      currentReadPath = path;
      return json(route, detail(secondId));
    }
    if (path.endsWith("/usages")) return json(route, { items: [] });
    if (path.endsWith("/audit-events"))
      return json(route, { items: [], total: 0, offset: 0, limit: 50 });
    return json(
      route,
      {
        code: "E2E_UNEXPECTED_READ",
        message: path,
        details: [],
        timestamp: now,
      },
      500,
    );
  });
  return {
    writes,
    hasHeldRequest: () => Boolean(held),
    // Reuse the actual B read endpoint; deployment proxy prefixes may differ.
    currentPath: () => currentReadPath,
    release: async () => {
      if (!held)
        throw new Error("Expected a held request for the first underlying.");
      await json(held, detail(firstId));
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

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("ignores a late load and submits only the current record and version", async ({
      page,
    }, info) => {
      const api = await installApi(page, false);
      await page.goto(`/underlyings/${firstId}/edit`);
      await expect(page.getByRole("status")).toHaveText(
        "Formular wird vorbereitet …",
      );
      await expect.poll(api.hasHeldRequest).toBe(true);
      await changeFormRoute(page, `/underlyings/${secondId}/edit`);
      await expect(page.getByLabel("Name *")).toHaveValue("Testwert B");
      const lateResponse = page.waitForResponse((response) =>
        new URL(response.url()).pathname.endsWith(`/underlyings/${firstId}`),
      );
      await api.release();
      await (await lateResponse).finished();
      // A following rendered frame gives the fetch/Promise handlers a chance to commit.
      await page.evaluate(
        () =>
          new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
          ),
      );
      await expect(page.getByLabel("Name *")).toHaveValue("Testwert B");
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: "Speichern", exact: true }),
      ).toBeEnabled();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      await info.attach(`${viewport.name}-current-form`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      });
      await page.getByLabel("Name *").fill("Testwert B bearbeitet");
      await page
        .getByRole("button", { name: "Speichern", exact: true })
        .click();
      await expect
        .poll(() => api.writes)
        .toEqual([
          {
            method: "PATCH",
            path: api.currentPath(),
            body: {
              version: 3,
              name: "Testwert B bearbeitet",
              isin: null,
              wkn: null,
            },
          },
        ]);
    });

    test("explains a failed edit load and cannot fall through to creation", async ({
      page,
    }, info) => {
      const api = await installApi(page, true);
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
      expect(api.writes).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      await info.attach(`${viewport.name}-load-error`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      });
    });
  });
}
