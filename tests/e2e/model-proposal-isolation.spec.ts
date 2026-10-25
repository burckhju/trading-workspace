import {
  expect,
  test,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";

import type {
  CreateModelChangeProposalInput,
  GovernedModelVersion,
  ModelChangeProposalSummary,
} from "../../frontend/src/features/model/types/hypothesisProposal";

// Synthetic browser/HTTP evidence through the existing Lesson route. This is
// deliberately separate from the native PostgreSQL governance contract tests.
const at = "2026-10-24T10:00:00Z";
const actor = "00000000-0000-4000-8000-000000000001";
const lessons = [
  "10000000-0000-4000-8000-000000000001",
  "10000000-0000-4000-8000-000000000002",
];
const lessonVersions = [
  "20000000-0000-4000-8000-000000000001",
  "20000000-0000-4000-8000-000000000002",
];
const hypotheses = [
  "30000000-0000-4000-8000-000000000001",
  "30000000-0000-4000-8000-000000000002",
];
const models = [
  "40000000-0000-4000-8000-000000000001",
  "40000000-0000-4000-8000-000000000002",
  "40000000-0000-4000-8000-000000000003",
];
const bases = [
  "50000000-0000-4000-8000-000000000001",
  "50000000-0000-4000-8000-000000000002",
  "50000000-0000-4000-8000-000000000003",
];
const proposalIds = [
  "60000000-0000-4000-8000-000000000001",
  "60000000-0000-4000-8000-000000000002",
];
const saveLabel = "ModelChangeProposal als DRAFT anlegen";
const candidateV1 = {
  schema: "TOP_DOWN_CANDIDATE/1.0",
  direction: "LONG",
  market_context_allowed: ["FAVORABLE", "CAUTIOUS"],
};
const candidateV2 = {
  schema: "TOP_DOWN_CANDIDATE/2.0",
  direction: "LONG",
  market_context_allowed: ["FAVORABLE"],
};

const version = (index: number): GovernedModelVersion => ({
  id: bases[index],
  model_id: models[index],
  version: index + 1,
  status: "APPROVED",
  definition:
    index === 2 ? candidateV1 : { synthetic_rule: `model-${index + 1}` },
  change_summary: "Synthetic immutable approved base",
  created_at: at,
  created_by: actor,
  previous_version_id: null,
});

type Write = {
  method: string;
  path: string;
  body: CreateModelChangeProposalInput;
  idempotencyKey: string | null;
};
type SaveOutcome = "success" | "error" | "disconnect";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function renderedFrame(page: Page) {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
      }),
  );
}

