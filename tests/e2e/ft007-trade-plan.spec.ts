import { expect, test, type Page, type Route } from "@playwright/test";
import type { TradePlanVersionResponse } from "../../frontend/src/features/trade_plan/types/api";
import {
  planContextFixture,
  underlyingContextFixture,
} from "./support/plan-context-fixtures";

const planId = "11111111-1111-4111-8111-111111111111";
const version1Id = "22222222-2222-4222-8222-222222222222";
const version2Id = "33333333-3333-4333-8333-333333333333";
const underlyingId = "99999999-9999-4999-8999-999999999999";
const candidateId = "44444444-4444-4444-8444-444444444444";
const evaluationId = "55555555-5555-4555-8555-555555555555";
const actorId = "00000000-0000-4000-8000-000000000002";
const now = "2026-08-11T17:00:00Z";
const tradePlanApiRoute = /\/api\/api\/v1\/trade-plans(?:\/.*)?(?:\?.*)?$/;
const underlying = underlyingContextFixture(
  underlyingId,
  "Synthetische Planaktie",
);

function version(overrides: Partial<TradePlanVersionResponse> = {}) {
  return planContextFixture(planId, version1Id, underlyingId, {
    status: "DRAFT",
    thesis: "Continuation thesis",
    approval: null,
    entry: {
      type: "PRICE",
      currency: "EUR",
      price: "100",
      price_from: null,
      price_to: null,
      trigger: null,
      reference_price: null,
      valid_until: null,
      rationale: null,
    },
    invalidation: {
      stop_price: "95",
      invalidation_rule: "Close below support",
      rationale: null,
    },
    targets: [{ sequence: 1, price: "110", rationale: "Prior high" }],
    risk_assumptions: {
      thesis_risk: "Breakout failure",
      max_loss_assumption: "5%",
      notes: "No position sizing",
    },
    ...overrides,
  }).latest_version;
}

const plan = planContextFixture(planId, version1Id, underlyingId).plan;

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockUnderlying(page: Page) {
  await page.route(
    /\/api\/api\/v1\/underlyings(?:\/.*)?(?:\?.*)?$/,
    async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith(`/${underlyingId}`))
        return json(route, underlying);
      expect(url.searchParams.get("q")).toBe("Planaktie");
      return json(route, {
        items: [underlying],
        total: 1,
        offset: 0,
        limit: 10,
      });
    },
  );
}

async function fillCommonPlan(page: Page) {
  await page.getByLabel("Trade Thesis").fill("Continuation thesis");
  await expect(page.getByLabel("Währung", { exact: true })).toHaveValue("");
  await page.getByLabel("Währung", { exact: true }).fill("EUR");
  await page.getByLabel("Technischer Stop").fill("95");
  await page
    .getByLabel("Invalidierungsregel", { exact: true })
    .fill("Close below support");
  await page.getByLabel("Target 1", { exact: true }).fill("110");
  await page.getByLabel("Target-Begründung 1").fill("Prior high");
  await page.getByLabel("Plan-Risiko / Annahme").fill("Breakout failure");
  await page.getByText("Weitere Risikoangaben", { exact: true }).click();
  await page.getByLabel("Max-Loss-Annahme (optional)").fill("5%");
  await page.getByLabel("Risk Notes").fill("No position sizing");
}

