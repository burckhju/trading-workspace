import { expect, test, type Page, type Route } from "@playwright/test";
import type {
  AnalysisRunDetail,
  SnapshotRow,
} from "../../frontend/src/features/analysis/types/api";
import type {
  Candidate,
  CandidateEvaluation,
} from "../../frontend/src/features/candidate/types/api";
import type {
  CreateCandidateTradePlanRequest,
  TradePlanDetailResponse,
} from "../../frontend/src/features/trade_plan/types/api";
import {
  planContextFixture,
  underlyingContextFixture,
} from "./support/plan-context-fixtures";

// All API requests, including commands, are fulfilled in this synthetic browser fixture.
// No provider, real backend or mutable trading data participates in these journeys.
const candidateId = "b1111111-1111-4111-8111-111111111111";
const evaluationId = "b2222222-2222-4222-8222-222222222222";
const newerEvaluationId = "b3333333-3333-4333-8333-333333333333";
const underlyingId = "b4444444-4444-4444-8444-444444444444";
const analysisId = "b5555555-5555-4555-8555-555555555555";
const listingId = "b6666666-6666-4666-8666-666666666666";
const planId = "b7777777-7777-4777-8777-777777777777";
const planVersionId = "b8888888-8888-4888-8888-888888888888";
const actorId = "b9999999-9999-4999-8999-999999999999";
const now = "2026-11-05T12:00:00Z";
const analysisVersion = 3;
const runPath = `/market-analyses/${analysisId}/runs/${analysisVersion}`;
const creationPath = `/trade-plans?candidate_id=${candidateId}&candidate_evaluation_id=${evaluationId}`;
const sourceHint = new RegExp(
  `Initialvorschlag aus Analyse ${analysisId}, Version ${analysisVersion}`,
);

const evaluation: CandidateEvaluation = {
  id: evaluationId,
  version: 7,
  direction: "LONG",
  model_id: "candidate-qualification",
  model_version: "1.0.0",
  qualification: "QUALIFIED",
  quality_status: "COMPLETE",
  warnings: [],
  evaluated_at: now,
  criteria: [],
  sources: [
    {
      role: "UNDERLYING",
      source_type: "ANALYSIS",
      source_id: analysisId,
      source_version: analysisVersion,
      model_id: "underlying-analysis",
      model_version: "1.0.0",
    },
  ],
};

const candidate: Candidate = {
  id: candidateId,
  underlying_id: underlyingId,
  status: "ACTIVE",
  created_at: now,
  created_by: actorId,
};

const run: AnalysisRunDetail = {
  analysis: {
    id: analysisId,
    underlying_id: underlyingId,
    listing_id: listingId,
    created_at: now,
    created_by: actorId,
  },
  run: {
    version: analysisVersion,
    status: "COMPLETED",
    quality_status: "COMPLETE",
    model_id: "underlying-analysis",
    model_version: "1.0.0",
    observation_count: 201,
    analysis_time: now,
    input_hash: "synthetic-historical-input",
  },
  parameters: {},
  metrics: {},
  notes: [],
  data_sources: [],
  criteria: [],
  // getRun deliberately omits the stored rows; only the paginated reader supplies them.
  snapshot: [],
};

function snapshot(lastCurrency: string): SnapshotRow[] {
  return Array.from({ length: 201 }, (_, index) => ({
    trading_date: new Date(Date.UTC(2025, 0, index + 1))
      .toISOString()
      .slice(0, 10),
    open: "99",
    high: "102",
    low: "98",
    close: "100",
    adjusted_close: "100",
    volume: "10000",
    currency: index === 200 ? lastCurrency : "USD",
    provider: "synthetic-stored-provider",
    provider_symbol: "HISTORICAL",
    quality_status: "COMPLETE",
    warnings: [],
  }));
}

function nullableString(
  value: string | number | null | undefined,
): string | null {
  return value === null || value === undefined ? null : String(value);
}