async function installApi(
  page: Page,
  baseURL: string | undefined,
  holdModel?: string,
) {
  if (!baseURL)
    throw new Error("The test frontend baseURL must be configured.");
  const frontendOrigin = new URL(baseURL).origin;
  // Match the existing CI/Compose build value. A custom static build supplies
  // its exact VITE_API_BASE_URL rather than relaxing the observed API contract.
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? new URL(baseURL).port;
  const buildApiBaseUrl =
    process.env.E2E_VITE_API_BASE_URL ??
    process.env.VITE_API_BASE_URL ??
    `http://localhost:${frontendPort || "8080"}/api`;
  const apiBase = new URL(buildApiBaseUrl);
  const apiPrefix = `${apiBase.pathname.replace(/\/$/, "")}/api/v1`;
  const governance = `${apiPrefix}/model-governance`;
  const writes: Write[] = [];
  const reads: string[] = [];
  const observations: Array<{
    method: string;
    url: string;
    prefix: string | null;
  }> = [];
  const unexpected: string[] = [];
  const saved = new Map<string, ModelChangeProposalSummary>();
  const heldVersions: Route[] = [];
  const heldSaves = new Map<string, Route[]>();
  let holdVersions = holdModel !== undefined;

  async function unexpectedRequest(route: Route) {
    const description = `${route.request().method()} ${route.request().url()}`;
    unexpected.push(description);
    return json(
      route,
      {
        code: "E2E_UNEXPECTED_REQUEST",
        message: description,
        details: [],
        timestamp: at,
      },
      500,
    );
  }

  // Only documents and static assets reach the local frontend. Every API,
  // fetch/XHR, mutation and external request is intercepted, including errors.
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
    )
      return route.continue();

    const observedPrefix =
      url.pathname.match(/^(.*\/api\/v1)(?:\/|$)/)?.[1] ?? null;
    observations.push({ method, url: url.toString(), prefix: observedPrefix });
    if (method !== "GET")
      writes.push({
        method,
        path: url.pathname,
        body: request.postDataJSON(),
        idempotencyKey: request.headers()["idempotency-key"] ?? null,
      });
    if (
      url.origin !== apiBase.origin ||
      observedPrefix !== apiPrefix ||
      url.search
    )
      return unexpectedRequest(route);

    if (method === "GET") {
      reads.push(url.pathname);
      const lessonIndex = lessons.findIndex(
        (id) => url.pathname === `${apiPrefix}/learning/lessons/${id}`,
      );
      if (lessonIndex >= 0)
        return json(route, {
          lesson_id: lessons[lessonIndex],
          current_version_id: lessonVersions[lessonIndex],
          current_state: "CURRENT",
          version: 1,
          title: `Synthetic Lesson ${lessonIndex + 1}`,
          main_category: "Process",
          content: "Synthetic interpretation, not a trading recommendation.",
          evidence: [],
          created_at: at,
          created_by: actor,
        });
      const reviewIndex = lessons.findIndex(
        (id) =>
          url.pathname === `${apiPrefix}/learning/lessons/${id}/review-context`,
      );
      if (reviewIndex >= 0)
        return json(route, {
          lesson: {
            id: lessons[reviewIndex],
            title: `Synthetic Lesson ${reviewIndex + 1}`,
            current_version_id: lessonVersions[reviewIndex],
            current_state: "CURRENT",
          },
          history: [
            {
              version: {
                id: lessonVersions[reviewIndex],
                lesson_id: lessons[reviewIndex],
                version: 1,
                main_category: "Process",
                content: "Synthetic interpretation.",
                created_at: at,
                created_by: actor,
                supersedes_version_id: null,
              },
              evidence_links: [],
            },
          ],
          signals: [],
          transitions: [],
          read_at: at,
        });
      const hypothesisIndex = lessonVersions.findIndex(
        (id) =>
          url.pathname === `${governance}/lesson-versions/${id}/hypotheses`,
      );
      if (hypothesisIndex >= 0)
        return json(route, [
          {
            id: hypotheses[hypothesisIndex],
            title: `Synthetic Hypothesis ${hypothesisIndex + 1}`,
            statement: "A deliberately separate hypothesis context.",
            status: "OPEN",
            source_lesson_version_id: lessonVersions[hypothesisIndex],
            created_at: at,
            created_by: actor,
          },
        ]);
      const proposalHypothesis = hypotheses.find(
        (id) => url.pathname === `${governance}/hypotheses/${id}/proposals`,
      );
      if (proposalHypothesis)
        return json(
          route,
          saved.has(proposalHypothesis) ? [saved.get(proposalHypothesis)] : [],
        );
      if (url.pathname === `${governance}/models`)
        return json(
          route,
          models.map((id, index) => ({
            id,
            model_key: [
              "SYNTHETIC_ALPHA",
              "SYNTHETIC_BETA",
              "TOP_DOWN_CANDIDATE",
            ][index],
            name: `Synthetic Model ${index + 1}`,
            purpose: "UI isolation fixture",
            created_at: at,
            created_by: actor,
          })),
        );
      const modelIndex = models.findIndex(
        (id) => url.pathname === `${governance}/models/${id}/versions`,
      );
      if (modelIndex >= 0) {
        if (holdVersions && models[modelIndex] === holdModel) {
          heldVersions.push(route);
          return;
        }
        return json(route, [version(modelIndex)]);
      }
      if (
        proposalIds.some(
          (id) => url.pathname === `${governance}/proposals/${id}/validations`,
        )
      )
        return json(route, []);
      return unexpectedRequest(route);
    }

    if (method !== "POST" || url.pathname !== `${governance}/proposals`)
      return unexpectedRequest(route);
    const input = request.postDataJSON() as CreateModelChangeProposalInput;
    if (!hypotheses.includes(input.hypothesis_id))
      return unexpectedRequest(route);
    heldSaves.set(input.hypothesis_id, [
      ...(heldSaves.get(input.hypothesis_id) ?? []),
      route,
    ]);
  });

  const fixture = {
    writes,
    reads,
    governance,
    hasHeldVersion: () => heldVersions.length > 0,
    releaseVersions: async () => {
      if (!heldVersions.length)
        throw new Error("Expected a held version request.");
      holdVersions = false;
      for (const route of heldVersions.splice(0)) {
        const response = page.waitForResponse(
          (value) => value.request() === route.request(),
        );
        await json(route, [version(models.indexOf(holdModel!))]);
        await (await response).finished();
      }
      await renderedFrame(page);
    },
    releaseSave: async (
      hypothesisId: string,
      outcome: SaveOutcome = "success",
    ) => {
      const routes = heldSaves.get(hypothesisId);
      if (!routes?.length)
        throw new Error(`Expected a held save for ${hypothesisId}.`);
      heldSaves.delete(hypothesisId);
      for (const route of routes) {
        const input = route
          .request()
          .postDataJSON() as CreateModelChangeProposalInput;
        const created: ModelChangeProposalSummary = {
          ...input,
          id: proposalIds[hypotheses.indexOf(hypothesisId)],
          status: "DRAFT",
          created_at: at,
          created_by: actor,
        };
        if (outcome !== "error") saved.set(hypothesisId, created);
        if (outcome === "disconnect") {
          const failed = page.waitForEvent(
            "requestfailed",
            (value) => value === route.request(),
          );
          await route.abort("failed");
          await failed;
        } else {
          const response = page.waitForResponse(
            (value) => value.request() === route.request(),
          );
          await json(
            route,
            outcome === "success"
              ? created
              : {
                  code: "SYNTHETIC_SAVE_FAILED",
                  message: "Synthetic proposal save failed.",
                  details: [],
                  timestamp: at,
                },
            outcome === "success" ? 201 : 503,
          );
          await (await response).finished();
        }
      }
      await renderedFrame(page);
    },
    assertContract: async (info: TestInfo) => {
      await info.attach("model-proposal-api-contract", {
        body: Buffer.from(
          JSON.stringify(
            {
              buildApiBaseUrl,
              apiPrefix,
              observations,
              writes,
              unexpected,
            },
            null,
            2,
          ),
        ),
        contentType: "application/json",
      });
      expect(unexpected).toEqual([]);
      expect([...new Set(observations.map((value) => value.prefix))]).toEqual([
        apiPrefix,
      ]);
      if (info.status === info.expectedStatus) {
        expect(heldVersions).toHaveLength(0);
        expect([...heldSaves.keys()]).toEqual([]);
      }
    },
  };
  apis.set(page, fixture);
  return fixture;
}

