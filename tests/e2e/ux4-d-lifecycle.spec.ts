import { expect, test, type Page } from "@playwright/test";
import type {
  EvidenceSource,
  JournalSources,
  PlanSource,
  ReviewSources,
  TradeSourceCore,
} from "../../frontend/src/features/trade/services/sourceView";
import {
  assertDocumentReflow,
  browserMeasurements,
  contrastSample,
  nativeScreenshot,
  nativeZoomBrowser,
} from "./support/ux4-native-zoom";

// Browser/HTTP integration with synthetic, intercepted owner payloads. No database/provider writes.
const tradeId = "10000000-0000-4000-8000-000000000001";
const reviewId = "20000000-0000-4000-8000-000000000001";
const journalId = "30000000-0000-4000-8000-000000000001";
const lessonId = "40000000-0000-4000-8000-000000000001";
const lessonVersion = "40000000-0000-4000-8000-000000000002";
const planId = "50000000-0000-4000-8000-000000000001";
const planVersion = "50000000-0000-4000-8000-000000000002";
const at = "2026-11-06T10:00:00Z";
const sourcePath = `/trade-management?trade_id=${tradeId}&view=sources&review_version_id=${reviewId}&journal_version_id=${journalId}`;

function plan(): PlanSource {
  const candidate = {
    candidate_id: "synthetic-candidate",
    evaluation_id: "synthetic-evaluation",
    evaluation_version: 3,
    direction: "LONG",
    model_id: "CANDIDATE_MODEL",
    model_version: "2.1",
    qualification: "QUALIFIED",
    quality_status: "VALID",
    evaluated_at: "2026-10-20T08:00:00Z",
    sources: [
      {
        role: "UNDERLYING",
        source_type: "MARKET_ANALYSIS",
        source_id: "historical-analysis-" + "a".repeat(80),
        source_version: 7,
        model_id: "ANALYSIS_MODEL",
        model_version: "1.0.1",
      },
    ],
  };
  return {
    plan: {
      id: planId,
      underlying_id: "synthetic-underlying",
      origin_type: "CANDIDATE_EVALUATION",
      candidate_id: candidate.candidate_id,
      candidate_evaluation_id: candidate.evaluation_id,
      created_at: at,
      created_by: "synthetic-actor",
    },
    version: {
      id: planVersion,
      trade_plan_id: planId,
      version: 2,
      direction: "LONG",
      thesis: "Historische synthetische Planthese",
      entry: {
        type: "PRICE",
        price: "100.00",
        currency: "EUR",
        price_from: null,
        price_to: null,
        trigger: null,
        reference_price: null,
        valid_until: null,
        rationale: null,
      },
      invalidation: {
        stop_price: "95.00",
        invalidation_rule: null,
        rationale: null,
      },
      targets: [],
      risk_assumptions: {
        thesis_risk: "Synthetische Risikoannahme",
        max_loss_assumption: null,
        notes: null,
      },
      status: "DRAFT",
      created_at: at,
      created_by: "synthetic-actor",
      previous_version_id: null,
      change_reason: null,
      candidate_evaluation: candidate,
      approval: null,
      events: [],
    },
    approval: null,
    candidate_evaluation: candidate,
    events: [],
  };
}

function core(): TradeSourceCore {
  const execution = {
    id: "synthetic-original-buy",
    trade_id: tradeId,
    kind: "EXECUTION" as const,
    execution_side: "BUY" as const,
    occurred_at: "2026-10-20T22:00:00Z",
    executed_on: "2026-10-21",
    execution_timezone: "Europe/Berlin",
    recorded_at: at,
    quantity: 10,
    price_per_unit: "0.00",
    numeric_value: null,
    text_value: null,
    management_event_type: null,
    supersedes_id: null,
    currency_resolution: {
      currency_code: null,
      source: "UNKNOWN" as const,
      source_execution_ids: [],
      confirmation_ids: [],
    },
  };
  return {
    trade: {
      id: tradeId,
      product_id: "synthetic-product",
      origin: "WORKSPACE_SELECTION",
      trade_plan_id: planId,
      trade_plan_version_id: planVersion,
      product_selection_id: "synthetic-selection",
      product_evaluation_id: "synthetic-product-evaluation",
      created_at: at,
    },
    product_name: "Synthetischer Lifecycle-Beleg",
    state: "UNKNOWN",
    open_quantity: null,
    currency_history: [],
    timeline: [
      execution,
      {
        ...execution,
        id: "synthetic-corrected-buy",
        price_per_unit: "1.234567890123456789",
        supersedes_id: execution.id,
      },
    ],
  };
}