function savedPlan(
  body: CreateCandidateTradePlanRequest,
): TradePlanDetailResponse {
  const detail = planContextFixture(planId, planVersionId, underlyingId, {
    status: "DRAFT",
    thesis: body.thesis,
    entry: {
      type: body.entry.type,
      currency: body.entry.currency,
      price: nullableString(body.entry.price),
      price_from: nullableString(body.entry.price_from),
      price_to: nullableString(body.entry.price_to),
      trigger: body.entry.trigger ?? null,
      reference_price: nullableString(body.entry.reference_price),
      valid_until: body.entry.valid_until ?? null,
      rationale: body.entry.rationale ?? null,
    },
    invalidation: {
      stop_price: nullableString(body.invalidation.stop_price),
      invalidation_rule: body.invalidation.invalidation_rule ?? null,
      rationale: body.invalidation.rationale ?? null,
    },
    targets: body.targets.map((target) => ({
      sequence: target.sequence,
      price: String(target.price),
      rationale: target.rationale ?? null,
    })),
    risk_assumptions: {
      thesis_risk: body.risk_assumptions.thesis_risk,
      max_loss_assumption: body.risk_assumptions.max_loss_assumption ?? null,
      notes: body.risk_assumptions.notes ?? null,
    },
    candidate_evaluation: {
      candidate_id: candidateId,
      evaluation_id: evaluationId,
      evaluation_version: evaluation.version,
      direction: evaluation.direction,
      model_id: evaluation.model_id,
      model_version: evaluation.model_version,
      qualification: evaluation.qualification,
      quality_status: evaluation.quality_status,
      evaluated_at: evaluation.evaluated_at,
      sources: evaluation.sources ?? [],
    },
    approval: null,
    events: [],
  });
  detail.plan.origin_type = "CANDIDATE_EVALUATION";
  detail.plan.candidate_id = candidateId;
  detail.plan.candidate_evaluation_id = evaluationId;
  return detail;
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installFixture(page: Page, lastCurrency = "USD") {
  const rows = snapshot(lastCurrency);
  const underlying = underlyingContextFixture(
    underlyingId,
    "Synthetischer UX1-B-Basiswert",
  );
  // Current EUR listing differs from the historical listing and its stored USD rows.
  const sourceReads: string[] = [];
  const snapshotOffsets: number[] = [];
  const commands: Array<{ method: string; path: string }> = [];
  const creates: CreateCandidateTradePlanRequest[] = [];
  const unexpected: string[] = [];
  let stored: TradePlanDetailResponse | undefined;
  let releaseLastPage!: () => void;
  const lastPageGate = new Promise<void>((resolve) => {
    releaseLastPage = resolve;
  });

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const isApi = /\/api(?:\/|$)/.test(url.pathname);
    const isDataRequest = ["fetch", "xhr"].includes(request.resourceType());
    if (!isApi && !isDataRequest) return route.continue();
    const path = url.pathname.replace(/^.*\/api\/v1(?=\/|$)/, "");
    const method = request.method();
    if (method !== "GET") commands.push({ method, path });

    if (method === "GET") {
      if (path === "/candidates") return json(route, [candidate]);
      if (path === `/candidates/${candidateId}/evaluations`) {
        return json(route, [
          {
            ...evaluation,
            id: newerEvaluationId,
            version: 8,
            sources: evaluation.sources?.map((source) => ({
              ...source,
              source_version: 4,
            })),
          },
          evaluation,
        ]);
      }
      if (path === `/underlyings/${underlyingId}`)
        return json(route, underlying);
      if (path.startsWith("/market-analyses/"))
        sourceReads.push(path + url.search);
      if (path === runPath && url.search === "?include_snapshot=false")
        return json(route, run);
      if (path === `${runPath}/snapshot`) {
        const offset = Number(url.searchParams.get("offset"));
        const limit = Number(url.searchParams.get("limit"));
        if ((offset === 0 || offset === 200) && limit === 200) {
          snapshotOffsets.push(offset);
          if (offset === 200) await lastPageGate;
          return json(route, {
            items: rows.slice(offset, offset + limit),
            total: rows.length,
            offset,
            limit,
          });
        }
      }
      if (stored && path === `/trade-plans/${planId}`)
        return json(route, stored);
      if (stored && path === `/trade-plans/${planId}/versions`)
        return json(route, [stored.latest_version]);
      if (stored && path === `/trade-plans/${planId}/versions/${planVersionId}`)
        return json(route, stored.latest_version);
    }
    if (method === "POST" && path === "/trade-plans") {
      const body = request.postDataJSON() as CreateCandidateTradePlanRequest;
      creates.push(body);
      stored = savedPlan(body);
      return json(route, stored, 201);
    }
    unexpected.push(`${method} ${url.pathname}${url.search}`);
    return json(
      route,
      { detail: "Unconfigured synthetic request; no backend fallback." },
      503,
    );
  });

  return {
    sourceReads,
    snapshotOffsets,
    commands,
    creates,
    unexpected,
    releaseLastPage,
  };
}

type Fixture = Awaited<ReturnType<typeof installFixture>>;

async function finishSnapshotRead(page: Page, fixture: Fixture) {
  await expect.poll(() => fixture.snapshotOffsets).toEqual([0, 200]);
  const lastResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname.endsWith(`${runPath}/snapshot`) &&
      url.searchParams.get("offset") === "200"
    );
  });
  fixture.releaseLastPage();
  await (await lastResponse).finished();
  // Let the response promise and the ensuing React update settle across a paint boundary.
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

function expectOnlyHistoricalReads(fixture: Fixture) {
  expect(fixture.sourceReads).toEqual([
    `${runPath}?include_snapshot=false`,
    `${runPath}/snapshot?offset=0&limit=200`,
    `${runPath}/snapshot?offset=200&limit=200`,
  ]);
  expect(fixture.unexpected).toEqual([]);
}