test("manual TradePlan flows from DRAFT through explicit approval with append-only audit", async ({
  page,
}) => {
  let current = version();
  let createRequests = 0;
  let submitReviewRequests = 0;
  let approveRequests = 0;
  await mockUnderlying(page);

  await page.route(tradePlanApiRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/trade-plans") && request.method() === "POST") {
      createRequests += 1;
      const body = request.postDataJSON();
      expect(body).toMatchObject({
        origin_type: "MANUAL",
        underlying_id: underlyingId,
        thesis: "Continuation thesis",
        entry: { type: "PRICE", currency: "EUR", price: "100" },
      });
      expect(body).not.toHaveProperty("candidate_id");
      expect(body).not.toHaveProperty("candidate_evaluation_id");
      expect(JSON.stringify(body)).not.toMatch(
        /warrant|issuer|leverage|order_quantity/i,
      );
      return json(route, { plan, latest_version: current }, 201);
    }
    if (
      path.endsWith(`/${planId}/versions/${version1Id}/submit-review`) &&
      request.method() === "POST"
    ) {
      submitReviewRequests += 1;
      current = {
        ...current,
        status: "READY_FOR_REVIEW",
        events: [
          {
            id: "66666666-6666-4666-8666-666666666661",
            event_type: "SUBMITTED_FOR_REVIEW",
            from_status: "DRAFT",
            to_status: "READY_FOR_REVIEW",
            reason: null,
            actor: actorId,
            correlation_id: request.headers()["x-correlation-id"] ?? null,
            occurred_at: now,
          },
        ],
      };
      return json(route, current);
    }
    if (
      path.endsWith(`/${planId}/versions/${version1Id}/approve`) &&
      request.method() === "POST"
    ) {
      approveRequests += 1;
      current = {
        ...current,
        status: "APPROVED",
        events: [
          ...current.events,
          {
            id: "66666666-6666-4666-8666-666666666662",
            event_type: "APPROVED",
            from_status: "READY_FOR_REVIEW",
            to_status: "APPROVED",
            reason: null,
            actor: actorId,
            correlation_id: request.headers()["x-correlation-id"] ?? null,
            occurred_at: now,
          },
        ],
        approval: {
          approval_id: "77777777-7777-4777-8777-777777777777",
          trade_plan_version_id: version1Id,
          version: 1,
          actor: actorId,
          approved_at: now,
          correlation_id: request.headers()["x-correlation-id"] ?? null,
        },
      };
      return json(route, current);
    }
    if (path.endsWith(`/${planId}/versions`) && request.method() === "GET")
      return json(route, [current]);
    if (
      path.endsWith(`/${planId}/versions/${version1Id}`) &&
      request.method() === "GET"
    )
      return json(route, current);
    if (path.endsWith(`/${planId}`) && request.method() === "GET")
      return json(route, { plan, latest_version: current });
    return json(
      route,
      { code: "E2E_ROUTE_MISSING", message: `${request.method()} ${path}` },
      500,
    );
  });

  await page.goto("/trade-plans");
  await page.getByLabel("Basiswert suchen").fill("Planaktie");
  await page.getByRole("button", { name: "Suchen", exact: true }).click();
  const choose = page.getByRole("button", { name: /Synthetische Planaktie/ });
  await choose.focus();
  await expect(choose).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Underlying-ID", { exact: true })).toHaveCount(
    0,
  );
  await fillCommonPlan(page);
  await page.getByLabel("Entry-Preis").fill("100");
  await page
    .getByRole("button", { name: "TradePlan als DRAFT erstellen" })
    .click();
  await expect(page).toHaveURL(
    new RegExp(`trade_plan_id=${planId}.*trade_plan_version_id=${version1Id}`),
  );
  await expect(
    page.getByRole("heading", { name: "Version 1 · DRAFT", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Trade Thesis")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "TradePlan als DRAFT erstellen" }),
  ).toHaveCount(0);
  expect(createRequests).toBe(1);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Version 1 · DRAFT", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Trade Thesis")).toHaveCount(0);

  await page.getByRole("button", { name: "Zur Prüfung einreichen" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Version 1 · READY_FOR_REVIEW",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Explizit freigeben" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Explizit freigeben" }).click();
  await expect(
    page.getByRole("heading", { name: "Version 1 · APPROVED", exact: true }),
  ).toBeVisible();
  expect(submitReviewRequests).toBe(1);
  expect(approveRequests).toBe(1);
  expect(current.events.map((event) => event.event_type)).toEqual([
    "SUBMITTED_FOR_REVIEW",
    "APPROVED",
  ]);
  await page
    .getByText("Herkunft und Lifecycle anzeigen", { exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Approval-Nachweis" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Produktauswahl starten" }),
  ).toHaveAttribute(
    "href",
    `/product-selection?trade_plan_id=${planId}&trade_plan_version_id=${version1Id}`,
  );
});