function reviews(): ReviewSources {
  const selected = {
    version: {
      id: reviewId,
      exit_review_id: "synthetic-review-root",
      version: 1,
      status: "FINALIZED" as const,
      currentness: "CURRENT" as const,
      timing: "NOT_ASSESSABLE" as const,
      process_adherence: null,
      risk_decision: null,
      overall_exit_decision: null,
      rationale: "Synthetische historische Reflexion",
      created_at: at,
      created_by: "synthetic-actor",
      finalized_at: at,
      finalized_by: "synthetic-actor",
      supersedes_version_id: null,
      stale_at: null,
      stale_reason: null,
    },
  };
  return {
    selected,
    history: [selected],
    source_currentness: "STALE",
    checked_at: at,
  };
}

function journals(): JournalSources {
  const selected = {
    id: journalId,
    trade_journal_id: "synthetic-journal-root",
    version: 1,
    edit_revision: 3,
    status: "FINALIZED" as const,
    source_exit_review_version_id: reviewId,
    supersedes_version_id: null,
    what_went_well: null,
    would_do_differently: null,
    additional_notes: null,
    created_at: at,
    created_by: "synthetic-actor",
    updated_at: at,
    updated_by: "synthetic-actor",
    finalized_at: at,
    finalized_by: "synthetic-actor",
  };
  return {
    selected,
    history: [selected],
    source_currentness: "CURRENT",
    checked_at: at,
  };
}

function evidence(): EvidenceSource[] {
  return [
    {
      evidence_id: "synthetic-evidence",
      evidence_type: "TRADE_JOURNAL_VERSION",
      created_at: at,
      review_version_id: null,
      journal_version_id: journalId,
      source_bound: true,
      lesson_links: [
        {
          link_id: "synthetic-link",
          lesson_id: lessonId,
          lesson_title: "Synthetische Gegenbeobachtung",
          lesson_version_id: lessonVersion,
          lesson_version: 1,
          relation: "CONTRADICTS",
          is_current_version: false,
        },
      ],
    },
  ];
}

async function setup(
  page: Page,
  options: {
    failPlan?: boolean;
    holdPlan?: boolean;
    manual?: boolean;
    empty?: boolean;
  } = {},
) {
  const reads: string[] = [];
  const writes: string[] = [];
  const unexpected: string[] = [];
  const errors: string[] = [];
  let failPlan = options.failPlan ?? false;
  let releasePlan!: () => void;
  const planGate = new Promise<void>((resolve) => {
    releasePlan = resolve;
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== "GET") {
      writes.push(request.method() + " " + url.pathname);
      return route.fulfill({
        status: 405,
        json: { message: "No test writes allowed" },
      });
    }
    // CI's API base may already include /api; retain the existing client contract.
    const path = url.pathname.replace(/^\/api(?:\/api)?\/v1/, "/api/v1");
    reads.push(path + url.search);
    const base = `/api/v1/trade-position/trades/${tradeId}/sources`;
    const section =
      path === base
        ? "core"
        : path.startsWith(base + "/")
          ? path.slice(base.length + 1)
          : "";
    if (!["core", "plan", "reviews", "journal", "evidence"].includes(section)) {
      unexpected.push(url.pathname);
      return route.fulfill({
        status: 404,
        json: { message: "Unexpected synthetic API path" },
      });
    }
    if (section === "plan") {
      if (options.holdPlan) await planGate;
      if (failPlan)
        return route.fulfill({
          status: 503,
          json: { message: "Synthetischer Planreadfehler" },
        });
    }
    const planValue = plan();
    if (options.manual) {
      planValue.plan.origin_type = "MANUAL";
      planValue.plan.candidate_id = null;
      planValue.plan.candidate_evaluation_id = null;
      planValue.candidate_evaluation = null;
      planValue.version.candidate_evaluation = null;
    }
    const coreValue = core();
    const evidenceValue = evidence();
    if (options.empty) {
      coreValue.trade.origin = "EXTERNAL";
      coreValue.trade.trade_plan_id = null;
      coreValue.trade.trade_plan_version_id = null;
      coreValue.trade.product_selection_id = null;
      coreValue.trade.product_evaluation_id = null;
      evidenceValue[0].evidence_type = "FT011";
      evidenceValue[0].source_bound = false;
      evidenceValue[0].review_version_id = null;
      evidenceValue[0].journal_version_id = null;
    }
    const values: Record<string, unknown> = {
      core: coreValue,
      plan: options.empty ? null : planValue,
      reviews: options.empty
        ? {
            history: [],
            selected: null,
            source_currentness: "UNKNOWN",
            checked_at: at,
          }
        : reviews(),
      journal: options.empty
        ? {
            history: [],
            selected: null,
            source_currentness: "UNKNOWN",
            checked_at: at,
          }
        : journals(),
      evidence: evidenceValue,
    };
    const minute = {
      core: "00",
      plan: "01",
      reviews: "02",
      journal: "03",
      evidence: "04",
    }[section];
    return route.fulfill({
      json: {
        data: values[section],
        read_started_at: `2026-11-06T10:${minute}:00Z`,
        read_completed_at: `2026-11-06T10:${minute}:01Z`,
      },
    });
  });
  return {
    reads,
    writes,
    unexpected,
    errors,
    releasePlan,
    recoverPlan: () => {
      failPlan = false;
    },
  };
}