async function fillPricesAndAssumptions(page: Page) {
  await page
    .getByLabel("Trade Thesis")
    .fill("Bewusst geplante historische Quelle");
  await page.getByLabel("Entry-Preis", { exact: true }).fill("100");
  await page.getByLabel("Technischer Stop").fill("95");
  await page.getByLabel("Target 1", { exact: true }).fill("110");
  await page
    .getByLabel("Plan-Risiko / Annahme")
    .fill("Bewusst angenommener Fehlausbruch");
}

async function saveVisibleCurrency(
  page: Page,
  fixture: Fixture,
  currency: string,
) {
  await expect(page.getByLabel("Währung", { exact: true })).toHaveValue(
    currency,
  );
  expect(fixture.commands).toEqual([]);
  await page
    .getByRole("button", { name: "TradePlan als DRAFT erstellen", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Version 1 · DRAFT", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(
    new RegExp(
      `trade_plan_id=${planId}&trade_plan_version_id=${planVersionId}$`,
    ),
  );
  expect(fixture.commands).toEqual([{ method: "POST", path: "/trade-plans" }]);
  expect(fixture.creates).toHaveLength(1);
  expect(fixture.creates[0]).toMatchObject({
    origin_type: "CANDIDATE_EVALUATION",
    candidate_id: candidateId,
    candidate_evaluation_id: evaluationId,
    entry: { currency, price: "100" },
  });
  expect(fixture.creates[0]).not.toHaveProperty("underlying_id");
  expect(fixture.creates[0]).not.toHaveProperty("currency_provenance");
  await expect(
    page
      .getByRole("region", { name: "Einstieg", exact: true })
      .getByText(currency, { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(sourceHint)).toHaveCount(0);
  await expect(page.getByLabel("Währung", { exact: true })).toHaveCount(0);
  expectOnlyHistoricalReads(fixture);
}

for (const width of [1280, 390]) {
  test(`UX1-B exact historical currency is editable and saves only the visible DRAFT value at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const fixture = await installFixture(page);
    await page.goto(creationPath);
    const currency = page.getByLabel("Währung", { exact: true });
    await expect(currency).toBeVisible();
    await expect.poll(() => fixture.snapshotOffsets).toEqual([0, 200]);
    // A complete first page is insufficient while the final stored row is still outstanding.
    await expect(currency).toHaveValue("");
    expect(fixture.commands).toEqual([]);
    await finishSnapshotRead(page, fixture);
    await expect(currency).toHaveValue("USD");
    await expect(currency).toBeEditable();
    await expect(currency).toHaveAccessibleDescription(sourceHint);
    await expect(page.getByText(sourceHint)).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Gebundener Planungsursprung" }),
    ).toContainText("CandidateEvaluation · Version 7");
    await expect(page).toHaveURL(
      new RegExp(`${creationPath.replace("?", "\\?")}$`),
    );
    expectOnlyHistoricalReads(fixture);
    expect(fixture.commands).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);

    await currency.fill("CHF");
    await expect(page.getByText(sourceHint)).toHaveCount(0);
    await currency.fill("USD");
    await expect(currency).not.toHaveAttribute("aria-describedby");
    await expect(page.getByText(sourceHint)).toHaveCount(0);
    await currency.fill("CHF");
    await fillPricesAndAssumptions(page);
    await saveVisibleCurrency(page, fixture, "CHF");
  });
}

test("UX1-B currency conflict on the last snapshot page preserves the manual creation path", async ({
  page,
}) => {
  const fixture = await installFixture(page, "EUR");
  await page.goto(creationPath);
  await expect(page.getByLabel("Währung", { exact: true })).toBeVisible();
  await finishSnapshotRead(page, fixture);
  await expect(page.getByLabel("Währung", { exact: true })).toHaveValue("");
  await expect(page.getByText(sourceHint)).toHaveCount(0);
  expectOnlyHistoricalReads(fixture);
  expect(fixture.commands).toEqual([]);
  await page.getByLabel("Währung", { exact: true }).fill("CHF");
  await fillPricesAndAssumptions(page);
  await saveVisibleCurrency(page, fixture, "CHF");
});

for (const edit of [
  { label: "Entry-Preis", value: "101", clear: false },
  { label: "Trade Thesis", value: "Eigener Entwurf", clear: true },
]) {
  test(`UX1-B delayed currency cannot relabel a draft after ${edit.label}${edit.clear ? " edit then clear" : " edit"}`, async ({
    page,
  }) => {
    const fixture = await installFixture(page);
    await page.goto(creationPath);
    await expect.poll(() => fixture.snapshotOffsets).toEqual([0, 200]);
    const field = page.getByLabel(edit.label, { exact: true });
    await field.fill(edit.value);
    if (edit.clear) await field.fill("");
    await finishSnapshotRead(page, fixture);
    await expect(field).toHaveValue(edit.clear ? "" : edit.value);
    await expect(page.getByLabel("Währung", { exact: true })).toHaveValue("");
    await expect(page.getByText(sourceHint)).toHaveCount(0);
    await expect(page).toHaveURL(
      new RegExp(`${creationPath.replace("?", "\\?")}$`),
    );
    expectOnlyHistoricalReads(fixture);
    expect(fixture.commands).toEqual([]);
  });
}
