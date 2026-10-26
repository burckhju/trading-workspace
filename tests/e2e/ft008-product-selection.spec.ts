import { expect, test, type Route } from "@playwright/test";
import { planContextFixture } from "./support/plan-context-fixtures";

const tradePlanId = "10000000-0000-4000-8000-000000000001";
const versionId = "10000000-0000-4000-8000-000000000002";
const underlyingId = "10000000-0000-4000-8000-000000000003";
const runId = "10000000-0000-4000-8000-000000000004";
const actorId = "10000000-0000-4000-8000-000000000005";
const now = "2026-08-16T10:00:00Z";
const productSelectionRoute =
  /\/api\/api\/v1\/product-selection-runs(?:\/.*)?(?:\?.*)?$/;

const approvedPlan = planContextFixture(tradePlanId, versionId, underlyingId);

test.beforeEach(async ({ page }) => {
  await page.route(
    /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/,
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith(`/${tradePlanId}/versions/${versionId}`))
        return json(route, approvedPlan.latest_version);
      if (path.endsWith(`/${tradePlanId}/versions`))
        return json(route, [approvedPlan.latest_version]);
      if (path.endsWith(`/${tradePlanId}`)) return json(route, approvedPlan);
      return json(route, [
        {
          id: tradePlanId,
          underlying_id: underlyingId,
          underlying_name: "Synthetischer Planbasiswert",
          origin_type: "MANUAL",
          created_at: now,
          latest_version_id: versionId,
          latest_version: 1,
          status: "APPROVED",
          selected_product: null,
        },
      ]);
    },
  );
});

function summary() {
  return {
    id: runId,
    trade_plan_id: tradePlanId,
    trade_plan_version_id: versionId,
    trade_plan_version_status: "APPROVED",
    underlying_id: underlyingId,
    evaluated_at: now,
    universe_model: { model_id: "ft008-universe", model_version: "1.0.0" },
    eligibility_model: {
      model_id: "ft008-eligibility",
      model_version: "1.0.0",
    },
    evaluation_model: { model_id: "ft008-evaluation", model_version: "1.0.0" },
    created_at: now,
    created_by: actorId,
  };
}