const apis = new WeakMap<
  Page,
  { assertContract: (info: TestInfo) => Promise<void> }
>();
test.afterEach(async ({ page }, info) => {
  await apis.get(page)?.assertContract(info);
});

const proposalForm = (page: Page) =>
  page
    .locator("form")
    .filter({
      has: page.getByRole("textbox", { name: "Rationale", exact: true }),
    });
async function dispatchSubmits(page: Page, count = 1) {
  await proposalForm(page).evaluate((form, times) => {
    // Synchronous events in one browser task, independent of disabled buttons.
    for (let index = 0; index < times; ++index)
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
  }, count);
  await renderedFrame(page);
}
async function selectModel(page: Page, index: number, rationale: string) {
  await page
    .getByRole("combobox", { name: "Governed Model", exact: true })
    .selectOption(models[index]);
  await expect(
    page.getByRole("combobox", { name: "APPROVED Base-Version", exact: true }),
  ).toHaveValue(bases[index]);
  await page
    .getByRole("textbox", { name: "Rationale", exact: true })
    .fill(rationale);
}
const expectedWrite = (
  governance: string,
  hypothesisIndex: number,
  modelIndex: number,
  rationale: string,
  definition = version(modelIndex).definition,
): Write => ({
  method: "POST",
  path: `${governance}/proposals`,
  idempotencyKey: null,
  body: {
    hypothesis_id: hypotheses[hypothesisIndex],
    model_id: models[modelIndex],
    base_model_version_id: bases[modelIndex],
    proposed_definition: definition,
    rationale,
  },
});