test("CandidateEvaluation origin preserves exact evaluation provenance and never sends underlying override", async ({
  page,
}) => {
  await mockUnderlying(page);
  const provenance = {
    candidate_id: candidateId,
    evaluation_id: evaluationId,
    evaluation_version: 7,
    direction: "LONG",
    model_id: "candidate-qualification",
    model_version: "1.0.0",
    qualification: "QUALIFIED",
    quality_status: "COMPLETE",
    evaluated_at: now,
    sources: [
      {
        role: "MARKET_CONTEXT",
        source_type: "MARKET_CONTEXT",
        source_id: "88888888-8888-4888-8888-888888888888",
        source_version: 3,
        model_id: "market-context",
        model_version: "1.0.0",
      },
    ],
  };
  const candidateVersion = version({
    entry: {
      ...version().entry,
      type: "TRIGGER",
      price: null,
      trigger: "Break above 101",
    },
    candidate_evaluation: provenance,
  });
  const candidatePlan = {
    ...plan,
    origin_type: "CANDIDATE_EVALUATION",
    candidate_id: candidateId,
    candidate_evaluation_id: evaluationId,
  };
  const evaluation = {
    ...provenance,
    id: evaluationId,
    version: 7,
    warnings: [],
    criteria: [],
  };
  await page.route(
    /\/api\/api\/v1\/candidates(?:\/.*)?(?:\?.*)?$/,
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith(`/${candidateId}/evaluations`)) {
        // A newer stored result exists, but must never replace the requested v7.
        return json(route, [
          {
            ...evaluation,
            id: "55555555-5555-4555-8555-555555555556",
            version: 8,
          },
          evaluation,
        ]);
      }
      return json(route, [
        {
          id: candidateId,
          underlying_id: underlyingId,
          status: "ACTIVE",
          created_at: now,
          created_by: actorId,
        },
      ]);
    },
  );
  let creates = 0;
  await page.route(tradePlanApiRoute, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/trade-plans") && request.method() === "POST") {
      creates += 1;
      const body = request.postDataJSON();
      expect(body.origin_type).toBe("CANDIDATE_EVALUATION");
      expect(body.candidate_id).toBe(candidateId);
      expect(body.candidate_evaluation_id).toBe(evaluationId);
      expect(body).not.toHaveProperty("underlying_id");
      return json(
        route,
        { plan: candidatePlan, latest_version: candidateVersion },
        201,
      );
    }
    if (path.endsWith(`/${planId}/versions`))
      return json(route, [candidateVersion]);
    if (path.endsWith(`/${planId}/versions/${version1Id}`))
      return json(route, candidateVersion);
    if (path.endsWith(`/${planId}`))
      return json(route, {
        plan: candidatePlan,
        latest_version: candidateVersion,
      });
    return json(
      route,
      { code: "E2E_ROUTE_MISSING", message: `${request.method()} ${path}` },
      500,
    );
  });

  await page.goto(
    `/trade-plans?candidate_id=${candidateId}&candidate_evaluation_id=${evaluationId}`,
  );
  await expect(page.getByText(/Synthetische Planaktie/).first()).toBeVisible();
  await expect(page.getByLabel("Candidate-ID", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("CandidateEvaluation-ID", { exact: true }),
  ).toHaveCount(0);
  await fillCommonPlan(page);
  await page.getByLabel("Entry-Art").selectOption("TRIGGER");
  await page
    .getByRole("textbox", { name: "Trigger", exact: true })
    .fill("Break above 101");
  await page
    .getByRole("button", { name: "TradePlan als DRAFT erstellen" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Version 1 · DRAFT", exact: true }),
  ).toBeVisible();
  expect(creates).toBe(1);
  expect(candidateVersion.candidate_evaluation?.evaluation_version).toBe(7);
  // The saved provenance is displayed on demand without editable identifiers.
  await page
    .getByText("Herkunft und Lifecycle anzeigen", { exact: true })
    .click();
  await expect(
    page.getByText("Kandidatenursprung · gespeicherte Evaluation v7."),
  ).toBeVisible();
  await page
    .getByText("Technische Provenance anzeigen", { exact: true })
    .click();
  await expect(page.getByText(/MARKET_CONTEXT/).first()).toBeVisible();
  await expect(page.getByText(new RegExp(evaluationId)).first()).toBeVisible();
});

