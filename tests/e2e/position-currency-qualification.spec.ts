import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import type { OperationalPositionsResponse } from "../../frontend/src/features/operational_workspace/types";
import type { ProductPositionValuationResponse } from "../../frontend/src/features/trade/types/api";

// This contract fixture is generated and fully compared by the PostgreSQL
// owner -> valuation -> HTTP regression. Amounts and qualifications are not
// recreated in this browser test.
function backendFixture() {
  return JSON.parse(
    readFileSync(
      fileURLToPath(
        new URL(
          "../fixtures/position_currency_qualification.json",
          import.meta.url,
        ),
      ),
      "utf8",
    ),
  ) as {
    positions_response: OperationalPositionsResponse;
    valuations: Record<string, ProductPositionValuationResponse>;
  };
}

async function setup(page: Page, baseURL: string) {
  const fixture = backendFixture();
  const writes: string[] = [];
  const external: string[] = [];
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/")) {
      if (
        url.origin === new URL(baseURL).origin &&
        ["document", "script", "stylesheet", "image", "font"].includes(
          request.resourceType(),
        )
      )
        return route.continue();
      external.push(url.href);
      return route.abort();
    }
    if (request.method() !== "GET") {
      writes.push(`${request.method()} ${url.pathname}`);
      return route.fulfill({
        status: 405,
        json: { message: "Read-only synthetic browser fixture" },
      });
    }
    const positions = fixture.positions_response.positions;
    const p = positions.find((item) => url.pathname.includes(item.trade_id));
    let body: unknown = [];
    if (url.pathname.endsWith("/operational-workspace/actions")) {
      body = {
        generated_at: fixture.positions_response.generated_at,
        actions: [],
      };
    } else if (url.pathname.endsWith("/operational-workspace/positions")) {
      body = fixture.positions_response;
    } else if (p && url.pathname.endsWith("/product-valuation")) {
      body = fixture.valuations[p.trade_id];
    } else if (p && url.pathname.endsWith("/position")) {
      body = {
        ...p.position_basis!.position,
        is_closed: false,
        is_cancelled: false,
      };
    } else if (p && url.pathname.endsWith(`/trades/${p.trade_id}`)) {
      body = {
        id: p.trade_id,
        product_id: p.position_basis!.position.product_id,
        origin: "EXTERNAL",
        trade_plan_id: null,
        trade_plan_version_id: null,
        product_selection_id: null,
        product_evaluation_id: null,
        created_at: p.opened_at,
      };
    } else if (p && url.pathname.endsWith("/management")) {
      body = {
        trade_id: p.trade_id,
        stop_price: null,
        target_price: null,
        thesis: null,
        notes: [],
      };
    } else if (p && url.pathname.endsWith("/alert-projection")) {
      body = p.position_signal ?? {
        trade_id: p.trade_id,
        position_id: p.position_id,
        quality_status: "MISSING",
        alert_level: null,
        attention_required: false,
        reason: "SYNTHETIC_READ_ONLY_FIXTURE",
        candidate_stop: null,
        latest_price: null,
        phase: null,
        policy_version: "V1",
        dynamic_stop_policy_version: "V1",
        analysis_run_id: null,
      };
    } else if (url.pathname.includes("/warrants/")) {
      const product = positions.find((item) =>
        url.pathname.includes(item.position_basis!.position.product_id),
      );
      if (product)
        body = {
          id: product.position_basis!.position.product_id,
          display_name: product.product_name,
          isin: product.product_isin,
          wkn: product.product_wkn,
        };
    }
    return route.fulfill({ status: 200, json: body });
  });
  return { fixture, writes, external };
}