function evaluation(
  id: string,
  status: "ELIGIBLE" | "INELIGIBLE" | "NOT_EVALUABLE",
  overrides: Record<string, unknown> = {},
) {
  return {
    id,
    run_id: runId,
    warrant_id: `${id.slice(0, -1)}a`,
    warrant_terms_version_id: `${id.slice(0, -1)}b`,
    warrant_listing_id: `${id.slice(0, -1)}c`,
    evaluated_at: now,
    eligibility_model: {
      model_id: "ft008-eligibility",
      model_version: "1.0.0",
    },
    evaluation_model: { model_id: "ft008-evaluation", model_version: "1.0.0" },
    inputs: [],
    criteria: [],
    metrics: [],
    eligibility_status: status,
    reasons: [],
    ...overrides,
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

test("approved TradePlan handoff keeps missing quote visible and allows an explicit not-evaluable selection", async ({
  page,
}) => {
  const evaluationId = "20000000-0000-4000-8000-000000000001";
  const notEvaluable = evaluation(evaluationId, "NOT_EVALUABLE", {
    inputs: [
      {
        name: "bid",
        value: null,
        availability: "MISSING",
        source: "warrant-listing-market-data",
        observed_at: null,
        quality: null,
      },
      {
        name: "ask",
        value: null,
        availability: "MISSING",
        source: "warrant-listing-market-data",
        observed_at: null,
        quality: null,
      },
    ],
    criteria: [
      {
        criterion_id: "market_data_available",
        outcome: "NOT_EVALUABLE",
        explanation: "No verified WarrantListing quote snapshot is available.",
        actual_value: null,
        expected_value: "verified bid/ask snapshot",
        data_availability: "MISSING",
      },
    ],
    reasons: [
      "WarrantListing quote data is unavailable or provider capability is unverified.",
    ],
  });
  const detail = {
    run: summary(),
    evaluations: [notEvaluable],
    universe_omissions: [
      {
        warrant_id: "30000000-0000-4000-8000-000000000001",
        reason: "NO_ACTIVE_LISTING",
        explanation: "No active WarrantListing exists for the evaluation time.",
      },
    ],
    selection: null,
  };
  const selected = {
    ...detail,
    selection: {
      id: "30000000-0000-4000-8000-000000000002",
      run_id: runId,
      product_evaluation_id: evaluationId,
      selected_at: "2026-08-16T10:05:00Z",
      selected_by: actorId,
      rationale: "Bewusst trotz fehlender Quote ausgewählt",
    },
  };
  let selectionPosts = 0;

  await page.route(productSelectionRoute, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      request.method() === "GET" &&
      url.searchParams.has("trade_plan_version_id")
    ) {
      return json(route, []);
    }
    if (
      request.method() === "POST" &&
      url.pathname.endsWith("/product-selection-runs")
    ) {
      expect(request.postDataJSON()).toMatchObject({
        trade_plan_id: tradePlanId,
        trade_plan_version_id: versionId,
      });
      return json(route, detail, 201);
    }
    if (
      request.method() === "POST" &&
      url.pathname.endsWith(`/${runId}/selection`)
    ) {
      selectionPosts += 1;
      expect(request.postDataJSON()).toEqual({
        product_evaluation_id: evaluationId,
        rationale: "Bewusst trotz fehlender Quote ausgewählt",
      });
      return json(route, selected, 201);
    }
    return json(
      route,
      {
        code: "E2E_ROUTE_MISSING",
        message: `${request.method()} ${url.pathname}`,
      },
      500,
    );
  });

  await page.goto(
    `/product-selection?trade_plan_id=${tradePlanId}&trade_plan_version_id=${versionId}`,
  );
  await expect(page.getByLabel("TradePlan-ID", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("TradePlanVersion-ID", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Version 1 · APPROVED", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Produkte neu bewerten" }).click();
  await expect(page).toHaveURL(`/product-selection?run_id=${runId}`);

  await expect(
    page.getByText("NOT_EVALUABLE", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText(
      "WarrantListing quote data is unavailable or provider capability is unverified.",
    ),
  ).toBeVisible();
  await expect(page.getByText("NO_ACTIVE_LISTING")).toBeVisible();
  const chooseButton = page.getByRole("button", {
    name: "Dieses Produkt auswählen",
  });
  await expect(chooseButton).toBeEnabled();

  await page.getByText("Bewertungsdetails").click();
  await expect(
    page.getByText("No verified WarrantListing quote snapshot is available."),
  ).toBeVisible();
  await expect(
    page.getByText(/kein Wert · Quelle warrant-listing-market-data/).first(),
  ).toBeVisible();

  await chooseButton.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Bewertung unvollständig")).toBeVisible();
  await expect(
    dialog.getByText(
      "WarrantListing quote data is unavailable or provider capability is unverified.",
    ),
  ).toBeVisible();
  const confirm = dialog.getByRole("button", { name: "Auswahl dokumentieren" });
  await expect(confirm).toBeDisabled();
  await dialog
    .getByLabel("Begründung (erforderlich bei nicht bewertbar)")
    .fill("Bewusst trotz fehlender Quote ausgewählt");
  await expect(confirm).toBeEnabled();
  await confirm.click();

  await expect.poll(() => selectionPosts).toBe(1);
  await expect(page.getByText("Produkt ausgewählt")).toBeVisible();
  await expect(
    page.getByText("Bewusst trotz fehlender Quote ausgewählt"),
  ).toBeVisible();
});

test("fixture-backed eligible quote requires explicit confirmation before one user selection is persisted", async ({
  page,
}) => {
  const evaluationId = "40000000-0000-4000-8000-000000000001";
  const eligible = evaluation(evaluationId, "ELIGIBLE", {
    inputs: [
      {
        name: "bid",
        value: "1.20",
        availability: "AVAILABLE",
        source: "fixture-warrant-provider",
        observed_at: now,
        quality: "GOOD",
      },
      {
        name: "ask",
        value: "1.24",
        availability: "AVAILABLE",
        source: "fixture-warrant-provider",
        observed_at: now,
        quality: "GOOD",
      },
    ],
    criteria: [
      {
        criterion_id: "market_data_available",
        outcome: "FULFILLED",
        explanation: "Verified listing quote snapshot is complete.",
        actual_value: "bid/ask available",
        expected_value: "verified bid/ask snapshot",
        data_availability: "AVAILABLE",
      },
    ],
    metrics: [
      {
        metric_id: "bid",
        value: "1.20",
        unit: "EUR",
        origin: "PROVIDER",
        source: "fixture-warrant-provider",
        formula_or_rule: null,
        data_availability: "AVAILABLE",
      },
      {
        metric_id: "ask",
        value: "1.24",
        unit: "EUR",
        origin: "PROVIDER",
        source: "fixture-warrant-provider",
        formula_or_rule: null,
        data_availability: "AVAILABLE",
      },
      {
        metric_id: "spread_percent",
        value: "3.2786885246",
        unit: "%",
        origin: "CALCULATED",
        source: "FT-008",
        formula_or_rule: "(ask - bid) / midpoint * 100",
        data_availability: "AVAILABLE",
      },
    ],
  });
  const detail = {
    run: summary(),
    evaluations: [eligible],
    universe_omissions: [],
    selection: null,
  };
  const selected = {
    ...detail,
    selection: {
      id: "50000000-0000-4000-8000-000000000001",
      run_id: runId,
      product_evaluation_id: evaluationId,
      selected_at: "2026-08-16T10:05:00Z",
      selected_by: actorId,
      rationale: "Nach transparentem Vergleich bewusst gewählt",
    },
  };
  let selectionPosts = 0;

  await page.route(productSelectionRoute, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      request.method() === "GET" &&
      url.searchParams.has("trade_plan_version_id")
    )
      return json(route, []);
    if (
      request.method() === "POST" &&
      url.pathname.endsWith("/product-selection-runs")
    )
      return json(route, detail, 201);
    if (
      request.method() === "POST" &&
      url.pathname.endsWith(`/${runId}/selection`)
    ) {
      selectionPosts += 1;
      expect(request.postDataJSON()).toEqual({
        product_evaluation_id: evaluationId,
        rationale: "Nach transparentem Vergleich bewusst gewählt",
      });
      return json(route, selected, 201);
    }
    return json(
      route,
      {
        code: "E2E_ROUTE_MISSING",
        message: `${request.method()} ${url.pathname}`,
      },
      500,
    );
  });

  await page.goto(
    `/product-selection?trade_plan_id=${tradePlanId}&trade_plan_version_id=${versionId}`,
  );
  await page.getByRole("button", { name: "Produkte neu bewerten" }).click();
  await expect(page).toHaveURL(`/product-selection?run_id=${runId}`);

  await expect(page.getByText("ELIGIBLE", { exact: true })).toBeVisible();
  await expect(
    page.getByText("1.20 EUR", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("1.24 EUR", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Dieses Produkt auswählen" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect.poll(() => selectionPosts).toBe(0);
  await page
    .getByLabel("Begründung (optional)")
    .fill("Nach transparentem Vergleich bewusst gewählt");
  await page.getByRole("button", { name: "Auswahl dokumentieren" }).click();

  await expect.poll(() => selectionPosts).toBe(1);
  await expect(page.getByText("Produkt ausgewählt")).toBeVisible();
  await expect(
    page.getByText("Nach transparentem Vergleich bewusst gewählt"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Ausgewählt" })).toBeDisabled();
});

test("explicit picker retains an approved version when the latest plan version is DRAFT", async ({
  page,
}) => {
  const draftId = "10000000-0000-4000-8000-000000000006";
  const draft = {
    ...approvedPlan.latest_version,
    id: draftId,
    version: 2,
    status: "DRAFT",
    approval: null,
    previous_version_id: versionId,
  };
  const writes: string[] = [];
  await page.route(
    /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/,
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (route.request().method() !== "GET") writes.push(path);
      if (path.endsWith(`/${tradePlanId}/versions/${versionId}`))
        return json(route, approvedPlan.latest_version);
      if (path.endsWith(`/${tradePlanId}/versions`))
        return json(route, [approvedPlan.latest_version, draft]);
      if (path.endsWith(`/${tradePlanId}`))
        return json(route, { ...approvedPlan, latest_version: draft });
      return json(route, [
        {
          id: tradePlanId,
          underlying_id: underlyingId,
          underlying_name: "Plan mit neuem Entwurf",
          origin_type: "MANUAL",
          created_at: now,
          latest_version_id: draftId,
          latest_version: 2,
          status: "DRAFT",
          selected_product: null,
        },
      ]);
    },
  );
  await page.route(productSelectionRoute, async (route) => {
    if (route.request().method() !== "GET")
      writes.push(new URL(route.request().url()).pathname);
    return json(route, []);
  });
  await page.goto("/product-selection");
  const choice = page.getByRole("link", {
    name: "Produktauswahl für diesen TradePlan öffnen",
    exact: true,
  });
  await expect(choice).toHaveAttribute(
    "href",
    `/product-selection?trade_plan_id=${tradePlanId}&trade_plan_version_id=${versionId}`,
  );
  await choice.focus();
  await expect(choice).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Version 1 · APPROVED", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Produkte neu bewerten", exact: true }),
  ).toBeEnabled();
  expect(writes).toEqual([]);
  await page
    .getByRole("button", { name: "Anderen Plan auswählen", exact: true })
    .click();
  await expect(page).toHaveURL(/\/product-selection$/);
  await expect(choice).toBeVisible();
  expect(writes).toEqual([]);
});

test("stored historical run remains pinned after a later approval and cannot silently start a replacement", async ({
  page,
}) => {
  const latestId = "10000000-0000-4000-8000-000000000006";
  const historical = { ...approvedPlan.latest_version, status: "SUPERSEDED" };
  const latest = {
    ...approvedPlan.latest_version,
    id: latestId,
    version: 2,
    previous_version_id: versionId,
  };
  const originalRun = {
    run: summary(),
    evaluations: [],
    universe_omissions: [],
    selection: null,
  };
  const writes: string[] = [];
  await page.route(
    /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/,
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith(`/${tradePlanId}/versions/${versionId}`))
        return json(route, historical);
      if (path.endsWith(`/${tradePlanId}`))
        return json(route, { ...approvedPlan, latest_version: latest });
      return json(route, []);
    },
  );
  await page.route(productSelectionRoute, async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() !== "GET") writes.push(path);
    if (path.endsWith(`/${runId}`)) return json(route, originalRun);
    return json(route, [originalRun.run]);
  });
  await page.goto(`/product-selection?run_id=${runId}`);
  await expect(
    page.getByText("Version 1 · SUPERSEDED", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Produkte neu bewerten", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("link", { name: "Ausgewählte Planversion ansehen" }),
  ).toHaveAttribute(
    "href",
    `/trade-plans?trade_plan_id=${tradePlanId}&trade_plan_version_id=${versionId}`,
  );
  await page.reload();
  await expect(
    page.getByText("Version 1 · SUPERSEDED", { exact: true }),
  ).toBeVisible();
  expect(originalRun.run.trade_plan_version_id).toBe(versionId);
  expect(writes).toEqual([]);
});
