import { expect, test, type Route } from "@playwright/test";

const tradePlanId = "10000000-0000-4000-8000-000000000001";
const versionId = "10000000-0000-4000-8000-000000000002";
const underlyingId = "10000000-0000-4000-8000-000000000003";
const runId = "10000000-0000-4000-8000-000000000004";
const actorId = "10000000-0000-4000-8000-000000000005";
const now = "2026-08-16T10:00:00Z";
const productSelectionRoute =
  /\/api\/api\/v1\/product-selection-runs(?:\/.*)?(?:\?.*)?$/;

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

test("approved TradePlan handoff shows missing warrant quote transparently and blocks selection", async ({
  page,
}) => {
  const notEvaluable = evaluation(
    "20000000-0000-4000-8000-000000000001",
    "NOT_EVALUABLE",
    {
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
          explanation:
            "No verified WarrantListing quote snapshot is available.",
          actual_value: null,
          expected_value: "verified bid/ask snapshot",
          data_availability: "MISSING",
        },
      ],
      reasons: [
        "WarrantListing quote data is unavailable or provider capability is unverified.",
      ],
    },
  );
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
  await expect(page.getByLabel("TradePlan-ID")).toHaveValue(tradePlanId);
  await expect(page.getByLabel("TradePlanVersion-ID")).toHaveValue(versionId);
  await page.getByRole("button", { name: "Produkte neu bewerten" }).click();

  await expect(
    page.getByText("NOT_EVALUABLE", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText(
      "WarrantListing quote data is unavailable or provider capability is unverified.",
    ),
  ).toBeVisible();
  await expect(page.getByText("NO_ACTIVE_LISTING")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Dieses Produkt auswählen" }),
  ).toBeDisabled();

  await page.getByText("Bewertungsdetails").click();
  await expect(
    page.getByText("No verified WarrantListing quote snapshot is available."),
  ).toBeVisible();
  await expect(
    page.getByText(/kein Wert · Quelle warrant-listing-market-data/).first(),
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

  await expect(
    page.getByText("ELIGIBLE", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("1.20 EUR", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("1.24 EUR", { exact: true }).first()).toBeVisible();
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