test("backend currency qualification reaches depot rows, filter, sort, EUR totals and coverage", async ({
  page,
  baseURL,
}, testInfo) => {
  const { writes, external } = await setup(page, baseURL!);
  await page.goto("/workspace");
  const rows = page.locator("tbody > tr[data-position-id]");
  await expect(rows).toHaveCount(6);
  for (const name of ["unknown", "mismatch", "mixed"]) {
    const row = page.getByRole("row", { name: new RegExp(`Currency ${name}`) });
    await expect(row.getByText("25,00 EUR", { exact: true })).toBeVisible();
    const pnlCell = row
      .getByRole("cell")
      .filter({ hasText: "Gewinn/Verlust ist nicht berechenbar" });
    await expect(pnlCell).toContainText("—");
    await expect(pnlCell).toHaveClass(/text-slate-300/);
    await expect(row).not.toContainText("+5,00 EUR");
    await expect(row).toContainText("Gewinn/Verlust ist nicht berechenbar");
  }
  await expect(
    page
      .getByRole("row", { name: /Currency gain/ })
      .getByText("+5,00 EUR", { exact: true }),
  ).toHaveClass(/text-emerald-300/);
  await expect(
    page
      .getByRole("row", { name: /Currency loss/ })
      .getByText("−5,00 EUR", { exact: true }),
  ).toHaveClass(/text-rose-300/);
  await expect(
    page
      .getByRole("row", { name: /Currency neutral/ })
      .getByText("0,00 EUR", { exact: true }),
  ).toHaveClass(/text-slate-300/);
  await page.getByText(/Bewertungssummen je Währung/).click();
  await expect(
    page.getByText("Marktwert: 135,00 EUR · 6/6 bewertet", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Nicht realisierter Brutto-G/V: 0,00 EUR · 3/6 verfügbar", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Gewinn", exact: true }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Currency gain");
  await page.getByRole("button", { name: "Verlust", exact: true }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Currency loss");
  await page.getByRole("button", { name: "Alle offenen Positionen" }).click();
  await page.getByLabel("Sortierung", { exact: true }).selectOption("pnl");
  await expect(rows.first()).toContainText("Currency loss");
  await expect(rows.nth(1)).toContainText("Currency neutral");
  await expect(rows.nth(2)).toContainText("Currency gain");
  await page.getByLabel("Reihenfolge").selectOption("desc");
  await expect(rows.first()).toContainText("Currency gain");
  await expect(rows.nth(1)).toContainText("Currency neutral");
  await expect(rows.nth(2)).toContainText("Currency loss");
  for (const index of [3, 4, 5])
    await expect(rows.nth(index)).toContainText("nicht berechenbar");
  const unknown = page.getByRole("row", { name: /Currency unknown/ });
  await unknown.getByRole("button", { name: "Details", exact: true }).click();
  const details = page.getByRole("region", {
    name: "Details Currency unknown",
  });
  await expect(details).toContainText(
    "Kaufwährung ist für mindestens einen wirksamen Kauf der Kostenbasis nicht belegt",
  );
  await expect(details.getByText("25,00 EUR", { exact: true })).toBeVisible();
  await details
    .getByText("Kostenbasis und Währungsnachweise", { exact: true })
    .click();
  await expect(details).toContainText("position-unrealized-gross-v1");
  await expect(details).toContainText(
    "Kostenbasiswährung: Nicht vollständig belegt",
  );
  await testInfo.attach(
    "Qualified PnL coverage with retained EUR market values",
    {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    },
  );
  expect(writes).toEqual([]);
  expect(external).toEqual([]);
});

test("the same backend qualification and sources remain visible after opening trade management", async ({
  page,
  baseURL,
}) => {
  const { fixture, writes, external } = await setup(page, baseURL!);
  const mismatch = fixture.positions_response.positions.find(
    (p) => p.product_name === "Currency mismatch",
  )!;
  await page.goto("/workspace");
  await page
    .getByRole("row", { name: /Currency mismatch/ })
    .getByRole("link", { name: "Trade verwalten", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`trade_id=${mismatch.trade_id}`));
  const panel = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "Produktbewertung", exact: true }),
    });
  await expect(panel.getByText("25 EUR", { exact: true })).toBeVisible();
  await expect(panel.getByText("5 EUR", { exact: true })).toHaveCount(0);
  await expect(panel).toContainText(
    "Kaufwährung der Kostenbasis stimmt nicht mit der Kurswährung überein",
  );
  await panel
    .getByText("Kostenbasis und Währungsnachweise", { exact: true })
    .click();
  await expect(panel).toContainText("Kostenbasiswährung: USD");
  await expect(panel).toContainText(mismatch.position_basis!.basis_id);
  for (const evidence of mismatch.position_basis!.buy_currency_evidence) {
    await expect(panel).toContainText(evidence.execution_id);
    for (const id of evidence.confirmation_ids)
      await expect(panel).toContainText(id);
  }
  await expect(panel).toContainText("Bewertungsquelle:");
  expect(writes).toEqual([]);
  expect(external).toEqual([]);
});