for (const scenario of [
  { type: "PRICE" as const, width: 1280 },
  { type: "PRICE_RANGE" as const, width: 1280 },
  { type: "TRIGGER" as const, width: 1280 },
  { type: "TRIGGER" as const, width: 390 },
]) {
  test(`approved ${scenario.type} amendment preserves full content and explicit lineage at ${scenario.width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: scenario.width, height: 900 });
    await mockUnderlying(page);
    const precise = "100.12345678901234567890";
    const approvedV1 = version({
      status: "APPROVED",
      entry: {
        type: scenario.type,
        currency: "USD",
        price: scenario.type === "PRICE" ? precise : null,
        price_from:
          scenario.type === "PRICE_RANGE" ? "99.12345678901234567890" : null,
        price_to: scenario.type === "PRICE_RANGE" ? precise : null,
        trigger:
          scenario.type === "TRIGGER"
            ? "Break above the confirmed daily high"
            : null,
        reference_price: scenario.type === "TRIGGER" ? precise : null,
        valid_until: "2027-01-02T13:45:00+01:00",
        rationale: "Explicit entry reasoning",
      },
      invalidation: {
        stop_price: "95.12345678901234567890",
        invalidation_rule: "Confirmed close below support",
        rationale: "Original invalidation reasoning",
      },
      targets: [
        {
          sequence: 1,
          price: "110.12345678901234567890",
          rationale: "First target reasoning",
        },
        {
          sequence: 2,
          price: "120.12345678901234567890",
          rationale: "Second target reasoning",
        },
        {
          sequence: 3,
          price: "130.12345678901234567890",
          rationale: "Third target reasoning",
        },
      ],
      risk_assumptions: {
        thesis_risk: "Failed breakout risk",
        max_loss_assumption: "Explicit loss assumption",
        notes: "All original risk notes retained",
      },
      approval: {
        approval_id: "77777777-7777-4777-8777-777777777777",
        trade_plan_version_id: version1Id,
        version: 1,
        actor: actorId,
        approved_at: now,
        correlation_id: "corr-approve-v1",
      },
    });
    const original = structuredClone(approvedV1);
    const originalContent = {
      thesis: approvedV1.thesis,
      entry: approvedV1.entry,
      invalidation: approvedV1.invalidation,
      targets: approvedV1.targets,
      risk_assumptions: approvedV1.risk_assumptions,
    };
    let versions = [approvedV1];
    let latest = approvedV1;
    const writes: string[] = [];
    await page.route(tradePlanApiRoute, async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (request.method() !== "GET") writes.push(path);
      if (
        request.method() === "POST" &&
        path.endsWith(`/${version1Id}/amendments`)
      ) {
        const body = request.postDataJSON();
        expect(body).toEqual({
          ...originalContent,
          thesis: "Only the thesis has changed",
          change_reason: "Explicit thesis clarification",
        });
        latest = {
          ...approvedV1,
          ...body,
          id: version2Id,
          version: 2,
          status: "DRAFT",
          previous_version_id: version1Id,
          approval: null,
          events: [],
        };
        versions = [approvedV1, latest];
        return json(route, latest, 201);
      }
      if (request.method() === "GET" && path.endsWith(`/${planId}/versions`))
        return json(route, versions);
      if (request.method() === "GET" && path.endsWith(`/${planId}`))
        return json(route, { plan, latest_version: latest });
      const selected = versions.find((item) =>
        path.endsWith(`/${planId}/versions/${item.id}`),
      );
      if (request.method() === "GET" && selected) return json(route, selected);
      return json(
        route,
        { code: "E2E_ROUTE_MISSING", message: `${request.method()} ${path}` },
        500,
      );
    });
    await page.goto(
      `/trade-plans?trade_plan_id=${planId}&trade_plan_version_id=${version1Id}`,
    );
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
    await expect(page.getByLabel("Entry-Art")).toHaveValue(scenario.type);
    await expect(page.getByLabel("Währung", { exact: true })).toHaveValue(
      "USD",
    );
    for (const target of approvedV1.targets) {
      await expect(
        page.getByLabel(`Target ${target.sequence}`, { exact: true }),
      ).toHaveValue(target.price);
      await expect(
        page.getByLabel(`Target-Begründung ${target.sequence}`, {
          exact: true,
        }),
      ).toHaveValue(target.rationale!);
    }
    await page.getByText("Weitere Entry-Angaben", { exact: true }).click();
    await expect(
      page.getByLabel("Gültig bis (ISO 8601 mit Zeitzone)"),
    ).toHaveValue(approvedV1.entry.valid_until!);
    await expect(page.getByLabel("Entry-Begründung")).toHaveValue(
      approvedV1.entry.rationale!,
    );
    if (scenario.type === "TRIGGER")
      await expect(page.getByLabel("Referenzpreis")).toHaveValue(precise);
    await page.getByLabel("Trade Thesis").fill("Only the thesis has changed");
    await page
      .getByLabel("Änderungsgrund")
      .fill("Explicit thesis clarification");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await testInfo.attach(
      `Full ${scenario.type} amendment ${scenario.width}px (synthetic API)`,
      {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      },
    );
    const save = page.getByRole("button", {
      name: "Neue DRAFT-Version speichern",
    });
    await save.focus();
    await expect(save).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Version 2 · DRAFT", exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel("Trade Thesis")).toHaveCount(0);
    expect(writes).toEqual([
      `/api/api/v1/trade-plans/${planId}/versions/${version1Id}/amendments`,
    ]);
    expect(approvedV1).toEqual(original);
    expect(latest.previous_version_id).toBe(version1Id);
    await page
      .getByRole("combobox", { name: "Planversion", exact: true })
      .selectOption(version1Id);
    await expect(
      page.getByRole("heading", { name: "Version 1 · APPROVED", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Produktauswahl starten" }),
    ).toHaveAttribute(
      "href",
      `/product-selection?trade_plan_id=${planId}&trade_plan_version_id=${version1Id}`,
    );
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Version 1 · APPROVED", exact: true }),
    ).toBeVisible();
    expect(writes).toHaveLength(1);
  });
}