// The real route keys LessonDetail and the parent keys hypothesis articles.
// Drive that existing React Router transition without a document reload or a
// synthetic production route; old server work remains independently observable.
async function changeLesson(page: Page, index: number) {
  await page.evaluate((path) => {
    history.pushState(null, "", path);
    dispatchEvent(new PopStateEvent("popstate"));
  }, `/lessons/${lessons[index]}`);
  await expect(
    page.getByRole("heading", {
      name: `Synthetic Hypothesis ${index + 1}`,
      exact: true,
    }),
  ).toBeVisible();
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    test("cannot submit a new model with the previous base while versions are pending", async ({
      page,
      baseURL,
    }, info) => {
      const api = await installApi(page, baseURL, models[1]);
      await page.goto(`/lessons/${lessons[0]}`);
      await selectModel(page, 0, "Rationale belonging to Model 1.");
      await page
        .getByRole("combobox", { name: "Governed Model", exact: true })
        .selectOption(models[1]);
      await expect.poll(api.hasHeldVersion).toBe(true);
      await dispatchSubmits(page);
      expect(api.writes).toEqual([]);
      await expect(
        page.getByRole("button", { name: saveLabel, exact: true }),
      ).toBeDisabled();
      await expect(
        page.getByRole("combobox", {
          name: "APPROVED Base-Version",
          exact: true,
        }),
      ).toHaveValue("");
      await expect(
        page.getByText(new RegExp(`Ausgangspunkt:.*${bases[0]}`)),
      ).toHaveCount(0);
      await api.releaseVersions();
      await expect(
        page.getByRole("combobox", {
          name: "APPROVED Base-Version",
          exact: true,
        }),
      ).toHaveValue(bases[1]);
      await expect(
        page.getByRole("textbox", { name: "Rationale", exact: true }),
      ).toHaveValue("");
      await page
        .getByRole("textbox", { name: "Rationale", exact: true })
        .fill("Explicit rationale for Model 2.");
      await page.getByRole("button", { name: saveLabel, exact: true }).click();
      await expect
        .poll(() => api.writes)
        .toEqual([
          expectedWrite(
            api.governance,
            0,
            1,
            "Explicit rationale for Model 2.",
          ),
        ]);
      await api.releaseSave(hypotheses[0]);
      await expect(
        page.getByText("Status: DRAFT", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", {
          name: "Retrospektive Validation erfassen",
        }),
      ).toBeVisible();
      expect(api.writes).toEqual([
        expectedWrite(api.governance, 0, 1, "Explicit rationale for Model 2."),
      ]);
      await info.attach(`${viewport.name}-proposal-draft`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      });
    });
  });
}

test("synchronous duplicate submits create once and a confirmed failure permits only an explicit retry", async ({
  page,
  baseURL,
}) => {
  const api = await installApi(page, baseURL);
  await page.goto(`/lessons/${lessons[0]}`);
  const rationale = "Preserve this rationale after a confirmed failure.";
  await selectModel(page, 0, rationale);
  await dispatchSubmits(page, 2);
  await expect
    .poll(() => api.writes)
    .toEqual([expectedWrite(api.governance, 0, 0, rationale)]);
  await api.releaseSave(hypotheses[0], "error");
  await expect(page.getByRole("alert")).toHaveText(
    "Synthetic proposal save failed.",
  );
  await expect(
    page.getByRole("textbox", { name: "Rationale", exact: true }),
  ).toHaveValue(rationale);
  await expect(
    page.getByRole("button", { name: saveLabel, exact: true }),
  ).toBeEnabled();
  expect(api.writes).toHaveLength(1);
  await page.getByRole("button", { name: saveLabel, exact: true }).click();
  await expect
    .poll(() => api.writes)
    .toEqual([
      expectedWrite(api.governance, 0, 0, rationale),
      expectedWrite(api.governance, 0, 0, rationale),
    ]);
  await api.releaseSave(hypotheses[0]);
  await expect(page.getByText("Status: DRAFT", { exact: true })).toBeVisible();
});

