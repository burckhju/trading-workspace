import { expect, test } from "@playwright/test";
import type {
  AddWarrantTermsRequest,
  WarrantResponse,
  WarrantTermsResponse,
} from "../../frontend/src/features/product/types/api";

// Real Chromium interactions with synthetic API fixtures. The native listing and
// repair journey is covered separately by warrant-listing-without-symbol.spec.ts.
const now = "2026-10-25T10:00:00Z";
const changedAt = "2026-10-25T11:00:00Z";
const issuerId = "10000000-0000-4000-8000-000000000001";
const underlyingId = "10000000-0000-4000-8000-000000000002";
const alpha: WarrantResponse = {
  id: "10000000-0000-4000-8000-00000000000a",
  workspace_id: "10000000-0000-4000-8000-000000000003",
  issuer_id: issuerId,
  underlying_id: underlyingId,
  product_family: "WARRANT",
  display_name: "Synthetischer Call Alpha",
  isin: "DE000SYN0001",
  wkn: "SYN001",
  lifecycle_status: "ACTIVE",
  version: 3,
  created_at: now,
  updated_at: now,
};
const beta: WarrantResponse = {
  ...alpha,
  id: "10000000-0000-4000-8000-00000000000b",
  display_name: "Synthetischer Put Beta",
  isin: "DE000SYN0002",
  wkn: "SYN002",
  version: 7,
};
const originalTerms: WarrantTermsResponse = {
  id: "20000000-0000-4000-8000-00000000000b",
  warrant_id: beta.id,
  version_no: 4,
  effective_from: now,
  effective_to: null,
  option_direction: "PUT",
  strike: "123.45",
  strike_currency_code: "USD",
  maturity_date: "2027-06-18",
  ratio: "0.1",
  created_at: now,
};