async function expectSources(page: Page) {
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    `Trade und Quellenstand · TR-${tradeId.slice(0, 8).toUpperCase()}`,
  );
  const list = page.getByRole("list", {
    name: "Belege im Trade-Lebenszyklus",
    exact: true,
  });
  await expect(list.locator(":scope > li")).toHaveCount(6);
  await expect(
    page.getByText(
      "Synthetische Gegenbeobachtung · Version 1 · CONTRADICTS · historische Version",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Analyse / Kandidat", exact: true }),
  ).toContainText("Version 7");
  await expect(
    page.getByRole("region", { name: "Ursprünglicher Plan", exact: true }),
  ).toContainText("Gespeicherte Freigabe: Nicht dokumentiert");
  await expect(
    page.getByRole("region", { name: "Ursprünglicher Plan", exact: true }),
  ).toContainText(
    "Eigenes Lesefenster der Planquelle, gemeinsam für Analyse und Plan:",
  );
  await expect(
    page.getByRole("region", { name: "Position", exact: true }),
  ).toContainText("UNKNOWN");
  await expect(
    page.getByRole("region", { name: "Position", exact: true }),
  ).toContainText("Nicht verfügbar");
  await expect(
    page.getByRole("region", { name: "Position", exact: true }),
  ).not.toContainText("0 Stück");
  await expect(
    page.getByRole("article", {
      name: "Quelle synthetic-original-buy",
      exact: true,
    }),
  ).toContainText("Historisch ersetzt");
  await expect(
    page.getByRole("article", {
      name: "Quelle synthetic-corrected-buy",
      exact: true,
    }),
  ).toContainText("2026-10-21 · Uhrzeit unbekannt · Europe/Berlin");
  await expect(
    page.getByRole("article", {
      name: "Quelle synthetic-corrected-buy",
      exact: true,
    }),
  ).toContainText("1.234567890123456789");
  await expect(
    page.getByRole("region", {
      name: "Dokumentierte Exit-Bewertung",
      exact: true,
    }),
  ).toContainText("Heutige Quellenprüfung: STALE");
  await expect(
    page.getByRole("region", { name: "Journal", exact: true }),
  ).toContainText("Finales Journal ohne Reflexionstext.");
  await expect(list.getByRole("progressbar")).toHaveCount(0);
  await expect(list).not.toContainText("6/6");
  return list;
}