for (const outcome of ["success", "error"] as const) {
  test(`a late ${outcome} after a real Lesson route change cannot alter or unlock the new save`, async ({
    page,
    baseURL,
  }) => {
    const api = await installApi(page, baseURL);
    await page.goto(`/lessons/${lessons[0]}`);
    await selectModel(page, 0, "Hypothesis 1 snapshot.");
    await page.getByRole("button", { name: saveLabel, exact: true }).click();
    await expect.poll(() => api.writes).toHaveLength(1);
    await changeLesson(page, 1);
    await selectModel(page, 1, "Hypothesis 2 snapshot.");
    await page.getByRole("button", { name: saveLabel, exact: true }).click();
    const expected = [
      expectedWrite(api.governance, 0, 0, "Hypothesis 1 snapshot."),
      expectedWrite(api.governance, 1, 1, "Hypothesis 2 snapshot."),
    ];
    await expect.poll(() => api.writes).toEqual(expected);
    await api.releaseSave(hypotheses[0], outcome);
    await expect(page).toHaveURL(new RegExp(`/lessons/${lessons[1]}$`));
    await expect(
      page.getByRole("heading", {
        name: "Synthetic Hypothesis 1",
        exact: true,
      }),
    ).toHaveCount(0);
    await expect(
      page.getByText(`Proposal ${proposalIds[0]}`, { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("textbox", { name: "Rationale", exact: true }),
    ).toHaveValue("Hypothesis 2 snapshot.");
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(
      page.getByRole("button", {
        name: "Proposal wird angelegt …",
        exact: true,
      }),
    ).toBeDisabled();
    await dispatchSubmits(page);
    expect(api.writes).toEqual(expected);
    await api.releaseSave(hypotheses[1]);
    await expect(
      page.getByText(`Proposal ${proposalIds[1]}`, { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Status: DRAFT", { exact: true }),
    ).toBeVisible();
    if (outcome === "success") {
      await changeLesson(page, 0);
      await expect(
        page.getByText(`Proposal ${proposalIds[0]}`, { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("Hypothesis 1 snapshot.", { exact: true }),
      ).toBeVisible();
    }
    expect(api.writes).toEqual(expected);
  });
}

test("an unknown network completion does not repeat POST and explicit readback finds the saved DRAFT", async ({
  page,
  baseURL,
}) => {
  const api = await installApi(page, baseURL);
  await page.goto(`/lessons/${lessons[0]}`);
  const rationale = "Keep this until an explicit readback.";
  await selectModel(page, 0, rationale);
  await page.getByRole("button", { name: saveLabel, exact: true }).click();
  await expect.poll(() => api.writes).toHaveLength(1);
  await api.releaseSave(hypotheses[0], "disconnect");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Rationale", exact: true }),
  ).toHaveValue(rationale);
  expect(api.writes).toEqual([expectedWrite(api.governance, 0, 0, rationale)]);
  // Existing conscious readback: reload the actual Lesson page. The mock has
  // recorded server completion even though the response never reached the UI.
  await page.reload();
  await expect(
    page.getByText(`Proposal ${proposalIds[0]}`, { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Status: DRAFT", { exact: true })).toBeVisible();
  await expect(page.getByText(rationale, { exact: true })).toBeVisible();
  expect(api.writes).toEqual([expectedWrite(api.governance, 0, 0, rationale)]);
});

test("the existing Candidate editor creates explicit V2 from V1 without Validation, Approval or Activation writes", async ({
  page,
  baseURL,
}) => {
  const api = await installApi(page, baseURL);
  await page.goto(`/lessons/${lessons[0]}`);
  await selectModel(page, 2, "Explicit synthetic Candidate policy change.");
  await expect(
    page.getByRole("button", { name: saveLabel, exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("radio", { name: "FAVORABLE only", exact: true })
    .check();
  await page.getByRole("button", { name: saveLabel, exact: true }).click();
  const expected = [
    expectedWrite(
      api.governance,
      0,
      2,
      "Explicit synthetic Candidate policy change.",
      candidateV2,
    ),
  ];
  await expect.poll(() => api.writes).toEqual(expected);
  await api.releaseSave(hypotheses[0]);
  await expect(page.getByText("Status: DRAFT", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Retrospektive Validation erfassen" }),
  ).toBeVisible();
  expect(api.writes).toEqual(expected);
});