for (const width of [1440, 390]) {
  test(`one product context preserves PUT terms and deletes opened Beta at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    let current = { ...beta };
    let terms: WarrantTermsResponse[] = [{ ...originalTerms }];
    let deleted = false;
    const writes: { method: string; path: string; body: unknown }[] = [];
    const unexpected: string[] = [];

    await page.route("**/api/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      const method = request.method();
      if (method !== "GET") {
        writes.push({
          method,
          path: `${path}${url.search}`,
          body: request.postData() ? request.postDataJSON() : null,
        });
      }
      if (method === "GET" && path.endsWith("/market-reference-data/issuers")) {
        return route.fulfill({
          json: {
            items: [
              {
                id: issuerId,
                legal_name: "Synthetic Bank AG",
                display_name: "Synthetic Bank",
                country_code: "DE",
                lei: null,
              },
            ],
          },
        });
      }
      if (
        method === "GET" &&
        path.endsWith("/market-reference-data/trading-venues")
      ) {
        return route.fulfill({ json: { items: [] } });
      }
      if (
        method === "GET" &&
        path.endsWith("/market-reference-data/currencies")
      ) {
        return route.fulfill({
          json: {
            items: [
              {
                code: "EUR",
                name: "Euro",
                minor_unit: 2,
                reference_version: "synthetic",
              },
              {
                code: "USD",
                name: "US-Dollar",
                minor_unit: 2,
                reference_version: "synthetic",
              },
            ],
          },
        });
      }
      if (method === "GET" && path.endsWith("/underlyings")) {
        return route.fulfill({
          json: {
            items: [
              {
                id: underlyingId,
                type: "STOCK",
                name: "Synthetic underlying",
                isin: null,
                wkn: null,
                lifecycle_status: "ACTIVE",
                quality_status: "COMPLETE",
                version: 1,
                created_at: now,
                updated_at: now,
                primary_listing: null,
              },
            ],
            total: 1,
            offset: 0,
            limit: 100,
          },
        });
      }
      if (method === "GET" && path.endsWith("/warrants")) {
        return route.fulfill({ json: deleted ? [alpha] : [alpha, current] });
      }
      if (method === "GET" && path.endsWith(`/warrants/${alpha.id}`)) {
        return route.fulfill({ json: alpha });
      }
      if (method === "GET" && path.endsWith(`/warrants/${beta.id}`)) {
        return route.fulfill({ json: current });
      }
      if (method === "GET" && path.endsWith(`/warrants/${alpha.id}/terms`)) {
        return route.fulfill({
          json: [
            {
              ...originalTerms,
              id: "20000000-0000-4000-8000-00000000000a",
              warrant_id: alpha.id,
              option_direction: "CALL",
              strike: "80",
              strike_currency_code: "EUR",
            },
          ],
        });
      }
      if (method === "GET" && path.endsWith(`/warrants/${beta.id}/terms`)) {
        return route.fulfill({ json: terms });
      }
      if (method === "GET" && /\/warrants\/[^/]+\/listings$/.test(path)) {
        return route.fulfill({ json: [] });
      }
      if (method === "POST" && path.endsWith(`/warrants/${beta.id}/terms`)) {
        const submitted = request.postDataJSON() as AddWarrantTermsRequest;
        expect(submitted).toEqual({
          expected_version: 7,
          option_direction: "PUT",
          strike: "123.45",
          strike_currency_code: "USD",
          maturity_date: "2027-09-17",
          ratio: "0.1",
        });
        const next: WarrantTermsResponse = {
          ...originalTerms,
          id: "20000000-0000-4000-8000-00000000000c",
          version_no: 5,
          effective_from: changedAt,
          created_at: changedAt,
          maturity_date: submitted.maturity_date,
        };
        terms = [next, { ...originalTerms, effective_to: changedAt }];
        current = { ...current, version: 8, updated_at: changedAt };
        return route.fulfill({ status: 201, json: next });
      }
      if (method === "DELETE" && path.endsWith(`/warrants/${beta.id}`)) {
        expect(url.searchParams.get("version")).toBe("8");
        deleted = true;
        return route.fulfill({ status: 204 });
      }
      unexpected.push(`${method} ${path}`);
      return route.fulfill({
        status: 500,
        json: { message: "Unexpected synthetic API request" },
      });
    });

    await page.goto("/warrants-admin");
    const alphaButton = page.getByRole("button", {
      name: new RegExp(alpha.display_name),
    });
    const betaButton = page.getByRole("button", {
      name: new RegExp(beta.display_name),
    });
    await expect(alphaButton).toBeVisible();
    await expect(betaButton).toBeVisible();
    const catalogueOrder = await page.getByRole("button").allTextContents();
    expect(
      catalogueOrder.findIndex((label) => label.includes(alpha.display_name)),
    ).toBeLessThan(
      catalogueOrder.findIndex((label) => label.includes(beta.display_name)),
    );
    await betaButton.focus();
    await expect(betaButton).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: beta.display_name, exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Neues Produkt", exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Anzeigename *", { exact: true })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("button", { name: "Optionsschein anlegen", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("combobox", { name: "Optionsschein", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("heading", {
        name: "Aktuelle Produktbedingungen",
        exact: true,
      }),
    ).toHaveCount(1);
    expect(writes).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await testInfo.attach(`product-beta-reading-${width}`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });

    const edit = page.getByRole("button", {
      name: "Produktbedingungen ändern",
      exact: true,
    });
    await edit.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("combobox", { name: "Neue Richtung", exact: true }),
    ).toHaveValue("PUT");
    await expect(
      page.getByRole("combobox", { name: "Neue Richtung", exact: true }),
    ).toBeFocused();
    await expect(page.getByLabel("Neuer Strike", { exact: true })).toHaveValue(
      "123.45",
    );
    await expect(
      page.getByLabel("Neue Strike-Währung", { exact: true }),
    ).toHaveValue("USD");
    await expect(
      page.getByLabel("Neue Fälligkeit", { exact: true }),
    ).toHaveValue("2027-06-18");
    await expect(
      page.getByLabel("Neues Bezugsverhältnis", { exact: true }),
    ).toHaveValue("0.1");
    // Cancel is read-only; reopening gets the same stored current version.
    await page
      .getByRole("button", { name: "Bedingungen abbrechen", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    expect(writes).toEqual([]);
    await expect(edit).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("combobox", { name: "Neue Richtung", exact: true }),
    ).toBeFocused();
    await page
      .getByLabel("Neue Fälligkeit", { exact: true })
      .fill("2027-09-17");

    // A real DataRouter navigation must preserve the draft when the user stays.
    const otherPage = page.getByRole("link", {
      name: "Stammdaten · Basiswerte",
      exact: true,
    });
    await otherPage.click();
    const navigationDialog = page.getByRole("alertdialog", {
      name: "Ungespeicherte Änderungen",
      exact: true,
    });
    await expect(navigationDialog).toBeVisible();
    const stay = navigationDialog.getByRole("button", {
      name: "Auf dieser Seite bleiben",
      exact: true,
    });
    const leave = navigationDialog.getByRole("button", {
      name: "Änderungen verwerfen und verlassen",
      exact: true,
    });
    await expect(stay).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(leave).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(stay).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(leave).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(stay).toBeFocused();
    await testInfo.attach(`product-beta-unsaved-navigation-${width}`, {
      body: await page.screenshot(),
      contentType: "image/png",
    });
    await page.keyboard.press("Escape");
    await expect(navigationDialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/warrants-admin$/);
    await expect(
      page.getByLabel("Neue Fälligkeit", { exact: true }),
    ).toHaveValue("2027-09-17");
    expect(writes).toEqual([]);
    await otherPage.focus();
    await page.keyboard.press("Enter");
    await expect(stay).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(navigationDialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/warrants-admin$/);
    await expect(
      page.getByLabel("Neue Fälligkeit", { exact: true }),
    ).toHaveValue("2027-09-17");
    expect(writes).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await testInfo.attach(`product-beta-terms-editor-${width}`, {
      body: await page
        .getByRole("form", { name: "Produktbedingungen ändern", exact: true })
        .screenshot(),
      contentType: "image/png",
    });
    await page
      .getByRole("button", { name: "Neue Terms-Version", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByLabel("Neue Fälligkeit", { exact: true }),
    ).toHaveCount(0);
    await expect(edit).toBeEnabled();
    expect(writes).toHaveLength(1);
    expect(writes[0]).toMatchObject({
      method: "POST",
      path: expect.stringContaining(`/warrants/${beta.id}/terms`),
    });

    await page.reload();
    // No mutation on reload. Re-open Beta if the catalogue is the entry view.
    await page
      .getByRole("button", { name: new RegExp(beta.display_name) })
      .click();
    await expect(
      page.getByRole("heading", { name: beta.display_name, exact: true }),
    ).toBeVisible();
    await expect(edit).toBeEnabled();
    await edit.click();
    await expect(
      page.getByLabel("Neue Fälligkeit", { exact: true }),
    ).toHaveValue("2027-09-17");
    await expect(
      page.getByRole("combobox", { name: "Neue Richtung", exact: true }),
    ).toHaveValue("PUT");
    await expect(page.getByLabel("Neuer Strike", { exact: true })).toHaveValue(
      "123.45",
    );
    await expect(
      page.getByLabel("Neue Strike-Währung", { exact: true }),
    ).toHaveValue("USD");
    await expect(
      page.getByLabel("Neues Bezugsverhältnis", { exact: true }),
    ).toHaveValue("0.1");
    await page
      .getByRole("button", { name: "Bedingungen abbrechen", exact: true })
      .click();
    await expect(edit).toBeFocused();
    expect(writes).toHaveLength(1);
    expect(terms[1]).toEqual({ ...originalTerms, effective_to: changedAt });
    await testInfo.attach(`product-beta-saved-${width}`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });

    const more = page
      .locator("summary")
      .filter({ hasText: "Weitere Aktionen" });
    await more.focus();
    await page.keyboard.press("Enter");
    let confirmation = "";
    page.once("dialog", async (dialog) => {
      confirmation = dialog.message();
      await dialog.accept();
    });
    await page
      .getByRole("button", { name: "Endgültig löschen", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect.poll(() => writes.length).toBe(2);
    expect(confirmation).toContain(beta.display_name);
    expect(confirmation).toContain(beta.isin);
    expect(confirmation).not.toContain(alpha.display_name);
    expect(writes[1]).toEqual({
      method: "DELETE",
      path: expect.stringMatching(
        new RegExp(`/warrants/${beta.id}\\?version=8$`),
      ),
      body: null,
    });
    await expect(
      page.getByRole("button", { name: new RegExp(beta.display_name) }),
    ).toHaveCount(0);
    await expect(alphaButton).toBeVisible();
    expect(unexpected).toEqual([]);
  });
}
