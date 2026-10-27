import { expect, test, type Page } from "@playwright/test";
import type { JournalHistory } from "../../frontend/src/features/learning/services/journalClient";

// Real browser, application router and forms; synthetic HTTP responses only.
// PostgreSQL qualification remains in the two separately guarded owner journeys.
const tradeId = "10000000-0000-4000-8000-000000000001";
const journalId = "20000000-0000-4000-8000-000000000001";
const finalId = "30000000-0000-4000-8000-000000000001";
const draftId = "30000000-0000-4000-8000-000000000002";
const reviewId = "40000000-0000-4000-8000-000000000001";
const historicalReviewId = "40000000-0000-4000-8000-000000000009";
const directEvidenceId = "50000000-0000-4000-8000-000000000001";
const journalEvidenceId = "50000000-0000-4000-8000-000000000002";
const at = "2026-10-25T12:00:00Z";
const fields = [
  ["Was lief gut?", "Bewusst dokumentierter Ausstieg."],
  ["Was würde ich anders machen?", "Belege vor dem Review abgleichen."],
  [
    "Weitere Notizen",
    "Persönliche Reflexion ohne automatische Interpretation.",
  ],
] as const;

async function setup(page: Page, selectedId = draftId) {
  const writes: {
    path: string;
    body: Record<string, unknown> | null;
    key?: string;
  }[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  let readGate: Promise<void> | null = null;
  let releaseReads = () => {};
  let journalReadFails = false;
  const history: JournalHistory = {
    trade_id: tradeId,
    journal_id: journalId,
    handoff: { ready: true, reason: "READY", exit_review_version_id: reviewId },
    versions: [2, 1].map((version) => ({
      version: {
        id: version === 2 ? draftId : finalId,
        trade_journal_id: journalId,
        version,
        edit_revision: 3,
        status: version === 2 ? "DRAFT" : "FINALIZED",
        source_exit_review_version_id:
          version === 2 ? reviewId : historicalReviewId,
        supersedes_version_id: version === 2 ? finalId : null,
        created_at: at,
        created_by: "synthetic-actor",
        updated_at: at,
        updated_by: "synthetic-actor",
        finalized_at: version === 2 ? null : at,
        finalized_by: version === 2 ? null : "synthetic-actor",
        what_went_well:
          version === 2 ? fields[0][1] : "Historische Reflexion V1.",
        would_do_differently: fields[1][1],
        additional_notes: fields[2][1],
      },
      is_latest: version === 2,
      source_currentness: version === 2 ? "CURRENT" : "STALE",
      source_checked_at: at,
      learning_evidence_id: version === 2 ? null : journalEvidenceId,
    })),
  };
  const review = {
    exit_review_id: "synthetic-review",
    current_version_id: reviewId,
    version: 1,
    status: "FINALIZED",
    currentness: "CURRENT",
    timing: "GOOD",
    process_adherence: "GOOD",
    risk_decision: "GOOD",
    overall_exit_decision: "GOOD",
    rationale: "Gespeicherte Review-Begründung.",
    created_at: at,
    created_by: "synthetic-actor",
    finalized_at: at,
    finalized_by: "synthetic-actor",
    supersedes_version_id: null,
    stale_at: null,
    stale_reason: null,
  };
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.split("/api/v1")[1];
    const body = request.postData() ? request.postDataJSON() : null;
    const json = (value: unknown, status = 200) =>
      route.fulfill({ status, json: value });
    if (request.method() !== "GET") {
      writes.push({ path, body, key: request.headers()["idempotency-key"] });
      if (path.endsWith("/journal/commands")) {
        const version = history.versions.find(
          (entry) => entry.version.id === body.version_id,
        )?.version;
        if (version && body.operation === "SAVE_DRAFT") {
          version.what_went_well = body.what_went_well;
          version.would_do_differently = body.would_do_differently;
          version.additional_notes = body.additional_notes;
          version.edit_revision += 1;
        } else if (version && body.operation === "FINALIZE") {
          version.status = "FINALIZED";
          version.edit_revision += 1;
          version.finalized_at = at;
          version.finalized_by = "synthetic-actor";
        } else {
          return json(
            {
              code: "UNEXPECTED_COMMAND",
              message: "Unexpected synthetic command",
            },
            409,
          );
        }
        return json({
          result_id: version.id,
          result_type: "TRADE_JOURNAL_VERSION",
          replayed: false,
        });
      }
      if (path.endsWith("/exit-review/revalidate")) return json(review);
      return json(
        {
          code: "UNEXPECTED_WRITE",
          message: "No synthetic writer for this action",
        },
        409,
      );
    }
    if (readGate) await readGate;
    if (path.endsWith("/journal")) {
      if (journalReadFails)
        return json(
          { code: "READ_UNAVAILABLE", message: "Synthetic read failure" },
          503,
        );
      return json(history);
    }
    if (path.endsWith("/materialization-status"))
      return json({
        ready: true,
        reason: "READY",
        materialized: true,
        learning_evidence_id: directEvidenceId,
        exit_review_version_id: reviewId,
      });
    if (path.endsWith("/ft011-evidence/history")) return json([]);
    if (/\/learning\/learning-evidence\/[^/]+\/lessons$/.test(path))
      return json([]);
    if (path.endsWith("/observation"))
      return json({
        id: "synthetic-observation",
        trade_id: tradeId,
        status: "COMPLETED",
        underlying_listing_id: "synthetic-listing",
        target_observation_count: 20,
        available_observation_count: 20,
        missing_observation_count: 0,
        is_complete: true,
        started_at: at,
        completed_at: at,
        created_at: at,
      });
    if (path.endsWith("/observation/evidence"))
      return json({
        observation_id: "synthetic-observation",
        trade_id: tradeId,
        product_context: null,
        planning_context: {
          trade_plan_id: null,
          trade_plan_version_id: null,
          original_stop: null,
          original_targets: [],
        },
        management_levels: [],
        actual_exit: {
          full_exit_at: at,
          realized_gross_pnl: null,
          executions: [],
        },
        counterfactual: null,
      });
    if (path.endsWith("/handoff"))
      return json({
        ready: true,
        reason: "READY",
        post_trade_observation_id: "synthetic-observation",
        exit_review_id: review.exit_review_id,
        exit_review_version_id: reviewId,
      });
    if (path.endsWith("/exit-review/history")) return json([review]);
    if (path.endsWith("/exit-review")) return json(review);
    if (path === `/trade-position/trades/${tradeId}`)
      return json({
        id: tradeId,
        product_id: "synthetic-product",
        origin: "EXTERNAL",
        trade_plan_id: null,
        trade_plan_version_id: null,
        created_at: at,
      });
    return json(
      { code: "NOT_FOUND", message: "No optional synthetic context" },
      404,
    );
  });
  await page.goto(
    `/post-trade?trade_id=${tradeId}&journal_version_id=${selectedId}&tab=reflection`,
  );
  return {
    writes,
    errors,
    history,
    pauseReads() {
      readGate = new Promise<void>((resolve) => {
        releaseReads = resolve;
      });
    },
    resumeReads() {
      readGate = null;
      releaseReads();
    },
    failJournalRead(value: boolean) {
      journalReadFails = value;
    },
  };
}