async function inspectWithoutReading(page: Page) {
  const planRegion = page.getByRole("region", {
    name: "Ursprünglicher Plan",
    exact: true,
  });
  const summary = planRegion.getByText("Herkunftsdetails", { exact: true });
  await summary.focus();
  await expect(summary).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    planRegion.getByText(new RegExp("Plan: " + planId)),
  ).toBeVisible();
  expect(
    await summary.evaluate((element) => ({
      style: getComputedStyle(element).outlineStyle,
      width: getComputedStyle(element).outlineWidth,
    })),
  ).toEqual({ style: "solid", width: "2px" });
  const contrast = await contrastSample(summary);
  expect(contrast.textRatio).toBeGreaterThanOrEqual(4.5);
  expect(contrast.focusRatio).toBeGreaterThanOrEqual(3);
  await page.keyboard.press("Tab");
  await expect(summary).not.toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(summary).toBeFocused();
  await page.keyboard.press("Space");
  await expect(
    planRegion.getByText(new RegExp("Plan: " + planId)),
  ).toBeHidden();
  const planLink = planRegion.getByRole("link", {
    name: "Gebundene Planversion öffnen",
  });
  const target = new URL(
    (await planLink.getAttribute("href"))!,
    "http://localhost",
  );
  expect(target.searchParams.get("trade_plan_id")).toBe(planId);
  expect(target.searchParams.get("trade_plan_version_id")).toBe(planVersion);
  expect(target.searchParams.get("review_version_id")).toBe(reviewId);
  expect(target.searchParams.get("journal_version_id")).toBe(journalId);
  const lessonLink = page.getByRole("link", {
    name: /Synthetische Gegenbeobachtung · Version 1/,
  });
  const lessonTarget = new URL(
    (await lessonLink.getAttribute("href"))!,
    "http://localhost",
  );
  expect(lessonTarget.searchParams.get("lesson_version_id")).toBe(
    lessonVersion,
  );
  expect(lessonTarget.searchParams.get("review_version_id")).toBe(reviewId);
  expect(lessonTarget.searchParams.get("journal_version_id")).toBe(journalId);
  await page
    .getByRole("link", { name: "Plan und Quellen", exact: true })
    .click();
  await expect(planRegion).toBeFocused();
  return contrast;
}

