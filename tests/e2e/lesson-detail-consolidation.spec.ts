import {
  expect,
  test,
  type Page,
  type Route,
  type TestInfo,
} from "@playwright/test";
import type {
  EvidenceChoice,
  EvidenceSummary,
  ReviewCommand,
  ReviewContext,
} from "../../frontend/src/features/learning/services/lessonReviewClient";

// Real browser / intercepted HTTP regression. All mutations remain in synthetic
// in-memory fixtures; PostgreSQL persistence is qualified by the existing owner job.
const at = "2026-10-26T10:00:00Z";
const lessonId = "10000000-0000-4000-8000-000000000001";
const versions = [1, 2, 3].map(
  (n) => `20000000-0000-4000-8000-00000000000${n}`,
);
const evidenceIds = [1, 2, 3].map(
  (n) => `30000000-0000-4000-8000-00000000000${n}`,
);
const tradeId = "40000000-0000-4000-8000-000000000001";
const journalId = "50000000-0000-4000-8000-000000000001";
const journalVersions = [1, 2].map(
  (n) => `60000000-0000-4000-8000-00000000000${n}`,
);
const reviewId = "70000000-0000-4000-8000-000000000001";
const externalVersionId = "80000000-0000-4000-8000-000000000001";
const originalContent = "Original interpretation bound to the first journal.";
const currentContent =
  "Current interpretation with three deliberately assigned sources.";
const revisedContent =
  "Revised interpretation; all existing source assignments remain intact.";
const journalText =
  "The original personal reflection belongs only to the journal.";
const evidence: EvidenceChoice[] = [
  { learning_evidence_id: evidenceIds[0], relation: "SUPPORTS" },
  { learning_evidence_id: evidenceIds[1], relation: "CONTRADICTS" },
  { learning_evidence_id: evidenceIds[2], relation: "CONTEXTUAL" },
];
const catalog: EvidenceSummary[] = [
  {
    evidence_id: evidenceIds[0],
    source_type: "TRADE_JOURNAL_VERSION",
    source: {
      type: "TRADE_JOURNAL_VERSION",
      trade_journal_version_id: journalVersions[0],
    },
    created_at: at,
  },
  {
    evidence_id: evidenceIds[1],
    source_type: "FT011",
    source: {
      type: "FT011",
      trade_id: tradeId,
      exit_review_version_id: reviewId,
    },
    created_at: at,
  },
  {
    evidence_id: evidenceIds[2],
    source_type: "EXTERNAL_OBSERVATION",
    source: {
      type: "EXTERNAL_OBSERVATION",
      external_observation_version_id: externalVersionId,
    },
    created_at: at,
  },
];
const snapshot = (number: number, content: string, choices = evidence) => ({
  version: {
    id: versions[number - 1],
    lesson_id: lessonId,
    version: number,
    main_category: "Prozess",
    content,
    created_at: at,
    created_by: "synthetic-actor",
    supersedes_version_id: number > 1 ? versions[number - 2] : null,
  },
  evidence_links: choices.map((choice, index) => ({
    ...choice,
    id: `90000000-0000-4000-8000-0000000000${number}${index + 1}`,
    lesson_version_id: versions[number - 1],
  })),
});
const journalHistory = () => ({
  trade_id: tradeId,
  journal_id: journalId,
  handoff: {
    ready: false,
    reason: "EXIT_REVIEW_STALE",
    exit_review_version_id: reviewId,
  },
  versions: [2, 1].map((number) => ({
    version: {
      id: journalVersions[number - 1],
      trade_journal_id: journalId,
      version: number,
      edit_revision: 1,
      status: "FINALIZED",
      what_went_well: number === 1 ? journalText : "Later personal reflection.",
      would_do_differently:
        number === 1 ? "Original alternative." : "Later alternative.",
      additional_notes:
        number === 1 ? "Original journal notes." : "Later journal notes.",
      source_exit_review_version_id: reviewId,
      supersedes_version_id: number === 1 ? null : journalVersions[0],
      created_at: at,
      created_by: "synthetic-actor",
      updated_at: at,
      updated_by: "synthetic-actor",
      finalized_at: at,
      finalized_by: "synthetic-actor",
    },
    is_latest: number === 2,
    source_currentness: number === 1 ? "STALE" : "CURRENT",
    source_checked_at: at,
    learning_evidence_id: number === 1 ? evidenceIds[0] : null,
  })),
});