test("journal UI keeps exact historical URL identity through refresh and browser history at 390px", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const fixture = await setup(page, finalId);
  const journal = page.getByRole("region", {
    name: "Trade-Journal",
    exact: true,
  });
  const selection = journal.getByLabel("Journalversion ansehen");
  await expect(selection).toHaveValue(finalId);
  await expect(
    journal.getByText("Historische Reflexion V1.", { exact: true }),
  ).toHaveCount(1);
  await expect(journal.getByText(fields[0][1], { exact: true })).toHaveCount(0);
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  await expect(selection).toHaveValue(finalId);
  await selection.selectOption(draftId);
  await expect(selection).toHaveValue(draftId);
  expect(new URL(page.url()).searchParams.get("tab")).toBe("reflection");
  await page.goBack();
  await expect(selection).toHaveValue(finalId);
  await page.goForward();
  await expect(selection).toHaveValue(draftId);
  await page.reload();
  await expect(selection).toHaveValue(draftId);
  for (const [, text] of fields)
    await expect(journal.getByText(text, { exact: true })).toHaveCount(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("journal-ui-390px.png"),
    fullPage: true,
  });
  await journal.screenshot({
    path: testInfo.outputPath("journal-panel-390px.png"),
  });
  for (const query of [
    "journal_version_id=",
    "journal_version_id=unknown",
    `journal_version_id=${finalId}&journal_version_id=${draftId}`,
  ]) {
    await page.goto(`/post-trade?trade_id=${tradeId}&${query}`);
    await expect(journal.getByRole("alert")).toBeVisible();
    await expect(journal.getByText(fields[0][1], { exact: true })).toHaveCount(
      0,
    );
    await expect(
      journal.getByRole("button", { name: "Journal bearbeiten", exact: true }),
    ).toHaveCount(0);
  }
  expect(fixture.writes).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test("journal UI replaces text with prefilled edit and confirmation and preserves dirty text on keyboard cancellation", async ({
  page,
}) => {
  const fixture = await setup(page);
  const journal = page.getByRole("region", {
    name: "Trade-Journal",
    exact: true,
  });
  await journal
    .getByRole("button", { name: "Journal bearbeiten", exact: true })
    .click();
  for (const [label, text] of fields)
    await expect(journal.getByLabel(label)).toHaveValue(text);
  const finalize = journal.getByRole("button", {
    name: "Journal finalisieren",
    exact: true,
  });
  await finalize.click();
  const confirmation = journal.getByRole("dialog");
  const cancel = confirmation.getByRole("button", {
    name: "Abbrechen",
    exact: true,
  });
  const confirm = confirmation.getByRole("button", {
    name: "Journalaktion bestätigen",
    exact: true,
  });
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(cancel).toBeFocused();
  for (const [label, text] of fields) {
    await expect(journal.getByLabel(label)).toHaveCount(0);
    await expect(journal.getByText(text, { exact: true })).toHaveCount(1);
  }
  await page.keyboard.press("Escape");
  await expect(finalize).toBeFocused();
  await journal
    .getByLabel("Was lief gut?")
    .fill("Lokale, noch ungespeicherte Reflexion.");
  await expect(finalize).toBeDisabled();
  await journal.getByLabel("Journalversion ansehen").selectOption(finalId);
  const guard = page.getByRole("alertdialog");
  await expect(
    guard.getByRole("button", { name: "Hier bleiben", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(journal.getByLabel("Was lief gut?")).toHaveValue(
    "Lokale, noch ungespeicherte Reflexion.",
  );
  await journal
    .getByRole("button", {
      name: "Gespeicherten Journalstand laden (lokalen Text verwerfen)",
      exact: true,
    })
    .click();
  await page.keyboard.press("Escape");
  await expect(journal.getByLabel("Was lief gut?")).toHaveValue(
    "Lokale, noch ungespeicherte Reflexion.",
  );
  expect(fixture.writes).toEqual([]);
  await journal
    .getByRole("button", { name: "Journalentwurf speichern", exact: true })
    .click();
  await expect(journal.getByLabel("Was lief gut?")).toHaveCount(0);
  await expect(
    journal.getByText("Lokale, noch ungespeicherte Reflexion.", {
      exact: true,
    }),
  ).toHaveCount(1);
  await finalize.click();
  await confirm.click();
  await expect(
    journal.getByRole("heading", {
      name: "Journal V2 · Finalisiert (unveränderlich)",
      exact: true,
    }),
  ).toBeVisible();
  expect(fixture.writes.map((write) => write.body?.operation)).toEqual([
    "SAVE_DRAFT",
    "FINALIZE",
  ]);
  expect(fixture.writes[1].body).toMatchObject({
    version_id: draftId,
    expected_edit_revision: 4,
    expected_exit_review_version_id: reviewId,
  });
  expect(fixture.errors).toEqual([]);
});

test("journal UI keeps real parent journal and both lesson forms mounted across parent refresh and failed read", async ({
  page,
}) => {
  const fixture = await setup(page, finalId);
  const journal = page.getByRole("region", {
    name: "Trade-Journal",
    exact: true,
  });
  const directLesson = page.locator("section").filter({
    has: page.getByRole("heading", { name: "FT-012 Learning", exact: true }),
  });
  await journal
    .getByLabel("Lesson-Titel")
    .fill("Journalquelle bleibt gebunden");
  await journal.getByLabel("Lesson-Kategorie").fill("Journal");
  await journal
    .getByLabel("Lesson-Inhalt")
    .fill("Eigene Interpretation der historischen Journalquelle.");
  await directLesson
    .getByLabel("Lesson-Titel")
    .fill("FT011-Quelle bleibt getrennt");
  await directLesson.getByLabel("Lesson-Kategorie").fill("Review");
  await directLesson
    .getByLabel("Lesson-Inhalt")
    .fill("Unabhängige Interpretation der FT011-Evidence.");
  fixture.pauseReads();
  await page
    .getByRole("button", { name: "Review-Quellenstand prüfen", exact: true })
    .click();
  await expect(journal.getByLabel("Lesson-Titel")).toHaveValue(
    "Journalquelle bleibt gebunden",
  );
  await expect(directLesson.getByLabel("Lesson-Titel")).toHaveValue(
    "FT011-Quelle bleibt getrennt",
  );
  fixture.resumeReads();
  await expect(
    journal.getByRole("button", { name: "Lesson anlegen", exact: true }),
  ).toBeEnabled();
  await expect(
    directLesson.getByRole("button", { name: "Lesson anlegen", exact: true }),
  ).toBeEnabled();
  fixture.failJournalRead(true);
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  await expect(journal.getByRole("alert")).toBeVisible();
  await expect(journal.getByLabel("Lesson-Titel")).toHaveValue(
    "Journalquelle bleibt gebunden",
  );
  await expect(
    journal.getByRole("button", { name: "Lesson anlegen", exact: true }),
  ).toBeDisabled();
  fixture.failJournalRead(false);
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  await expect(
    journal.getByRole("button", { name: "Lesson anlegen", exact: true }),
  ).toBeEnabled();
  await journal.getByLabel("Journalversion ansehen").selectOption(draftId);
  await page.getByRole("button", { name: "Hier bleiben", exact: true }).click();
  await expect(journal.getByLabel("Lesson-Titel")).toHaveValue(
    "Journalquelle bleibt gebunden",
  );
  await expect(directLesson.getByLabel("Lesson-Titel")).toHaveValue(
    "FT011-Quelle bleibt getrennt",
  );
  // A changed read binding cannot silently retarget an open interpretation.
  const nextJournalEvidenceId = "50000000-0000-4000-8000-000000000099";
  fixture.history.versions.find(
    (entry) => entry.version.id === finalId,
  )!.learning_evidence_id = nextJournalEvidenceId;
  const writesBeforeEvidenceChange = fixture.writes.length;
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  const changedEvidence = journal
    .getByRole("alert")
    .filter({ hasText: "Die Evidence hat sich geändert" });
  await expect(changedEvidence).toBeVisible();
  await expect(changedEvidence).toContainText(journalEvidenceId);
  await expect(journal.getByLabel("Lesson-Titel")).toHaveValue(
    "Journalquelle bleibt gebunden",
  );
  await expect(journal.getByLabel("Lesson-Inhalt")).toHaveValue(
    "Eigene Interpretation der historischen Journalquelle.",
  );
  await expect(
    journal.getByRole("button", { name: "Lesson anlegen", exact: true }),
  ).toBeDisabled();
  const openChangedEvidence = journal.getByRole("button", {
    name: "Eingaben verwerfen und neue Evidence öffnen",
    exact: true,
  });
  await expect(openChangedEvidence).toBeEnabled();
  await openChangedEvidence.click();
  for (const label of ["Lesson-Titel", "Lesson-Kategorie", "Lesson-Inhalt"])
    await expect(journal.getByLabel(label)).toHaveValue("");
  await expect(changedEvidence).toHaveCount(0);
  await expect(journal.getByText(/LearningEvidence:/)).toContainText(
    nextJournalEvidenceId,
  );
  await expect(directLesson.getByLabel("Lesson-Titel")).toHaveValue(
    "FT011-Quelle bleibt getrennt",
  );
  await expect(directLesson.getByLabel("Lesson-Inhalt")).toHaveValue(
    "Unabhängige Interpretation der FT011-Evidence.",
  );
  expect(fixture.writes).toHaveLength(writesBeforeEvidenceChange);
  expect(fixture.writes.map((write) => write.path)).toEqual([
    `/post-trade/trades/${tradeId}/exit-review/revalidate`,
  ]);
  expect(fixture.errors).toEqual([]);
});