for (const width of [320, 390, 1280]) {
  test(`UX4-D lifecycle keeps exact independent evidence and keyboard access at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    const requests = await setup(page);
    await page.goto(sourcePath);
    const list = await expectSources(page);
    await expect.poll(() => requests.reads.length).toBe(5);
    const originalReads = [...requests.reads];
    const contrast = await inspectWithoutReading(page);
    await assertDocumentReflow(page);
    expect(requests.reads).toEqual(originalReads);
    expect(requests.writes).toEqual([]);
    expect(requests.unexpected).toEqual([]);
    expect(requests.errors).toEqual([]);
    await testInfo.attach(`ux4-d-lifecycle-${width}.png`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await testInfo.attach(`ux4-d-lifecycle-${width}.aria.yml`, {
      body: await list.ariaSnapshot(),
      contentType: "text/plain",
    });
    await testInfo.attach(`ux4-d-lifecycle-${width}.json`, {
      body: JSON.stringify({
        ...(await browserMeasurements(page)),
        contrast,
        reads: requests.reads,
        writes: requests.writes,
      }),
      contentType: "application/json",
    });
  });
}

test("UX4-D later evidence does not complete a loading, failed, missing or manual earlier source", async ({
  page,
}) => {
  const requests = await setup(page, {
    holdPlan: true,
    failPlan: true,
    manual: true,
  });
  await page.goto(sourcePath);
  await expect(
    page.getByText(/Synthetische Gegenbeobachtung · Version 1/),
  ).toBeVisible();
  const analysis = page.getByRole("region", {
    name: "Analyse / Kandidat",
    exact: true,
  });
  const planRegion = page.getByRole("region", {
    name: "Ursprünglicher Plan",
    exact: true,
  });
  await expect(analysis).toContainText(
    "Analyseherkunft wird gemeinsam mit der Planquelle gelesen.",
  );
  await expect(planRegion.getByRole("status")).toContainText("wird gelesen");
  requests.releasePlan();
  await expect(planRegion.getByRole("alert")).toContainText(
    "Das bedeutet nicht, dass sie fehlt.",
  );
  await expect(analysis).toContainText(
    "Analyseherkunft konnte nicht geprüft werden.",
  );
  const originalReads = [...requests.reads];
  requests.recoverPlan();
  const retry = planRegion.getByRole("button", {
    name: "Ursprünglicher Plan neu lesen",
  });
  await retry.focus();
  await page.keyboard.press("Enter");
  await expect(analysis).toContainText(
    "Manueller Plan ohne gebundene Kandidatenbewertung.",
  );
  expect(requests.reads.slice(originalReads.length)).toEqual([
    `/api/v1/trade-position/trades/${tradeId}/sources/plan`,
  ]);
  expect(requests.writes).toEqual([]);
  expect(requests.errors).toEqual([]);
});

test("UX4-D confirmed missing plan and journal remain missing beside historical evidence", async ({
  page,
}) => {
  const requests = await setup(page, { empty: true });
  await page.goto(`/trade-management?trade_id=${tradeId}&view=sources`);
  await expect(
    page.getByText(/Synthetische Gegenbeobachtung · Version 1/),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Analyse / Kandidat", exact: true }),
  ).toContainText("Keine Analyse-/Kandidatenquelle");
  await expect(
    page.getByRole("region", { name: "Ursprünglicher Plan", exact: true }),
  ).toContainText("ohne dokumentierte ursprüngliche Planherkunft");
  await expect(
    page.getByRole("region", { name: "Journal", exact: true }),
  ).toContainText("Journal nicht dokumentiert.");
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(requests.reads).toHaveLength(5);
  expect(requests.writes).toEqual([]);
  expect(requests.errors).toEqual([]);
});

test("UX4-D lifecycle supports measured native 200 and 400 percent zoom", async ({
  baseURL,
}, testInfo) => {
  const { context, page, setZoom } = await nativeZoomBrowser(testInfo);
  try {
    const requests = await setup(page);
    await page.goto((baseURL ?? "http://127.0.0.1:8080") + sourcePath);
    const list = await expectSources(page);
    await expect.poll(() => requests.reads.length).toBe(5);
    const originalReads = [...requests.reads];
    const measurements: unknown[] = [];
    for (const factor of [2, 4]) {
      const measured = await setZoom(factor);
      const contrast = await inspectWithoutReading(page);
      await assertDocumentReflow(page);
      const position = page.getByRole("region", {
        name: "Position",
        exact: true,
      });
      await position.evaluate((element) =>
        element.scrollIntoView({ block: "center" }),
      );
      await nativeScreenshot(
        context,
        page,
        testInfo,
        `ux4-d-lifecycle-native-${factor * 100}.png`,
      );
      const summary = page
        .getByRole("region", { name: "Ursprünglicher Plan", exact: true })
        .getByText("Herkunftsdetails", { exact: true });
      await summary.focus();
      await page.keyboard.press("Tab");
      await page.keyboard.press("Shift+Tab");
      await expect(summary).toBeFocused();
      await summary.evaluate((element) =>
        element.scrollIntoView({ block: "center", inline: "nearest" }),
      );
      await expect(summary).toBeInViewport({ ratio: 1 });
      const focus = await summary.evaluate((element) => {
        const rectangle = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return {
          visible: element.matches(":focus-visible"),
          outlineStyle: style.outlineStyle,
          outlineWidth: style.outlineWidth,
          bounds: {
            x: rectangle.x,
            y: rectangle.y,
            width: rectangle.width,
            height: rectangle.height,
          },
        };
      });
      expect(focus).toMatchObject({
        visible: true,
        outlineStyle: "solid",
        outlineWidth: "2px",
      });
      await nativeScreenshot(
        context,
        page,
        testInfo,
        `ux4-d-lifecycle-native-${factor * 100}-focus.png`,
      );
      measurements.push({
        ...measured,
        ...(await browserMeasurements(page)),
        contrast,
        focus,
      });
      expect(requests.reads).toEqual(originalReads);
    }
    expect(requests.writes).toEqual([]);
    expect(requests.unexpected).toEqual([]);
    expect(requests.errors).toEqual([]);
    await testInfo.attach("ux4-d-lifecycle-native-zoom.json", {
      body: JSON.stringify(measurements, null, 2),
      contentType: "application/json",
    });
    await testInfo.attach("ux4-d-lifecycle-native.aria.yml", {
      body: await list.ariaSnapshot(),
      contentType: "text/plain",
    });
  } finally {
    await context.close();
  }
});