type Write = { path: string; body: ReviewCommand; key: string | null };
async function installApi(
  page: Page,
  baseURL: string | undefined,
  state: "CURRENT" | "REVIEW_RECOMMENDED",
) {
  if (!baseURL) throw new Error("A local frontend URL is required.");
  const frontendOrigin = new URL(baseURL).origin;
  const apiBase = new URL(
    process.env.E2E_VITE_API_BASE_URL ??
      process.env.VITE_API_BASE_URL ??
      "http://localhost:8080/api",
  );
  const prefix = `${apiBase.pathname.replace(/\/$/, "")}/api/v1`;
  const context: ReviewContext = {
    lesson: {
      id: lessonId,
      title: "Synthetic consolidated lesson",
      current_version_id: versions[1],
      current_state: state,
    },
    history: [
      snapshot(2, currentContent),
      snapshot(1, originalContent, evidence.slice(0, 1)),
    ],
    signals: [],
    transitions: [],
    read_at: at,
  };
  const originalHistory = structuredClone(context.history);
  const writes: Write[] = [];
  const unexpected: string[] = [];
  const errors: string[] = [];
  const reads: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const json = (route: Route, data: unknown, status = 200) =>
    route.fulfill({ status, json: data });
  await page.context().route("**/*", async (route) => {
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
    const path = url.pathname.slice(prefix.length);
    if (
      url.origin === apiBase.origin &&
      url.pathname.startsWith(`${prefix}/`) &&
      !url.search
    ) {
      if (method === "GET") {
        reads.push(path);
        if (path === `/learning/lessons/${lessonId}/review-context`)
          return json(route, context);
        if (path === "/learning/learning-evidence") return json(route, catalog);
        if (
          versions.some(
            (id) =>
              path === `/model-governance/lesson-versions/${id}/hypotheses`,
          )
        )
          return json(route, []);
        const entry = catalog.find(
          (item) => path === `/learning/learning-evidence/${item.evidence_id}`,
        );
        if (entry) return json(route, entry);
        const sourceIndex = evidenceIds.findIndex(
          (id) => path === `/learning/learning-evidence/${id}/currentness`,
        );
        if (sourceIndex >= 0)
          return json(route, {
            evidence_id: evidenceIds[sourceIndex],
            source_type: catalog[sourceIndex].source_type,
            source_version_id: [
              journalVersions[0],
              reviewId,
              externalVersionId,
            ][sourceIndex],
            source_currentness: ["SUPERSEDED", "CURRENT", "UNKNOWN"][
              sourceIndex
            ],
            review_currentness: sourceIndex === 0 ? "STALE" : null,
            superseded_by_version_id:
              sourceIndex === 0 ? journalVersions[1] : null,
            checked_at: at,
          });
        if (
          path === `/learning/journal-versions/${journalVersions[0]}` ||
          path === `/learning/trades/${tradeId}/journal`
        )
          return json(route, journalHistory());
        if (path === `/learning/trades/${tradeId}/ft011-evidence/history`)
          return json(route, []);
        if (
          path ===
          `/learning/trades/${tradeId}/ft011-evidence/materialization-status`
        )
          return json(route, {
            ready: false,
            reason: "EXIT_REVIEW_STALE",
            materialized: false,
            learning_evidence_id: null,
            exit_review_version_id: null,
          });
        if (path === `/post-trade/trades/${tradeId}/handoff`)
          return json(route, {
            ready: false,
            reason: "EXIT_REVIEW_STALE",
            post_trade_observation_id: null,
            exit_review_id: null,
            exit_review_version_id: null,
          });
        if (
          [
            `/trade-position/trades/${tradeId}`,
            `/post-trade/trades/${tradeId}/observation`,
            `/post-trade/trades/${tradeId}/exit-review`,
          ].includes(path)
        )
          return json(
            route,
            {
              code: "NOT_FOUND",
              message: "Synthetic optional source context is not present.",
              details: [],
              timestamp: at,
            },
            404,
          );
      }
      if (
        method === "POST" &&
        path === `/learning/lessons/${lessonId}/review-commands`
      ) {
        const body = request.postDataJSON() as ReviewCommand;
        writes.push({
          path,
          body,
          key: request.headers()["idempotency-key"] ?? null,
        });
        if (body.operation === "NEW_VERSION") {
          context.history = [
            snapshot(3, body.content, body.evidence),
            ...context.history,
          ];
          context.lesson.current_version_id = versions[2];
          context.lesson.current_state = "CURRENT";
          return json(route, {
            lesson_id: lessonId,
            result_id: versions[2],
            result_type: "LESSON_VERSION",
            replayed: false,
          });
        }
        if (body.operation === "OPEN_SOURCE_REVIEW") {
          context.lesson.current_state = "REVIEW_RECOMMENDED";
          return json(route, {
            lesson_id: lessonId,
            result_id: "synthetic-source-review",
            result_type: "LESSON_STATE_TRANSITION",
            replayed: false,
          });
        }
      }
    }
    unexpected.push(`${method} ${url}`);
    return json(
      route,
      {
        code: "UNEXPECTED_SYNTHETIC_REQUEST",
        message: "Unexpected API request.",
        details: [],
        timestamp: at,
      },
      500,
    );
  });
  return {
    writes,
    reads,
    context,
    originalHistory,
    async verify(info: TestInfo) {
      expect(unexpected).toEqual([]);
      expect(errors).toEqual([]);
      await info.attach("lesson-http-contract", {
        body: JSON.stringify({ reads, writes, unexpected, errors }, null, 2),
        contentType: "application/json",
      });
    },
  };
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "narrow", width: 390, height: 844 },
]) {
  test.describe(viewport.name, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      serviceWorkers: "block",
    });
    test("one selected snapshot, exact historical links and canonical journal texts", async ({
      page,
      baseURL,
    }, info) => {
      const api = await installApi(page, baseURL, "CURRENT");
      await page.goto(`/lessons/${lessonId}`);
      await expect(page.getByText(currentContent, { exact: true })).toHaveCount(
        1,
      );
      await expect(
        page.getByText(originalContent, { exact: true }),
      ).toHaveCount(0);
      await expect(
        page.getByText("Heutiger Lesson-Status: CURRENT", { exact: true }),
      ).toBeVisible();
      for (const item of evidence)
        await expect(
          page.getByText(
            `${item.relation} · Evidence ${item.learning_evidence_id}`,
            { exact: true },
          ),
        ).toHaveCount(1);
      const externalSource = page.getByText(
        `CONTEXTUAL · Evidence ${evidenceIds[2]}`,
        { exact: true },
      );
      await externalSource.click();
      await expect(
        page.getByText("Quellversion jetzt: UNKNOWN", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("link", {
          name: "Genau diese Journalversion öffnen",
          exact: true,
        }),
      ).toHaveCount(0);
      await externalSource.click();
      await page.getByLabel("Lesson-Version ansehen").selectOption(versions[0]);
      expect(new URL(page.url()).searchParams.get("lesson_version_id")).toBe(
        versions[0],
      );
      await expect(
        page.getByText(originalContent, { exact: true }),
      ).toHaveCount(1);
      await expect(page.getByText(currentContent, { exact: true })).toHaveCount(
        0,
      );
      await expect(
        page.getByText(`CONTRADICTS · Evidence ${evidenceIds[1]}`, {
          exact: true,
        }),
      ).toHaveCount(0);
      await expect(
        page.getByRole("button", {
          name: "Quellenbezogene Prüfung beginnen",
          exact: true,
        }),
      ).toHaveCount(0);
      await expect(
        page.getByRole("button", {
          name: "Hypothese für FT-013 anlegen",
          exact: true,
        }),
      ).toBeEnabled();
      const exactLesson = page.getByRole("link", {
        name: "Genau diese Lesson-Version öffnen",
        exact: true,
      });
      await expect(exactLesson).toHaveAttribute(
        "href",
        `/lessons/${lessonId}?lesson_version_id=${versions[0]}#lesson-history`,
      );
      await page.reload();
      await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(
        versions[0],
      );
      await page.goBack();
      await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(
        versions[1],
      );
      await page.goForward();
      await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(
        versions[0],
      );
      const source = page.getByText(`SUPPORTS · Evidence ${evidenceIds[0]}`, {
        exact: true,
      });
      await source.focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByText("Quellversion jetzt: SUPERSEDED", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("Review-Quelle jetzt: STALE", { exact: true }),
      ).toBeVisible();
      await expect(page.getByText(journalText, { exact: true })).toHaveCount(0);
      await expect(
        page.getByText("Was lief gut?", { exact: true }),
      ).toHaveCount(0);
      await info.attach(`${viewport.name}-historical-lesson`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      });
      const exactJournal = page.getByRole("link", {
        name: "Genau diese Journalversion öffnen",
        exact: true,
      });
      await expect(exactJournal).toHaveAttribute(
        "href",
        `/post-trade?trade_id=${tradeId}&journal_version_id=${journalVersions[0]}`,
      );
      await exactJournal.click();
      const journal = page.getByRole("region", {
        name: "Trade-Journal",
        exact: true,
      });
      await expect(
        journal.getByRole("heading", {
          name: "Journal V1 · Finalisiert (unveränderlich)",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        journal.getByText(journalText, { exact: true }),
      ).toBeVisible();
      await expect(
        journal.getByText("Later personal reflection.", { exact: true }),
      ).toHaveCount(0);
      expect(api.writes).toEqual([]);
      expect(api.reads).not.toContain(`/learning/lessons/${lessonId}`);
      await api.verify(info);
    });

    test("prefilled editor, guarded version navigation and one explicit complete successor", async ({
      page,
      baseURL,
    }, info) => {
      const api = await installApi(page, baseURL, "REVIEW_RECOMMENDED");
      await page.goto(`/lessons/${lessonId}`);
      await page
        .getByRole("button", {
          name: "Neue Lesson-Version vorbereiten",
          exact: true,
        })
        .click();
      const editor = page.getByRole("form", {
        name: "Lesson-Prüfentscheidung",
        exact: true,
      });
      await expect(
        editor.getByLabel("Kategorie der neuen Lesson-Version"),
      ).toHaveValue("Prozess");
      const content = editor.getByLabel(
        "Ausdrückliche Interpretation der neuen Lesson-Version",
      );
      await expect(content).toHaveValue(currentContent);
      await expect(
        page.locator("p").filter({ hasText: currentContent }),
      ).toHaveCount(0);
      await expect(
        page.getByRole("article", {
          name: "Lesson-Snapshot Version 2",
          exact: true,
        }),
      ).toHaveCount(0);
      for (let index = 0; index < evidence.length; index++)
        await expect(
          editor.getByLabel(`Bezug ${index + 1}`, { exact: true }),
        ).toHaveValue(evidence[index].relation);
      await expect(
        editor.getByLabel(/Begründung der Prüfentscheidung/),
      ).toHaveValue("");
      await expect(
        editor.getByRole("link", {
          name: "Genau diese Journalversion öffnen",
          exact: true,
        }),
      ).toHaveAttribute(
        "href",
        `/post-trade?trade_id=${tradeId}&journal_version_id=${journalVersions[0]}`,
      );
      await expect(
        editor.getByText("Materialisiert: " + at, { exact: true }),
      ).toHaveCount(3);
      await content.fill(revisedContent);
      await page.getByLabel("Lesson-Version ansehen").selectOption(versions[0]);
      const dialog = page.getByRole("alertdialog");
      await expect(dialog).toHaveCount(1);
      await expect(
        dialog.getByRole("button", { name: "Hier bleiben", exact: true }),
      ).toBeFocused();
      await dialog
        .getByRole("button", { name: "Hier bleiben", exact: true })
        .click();
      await expect(content).toHaveValue(revisedContent);
      await page.getByLabel("Lesson-Version ansehen").selectOption(versions[0]);
      await dialog
        .getByRole("button", {
          name: "Eingaben verwerfen und wechseln",
          exact: true,
        })
        .click();
      await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(
        versions[0],
      );
      await expect(editor).toHaveCount(0);
      expect(api.writes).toEqual([]);
      await page.getByLabel("Lesson-Version ansehen").selectOption(versions[1]);
      await page
        .getByRole("button", {
          name: "Neue Lesson-Version vorbereiten",
          exact: true,
        })
        .click();
      await content.fill(revisedContent);
      await editor
        .getByLabel(/Begründung der Prüfentscheidung/)
        .fill("Explicitly revised interpretation; original sources retained.");
      await editor
        .getByRole("button", {
          name: "Prüfentscheidung verbindlich bestätigen",
          exact: true,
        })
        .click();
      await expect(page.getByText(revisedContent, { exact: true })).toHaveCount(
        1,
      );
      await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(
        versions[2],
      );
      expect(new URL(page.url()).searchParams.get("lesson_version_id")).toBe(
        versions[2],
      );
      await expect(
        page.getByText(/Prüfentscheidung gespeichert/),
      ).toBeVisible();
      await expect(dialog).toHaveCount(0);
      expect(api.writes).toHaveLength(1);
      expect(api.writes[0].key).toBeTruthy();
      expect(api.writes[0].body).toEqual({
        operation: "NEW_VERSION",
        expected_current_version_id: versions[1],
        expected_current_state: "REVIEW_RECOMMENDED",
        expected_open_signal_id: null,
        reason: "Explicitly revised interpretation; original sources retained.",
        confirmed: true,
        main_category: "Prozess",
        content: revisedContent,
        evidence,
      });
      expect(api.context.history.slice(1)).toEqual(api.originalHistory);
      await info.attach(`${viewport.name}-confirmed-successor`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: "image/png",
      });
      await page.reload();
      await expect(page.getByText(revisedContent, { exact: true })).toHaveCount(
        1,
      );
      expect(api.writes).toHaveLength(1);
      await api.verify(info);
    });
  });
}
