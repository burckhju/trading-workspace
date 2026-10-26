import { randomUUID } from "node:crypto";
import { expect, test, type APIResponse, type Request } from "@playwright/test";
import type { TradePlanVersionResponse } from "../../frontend/src/features/trade_plan/types/api";

test.use({
  baseURL: process.env.TRADE_E2E_UI_URL ?? "http://localhost:8080",
  timezoneId: "Europe/Berlin",
  serviceWorkers: "block",
  trace: "on",
});
test.skip(
  process.env.TRADE_E2E_WRITES_ALLOWED !== "1",
  "Requires an explicitly disposable test stack; never enable on a user depot",
);

async function body(
  response: Pick<APIResponse, "status" | "text" | "json">,
  status = 201,
) {
  expect(response.status(), await response.text()).toBe(status);
  return response.json();
}

function content(version: TradePlanVersionResponse) {
  return {
    thesis: version.thesis,
    entry: version.entry,
    invalidation: version.invalidation,
    targets: version.targets,
    risk_assumptions: version.risk_assumptions,
  };
}

// No route mocks. All stored rows are created through their existing owner APIs.
test("native plan context: full TRIGGER amendment and separate approval preserve the historical run and BUY", async ({
  page,
  request,
}, testInfo) => {
  const api = process.env.TRADE_E2E_API_URL ?? "http://127.0.0.1:8000/api/v1";
  const token = randomUUID().slice(0, 8);
  const get = async (path: string) =>
    body(await request.get(`${api}${path}`), 200);
  const post = async (path: string, data?: object, status = 201) =>
    body(await request.post(`${api}${path}`, data ? { data } : {}), status);
  const issuer = await post("/market-reference-data/issuers", {
    legal_name: `Synthetic amendment ${randomUUID()}`,
    display_name: `Synthetic amendment ${token}`,
  });
  const venues = await get("/market-reference-data/trading-venues");
  const venueId = venues.items.find(
    (venue: { mic: string }) => venue.mic === "XETR",
  ).id;
  const underlying = await post("/underlyings", {
    name: `Synthetic amendment stock ${token}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venueId,
      ticker: `AM${token}`,
      currency_code: "USD",
    },
  });
  const warrant = await post("/warrants", {
    issuer_id: issuer.id,
    underlying_id: underlying.id,
    display_name: `Synthetic amendment warrant ${token}`,
    option_direction: "CALL",
    strike: "100",
    strike_currency_code: "USD",
    maturity_date: "2099-12-31",
    ratio: "0.1",
  });
  await post(`/warrants/${warrant.id}/listings`, {
    trading_venue_id: venueId,
    symbol: `AML${token}`,
    quotation_currency_code: "EUR",
  });
  const created = await post("/trade-plans", {
    origin_type: "MANUAL",
    underlying_id: underlying.id,
    thesis: "Synthetic original trigger thesis; no investment recommendation",
    entry: {
      type: "TRIGGER",
      currency: "USD",
      price: null,
      price_from: null,
      price_to: null,
      trigger: "Confirmed close above the daily breakout level",
      reference_price: "100.12345678901234567890",
      valid_until: "2027-12-31T15:45:00Z",
      rationale: "Original complete entry explanation",
    },
    invalidation: {
      stop_price: "95.12345678901234567890",
      invalidation_rule: "Confirmed close below support",
      rationale: "Original complete invalidation explanation",
    },
    targets: [
      {
        sequence: 1,
        price: "110.12345678901234567890",
        rationale: "First original target explanation",
      },
      {
        sequence: 2,
        price: "120.12345678901234567890",
        rationale: "Second original target explanation",
      },
      {
        sequence: 3,
        price: "130.12345678901234567890",
        rationale: "Third original target explanation",
      },
    ],
    risk_assumptions: {
      thesis_risk: "Synthetic failed-breakout risk",
      max_loss_assumption: "Explicit original loss assumption",
      notes: "All original risk notes, without position-sizing instructions",
    },
  });
  const planId = created.plan.id;
  const baseId = created.latest_version.id;
  const baseUrl = `/trade-plans/${planId}/versions/${baseId}`;
  await post(`${baseUrl}/submit-review`, undefined, 200);
  await post(`${baseUrl}/approve`, undefined, 200);
  const original: TradePlanVersionResponse = await get(baseUrl);
  const run = await post("/product-selection-runs", {
    trade_plan_id: planId,
    trade_plan_version_id: baseId,
  });
  expect(run.evaluations).toHaveLength(1);
  expect(run.evaluations[0].eligibility_status).toBe("NOT_EVALUABLE");
  const selected = await post(
    `/product-selection-runs/${run.run.id}/selection`,
    {
      product_evaluation_id: run.evaluations[0].id,
      rationale: "Synthetic explicit selection with incomplete quote evidence",
    },
  );
  const purchase = await post("/trade-position/purchases/from-selection", {
    product_selection_id: selected.selection.id,
    quantity: 10,
    price_per_unit: "2.35",
    executed_on: "2026-10-24",
    execution_timezone: "Europe/Berlin",
    request_id: randomUUID(),
    currency_confirmation: {
      currency_code: "EUR",
      source: "USER_CONFIRMED",
      note: "Explicit synthetic execution currency, separate from USD plan",
    },
  });
  expect(purchase.trade.trade_plan_version_id).toBe(baseId);
  expect(purchase.execution.currency_confirmation.currency_code).toBe("EUR");
  const runBefore = await get(`/product-selection-runs/${run.run.id}`);
  const tradeBefore = await get(`/trade-position/trades/${purchase.trade.id}`);
  const timelineBefore = await get(
    `/trade-position/trades/${purchase.trade.id}/timeline`,
  );
  const writes: Request[] = [];
  page.on("request", (outgoing) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(outgoing.method()))
      writes.push(outgoing);
  });

  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(
    `/trade-plans?trade_plan_id=${planId}&trade_plan_version_id=${baseId}`,
  );
  await expect(
    page.getByRole("heading", { name: "Version 1 · APPROVED", exact: true }),
  ).toBeVisible();
  const amend = page.getByRole("button", {
    name: "Neue Planversion erstellen",
    exact: true,
  });
  await amend.focus();
  await expect(amend).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Neue Planversion aus Version 1" }),
  ).toBeVisible();
  await expect(page.getByLabel("Entry-Art")).toHaveValue("TRIGGER");
  await expect(page.getByLabel("Währung", { exact: true })).toHaveValue("USD");
  await expect(
    page.getByRole("textbox", { name: "Trigger", exact: true }),
  ).toHaveValue(original.entry.trigger!);
  await expect(page.getByLabel("Invalidierungsbegründung")).toHaveValue(
    original.invalidation.rationale!,
  );
  for (const target of original.targets) {
    await expect(
      page.getByLabel(`Target ${target.sequence}`, { exact: true }),
    ).toHaveValue(target.price);
    await expect(
      page.getByLabel(`Target-Begründung ${target.sequence}`, { exact: true }),
    ).toHaveValue(target.rationale!);
  }
  await page.getByText("Weitere Entry-Angaben", { exact: true }).click();
  await expect(page.getByLabel("Referenzpreis")).toHaveValue(
    original.entry.reference_price!,
  );
  await expect(
    page.getByLabel("Gültig bis (ISO 8601 mit Zeitzone)"),
  ).toHaveValue(original.entry.valid_until!);
  await expect(page.getByLabel("Entry-Begründung")).toHaveValue(
    original.entry.rationale!,
  );
  await page.getByText("Weitere Risikoangaben", { exact: true }).click();
  await expect(page.getByLabel("Max-Loss-Annahme (optional)")).toHaveValue(
    original.risk_assumptions.max_loss_assumption!,
  );
  await expect(page.getByLabel("Risk Notes")).toHaveValue(
    original.risk_assumptions.notes!,
  );
  const thesis = "Only the synthetic thesis is clarified";
  const reason = "Explicit thesis-only amendment";
  await page.getByLabel("Trade Thesis").fill(thesis);
  await page.getByLabel("Änderungsgrund").fill(reason);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await testInfo.attach("native full TRIGGER amendment 390px", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  const amendmentResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`${baseUrl}/amendments`),
  );
  const save = page.getByRole("button", {
    name: "Neue DRAFT-Version speichern",
  });
  await save.focus();
  await expect(save).toBeFocused();
  await page.keyboard.press("Enter");
  const draft: TradePlanVersionResponse = await body(await amendmentResponse);
  expect(writes).toHaveLength(1);
  expect(writes[0].postDataJSON()).toEqual({
    ...content(original),
    thesis,
    change_reason: reason,
  });
  expect(draft).toMatchObject({
    version: 2,
    status: "DRAFT",
    previous_version_id: baseId,
  });
  expect(content(draft)).toEqual({ ...content(original), thesis });
  await expect(
    page.getByRole("heading", { name: "Version 2 · DRAFT", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Trade Thesis")).toHaveCount(0);
  expect(await get(baseUrl)).toEqual(original);
  expect(await get(`/product-selection-runs/${run.run.id}`)).toEqual(runBefore);
  expect(
    await get(`/trade-position/trades/${purchase.trade.id}/timeline`),
  ).toEqual(timelineBefore);

  // The newest draft must not hide the still-approved V1 in the explicit picker.
  await page.goto("/product-selection");
  const oldPlanChoice = page.locator(
    `a[href="/product-selection?trade_plan_id=${planId}&trade_plan_version_id=${baseId}"]`,
  );
  await expect(oldPlanChoice).toBeVisible();
  await oldPlanChoice.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Version 1 · APPROVED", { exact: true }),
  ).toBeVisible();
  expect(writes).toHaveLength(1);

  // Approval is a second, separate explicit workflow; it does not create another run or BUY.
  await page.goto(
    `/trade-plans?trade_plan_id=${planId}&trade_plan_version_id=${draft.id}`,
  );
  await page.getByRole("button", { name: "Zur Prüfung einreichen" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Version 2 · READY_FOR_REVIEW",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explizit freigeben" }).click();
  await expect(
    page.getByRole("heading", { name: "Version 2 · APPROVED", exact: true }),
  ).toBeVisible();
  const oldVersion: TradePlanVersionResponse = await get(baseUrl);
  expect(oldVersion.status).toBe("SUPERSEDED");
  expect(content(oldVersion)).toEqual(content(original));
  expect(oldVersion.approval).toEqual(original.approval);
  expect(await get(`/product-selection-runs/${run.run.id}`)).toEqual(runBefore);
  expect(await get(`/trade-position/trades/${purchase.trade.id}`)).toEqual(
    tradeBefore,
  );
  expect(
    await get(`/trade-position/trades/${purchase.trade.id}/timeline`),
  ).toEqual(timelineBefore);
  expect(
    writes.map(
      (sent) => new URL(sent.url()).pathname.split("/trade-plans/")[1],
    ),
  ).toEqual([
    `${planId}/versions/${baseId}/amendments`,
    `${planId}/versions/${draft.id}/submit-review`,
    `${planId}/versions/${draft.id}/approve`,
  ]);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/product-selection?run_id=${run.run.id}`);
  await expect(
    page.getByText("Version 1 · SUPERSEDED", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Produkte neu bewerten", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Produkt ausgewählt", { exact: true }),
  ).toBeVisible();
  expect(writes).toHaveLength(3);
  await testInfo.attach(
    "native historical run after separate approval 1280px",
    {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    },
  );
  await testInfo.attach(
    "native exact versions and unchanged historical sources",
    {
      body: JSON.stringify(
        {
          planId,
          original,
          amendmentRequest: writes[0].postDataJSON(),
          draft,
          oldVersion,
          runBefore,
          runAfter: await get(`/product-selection-runs/${run.run.id}`),
          tradeBefore,
          tradeAfter: await get(`/trade-position/trades/${purchase.trade.id}`),
          timelineBefore,
          timelineAfter: await get(
            `/trade-position/trades/${purchase.trade.id}/timeline`,
          ),
        },
        null,
        2,
      ),
      contentType: "application/json",
    },
  );
});
