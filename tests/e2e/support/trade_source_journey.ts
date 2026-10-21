import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import {
  expect,
  type APIRequestContext,
  type Page,
  type TestInfo,
} from "@playwright/test";

// Added to the existing protected owner journey, not a mocked UI test. All setup
// writes happen outside the fingerprinted read windows and after the DB guard.
export async function qualifyTradeSources(
  page: Page,
  request: APIRequestContext,
  testInfo: TestInfo,
  input: {
    api: string;
    root: string;
    tradeId: string;
    productId: string;
    planId: string;
    planVersionId: string;
    replacedExecutionId: string;
    replacementExecutionId: string;
    databaseState: () => { fingerprint: string; [key: string]: unknown };
  },
) {
  const { api, root, tradeId, databaseState } = input;
  const sourceUrl = (id: string, section = "", pin?: string) =>
    `${api}/trade-position/trades/${id}/sources${section ? `/${section}` : ""}${pin ? `?version_id=${pin}` : ""}`;
  const source = async (id: string, section = "", pin?: string) => {
    const response = await request.get(sourceUrl(id, section, pin));
    expect(response.status(), await response.text()).toBe(200);
    const body = await response.json();
    expect(Date.parse(body.read_started_at)).toBeLessThanOrEqual(
      Date.parse(body.read_completed_at),
    );
    return body;
  };
  const command = async (
    path: string,
    data?: object,
    method: "POST" | "PUT" = "POST",
  ) => {
    databaseState(); // independently verify the marked disposable target before every write
    const response = await request.fetch(api + path, {
      method,
      data,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  };
  const pageUrl = (id: string, review?: string, journal?: string) =>
    "/trade-management?" +
    new URLSearchParams({
      trade_id: id,
      view: "sources",
      ...(review ? { review_version_id: review } : {}),
      ...(journal ? { journal_version_id: journal } : {}),
    });
  const region = (name: string) =>
    page.getByRole("region", { name, exact: true });
  const settled = async () => {
    await expect(region("Evidence und Lesson-Versionen")).toContainText(
      "Eigenes Lesefenster",
    );
    await expect(region("Journal")).toContainText("Eigenes Lesefenster");
    await expect(region("Dokumentierte Exit-Bewertung")).toContainText(
      "Eigenes Lesefenster",
    );
    await expect(region("Ursprünglicher Plan")).toContainText(
      "Eigenes Lesefenster",
    );
  };
  const observed: Array<{ method: string; url: string }> = [];
  let readWindow = false;
  page.on("request", (req) => {
    if (readWindow && req.url().startsWith(api))
      observed.push({ method: req.method(), url: req.url() });
  });
  const originalPlan = await source(tradeId, "plan");
  expect(originalPlan.data.version.id).toBe(input.planVersionId);
  const p2 = await command(
    `/trade-plans/${input.planId}/versions/${input.planVersionId}/amendments`,
    {
      change_reason: "Synthetic later assumption, not the execution origin",
      thesis: "P2 must not replace the original execution plan",
      entry: { type: "PRICE", currency: "EUR", price: "101" },
      invalidation: { stop_price: "96" },
      targets: [{ sequence: 1, price: "111" }],
      risk_assumptions: { thesis_risk: "Later synthetic risk" },
    },
  );
  expect(p2.id).not.toBe(input.planVersionId);

  const firstBefore = databaseState();
  readWindow = true;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(pageUrl(tradeId));
  await settled();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    `TR-${tradeId.slice(0, 8).toUpperCase()}`,
  );
  await expect(region("Wirtschaftliches Gesamtergebnis")).toContainText(
    "noch nicht angebunden",
  );
  await expect(region("Wirtschaftliches Gesamtergebnis")).not.toContainText(
    "70,00",
  );
  await expect(region("Ursprünglicher Plan")).toContainText(
    originalPlan.data.version.thesis,
  );
  await expect(region("Ursprünglicher Plan")).not.toContainText(p2.thesis);
  await expect(region("Dokumentierte Exit-Bewertung")).toContainText(
    "Exit-Bewertung nicht dokumentiert",
  );
  await expect(region("Journal")).toContainText("Journal nicht dokumentiert");
  const oldSale = page.getByRole("article", {
    name: `Quelle ${input.replacedExecutionId}`,
    exact: true,
  });
  await expect(oldSale).toContainText("Historisch ersetzt");
  await expect(oldSale).toContainText("2026-09-12 · Uhrzeit unbekannt");
  await expect(
    page.getByRole("article", {
      name: `Quelle ${input.replacementExecutionId}`,
      exact: true,
    }),
  ).toContainText("Korrektur eines früheren Eintrags");
  await expect(page.getByRole("form")).toHaveCount(0);
  await page.screenshot({
    path: testInfo.outputPath("source-view-original-plan-desktop.png"),
    fullPage: true,
  });
  await page.reload();
  await settled();
  const core = await source(tradeId);
  expect(core.data.timeline).toHaveLength(7);
  expect(core.data.currency_history).toHaveLength(1);
  expect((await source(tradeId, "plan")).data).toEqual(originalPlan.data);
  const firstAfter = databaseState();
  expect(firstAfter.fingerprint).toBe(firstBefore.fingerprint);
  readWindow = false;

  // A second, older real trade has a completed synthetic observation horizon.
  // No future prices are invented for the October reference trade above.
  const capture = (quantity: number, price: string, day: string) => ({
    quantity,
    price_per_unit: price,
    executed_on: day,
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
  });
  const purchase = await command("/trade-position/purchases/external", {
    product_id: input.productId,
    ...capture(10, "2.00", "2026-08-17"),
    currency_confirmation: {
      currency_code: "EUR",
      source: "USER_CONFIRMED",
      note: "Synthetic source journey",
    },
  });
  const tid = purchase.trade.id;
  const sale = await command(
    `/trade-position/trades/${tid}/sales`,
    capture(10, "1.00", "2026-08-18"),
  );
  expect(sale.position.realized_gross_pnl).toBe("-10.0000000000");
  const observation = await command(`/post-trade/trades/${tid}/observation`);
  databaseState();
  execFileSync(
    process.env.REPORT_E2E_PYTHON ?? "python",
    [
      resolve(root, "tests/e2e/support/seed_source_view_prices.py"),
      tid,
      observation.underlying_listing_id,
    ],
    {
      cwd: root,
      env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
      encoding: "utf8",
    },
  );
  // This existing observation GET performs owner refresh; it is deliberate setup,
  // not part of the new source-view read-only window.
  databaseState();
  const refreshed = await request.get(
    `${api}/post-trade/trades/${tid}/observation`,
  );
  expect(refreshed.status(), await refreshed.text()).toBe(200);
  expect((await refreshed.json()).is_complete).toBe(true);
  await command(`/post-trade/trades/${tid}/exit-review`);
  await command(
    `/post-trade/trades/${tid}/exit-review/draft`,
    {
      timing: "NOT_ASSESSABLE",
      process_adherence: "GOOD",
      risk_decision: "ACCEPTABLE",
      overall_exit_decision: "GOOD",
      rationale: "Stored synthetic exit judgment, independent of the loss.",
    },
    "PUT",
  );
  const review = await command(
    `/post-trade/trades/${tid}/exit-review/finalize`,
  );
  const rid = review.current_version_id;
  const journalPath = `/learning/trades/${tid}/journal/commands`;
  const created = await command(journalPath, {
    operation: "CREATE_DRAFT",
    expected_latest_version_id: null,
    expected_exit_review_version_id: rid,
    confirmed: true,
  });
  const jid = created.result_id;
  await command(journalPath, {
    operation: "SAVE_DRAFT",
    version_id: jid,
    expected_edit_revision: 1,
    what_went_well:
      "Synthetic exact journal source <script>never executed</script>",
    would_do_differently: null,
    additional_notes: "No automatic rule violation.",
  });
  const draft = await source(tid, "journal", jid);
  expect(draft.data.selected.edit_revision).toBe(2);
  const draftBefore = databaseState();
  readWindow = true;
  await page.goto(pageUrl(tid, rid, jid));
  await settled();
  await expect(region("Journal")).toContainText("Bearbeitungsrevision 2");
  await expect(region("Journal")).toContainText("DRAFT");
  await page.reload();
  await settled();
  expect(databaseState().fingerprint).toBe(draftBefore.fingerprint);
  readWindow = false;
  await command(journalPath, {
    operation: "FINALIZE",
    version_id: jid,
    expected_edit_revision: 2,
    expected_exit_review_version_id: rid,
    confirmed: true,
  });
  const jeid = (
    await command(journalPath, {
      operation: "MATERIALIZE",
      version_id: jid,
      confirmed: true,
    })
  ).result_id;
  const feid = (
    await command(`/learning/trades/${tid}/ft011-evidence/materialize`, {
      expected_exit_review_version_id: rid,
    })
  ).learning_evidence_id;
  const lesson = await command("/learning/lessons", {
    title: "Synthetic source journey lesson",
    main_category: "Process",
    content: "Original exact interpretation L1",
    tags: [],
    evidence_links: [
      { learning_evidence_id: jeid, relation: "SUPPORTS" },
      { learning_evidence_id: feid, relation: "CONTRADICTS" },
    ],
  });
  const lid = lesson.lesson_id;
  const l1 = lesson.current_version_id;
  const successor = await command(`/learning/lessons/${lid}/versions`, {
    main_category: "Process",
    content: "Separate later interpretation L2",
    expected_current_version_id: l1,
    expected_current_state: "CURRENT",
    evidence_links: [
      { learning_evidence_id: jeid, relation: "CONTEXTUAL" },
      { learning_evidence_id: feid, relation: "CONTRADICTS" },
    ],
  });
  expect(successor.current_version_id).not.toBe(l1);
  const originalReview = await source(tid, "reviews", rid);
  const originalJournal = await source(tid, "journal", jid);
  const evidence = await source(tid, "evidence");
  await command(
    `/trade-position/trades/${tid}/executions/${sale.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 10,
      price_per_unit: "0.90",
      executed_on: "2026-08-18",
      execution_timezone: "Europe/Berlin",
    },
  );
  const secondBefore = databaseState();
  readWindow = true;
  await page.goto(pageUrl(tid, rid, jid));
  await settled();
  await expect(region("Ursprünglicher Plan")).toContainText(
    "EXTERNAL-Trade ohne dokumentierte ursprüngliche Planherkunft",
  );
  await expect(region("Dokumentierte Exit-Bewertung")).toContainText("GOOD");
  await expect(region("Dokumentierte Exit-Bewertung")).toContainText(
    "NOT_ASSESSABLE – ausdrücklich nicht beurteilbar",
  );
  await expect(region("Journal")).toContainText(
    "<script>never executed</script>",
  );
  const correctedReview = await source(tid, "reviews", rid);
  const correctedJournal = await source(tid, "journal", jid);
  expect(correctedReview.data.selected).toEqual(originalReview.data.selected);
  expect(correctedJournal.data.selected).toEqual(originalJournal.data.selected);
  expect(correctedReview.data.source_currentness).toBe("STALE");
  expect(correctedJournal.data.source_currentness).toBe("STALE");
  expect(correctedReview.data.selected.version.currentness).toBe("CURRENT");
  expect((await source(tid, "evidence")).data).toEqual(evidence.data);
  const historical = region("Evidence und Lesson-Versionen").getByRole("link", {
    name: /Version 1 · SUPPORTS · historische Version/,
  });
  await expect(historical).toHaveAttribute(
    "href",
    `/lessons/${lid}?lesson_version_id=${l1}#lesson-history`,
  );
  await historical.focus();
  await page.keyboard.press("Enter");
  const snapshot = page.getByRole("article", {
    name: "Lesson-Snapshot Version 1",
    exact: true,
  });
  await expect(snapshot).toContainText("Original exact interpretation L1");
  await expect(snapshot).toContainText("SUPPORTS");
  await expect(snapshot).toContainText("CONTRADICTS");
  await page.reload();
  await expect(snapshot).toContainText("Original exact interpretation L1");
  await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(l1);
  await page.goto(pageUrl(tid, rid, jid));
  await settled();
  await region("Evidence und Lesson-Versionen")
    .getByRole("link", {
      name: "Exakte Evidence-Journalquelle lesen",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(new RegExp(`journal_version_id=${jid}`));
  await expect(region("Journal")).toContainText("Journalversion 1 · FINALIZED");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: testInfo.outputPath("source-view-historical-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);

  const invalid = crypto.randomUUID();
  await page.goto(pageUrl(tid, rid, invalid));
  await expect(region("Journal").getByRole("alert")).toContainText(
    "Quelle konnte nicht gelesen werden",
  );
  await expect(region("Journal")).not.toContainText(
    "Synthetic exact journal source",
  );
  await expect(region("Dokumentierte Exit-Bewertung")).toContainText("GOOD");
  await page.reload();
  await expect(region("Journal").getByRole("alert")).toBeVisible();
  // One deliberately blocked transport request, never a successful fixture.
  const journalUrl = sourceUrl(tid, "journal", jid);
  await page.route(journalUrl, (route) => route.abort("failed"), { times: 1 });
  await page.goto(pageUrl(tid, rid, jid));
  await expect(region("Journal").getByRole("alert")).toBeVisible();
  await region("Journal")
    .getByRole("button", { name: "Journal neu lesen", exact: true })
    .click();
  await expect(region("Journal")).toContainText(
    "Synthetic exact journal source",
  );
  await settled();
  const secondAfter = databaseState();
  expect(secondAfter.fingerprint).toBe(secondBefore.fingerprint);
  readWindow = false;
  expect(observed.length).toBeGreaterThan(20);
  expect(observed.every((entry) => entry.method === "GET")).toBe(true);
  for (const section of ["", "/plan", "/reviews", "/journal", "/evidence"]) {
    expect(
      observed.some(
        (entry) => entry.url.split("?")[0] === sourceUrl(tradeId) + section,
      ),
    ).toBe(true);
  }
  await testInfo.attach("source-view-real-api-and-read-windows", {
    body: JSON.stringify(
      {
        core,
        originalPlan,
        originalReview,
        originalJournal,
        correctedReview,
        correctedJournal,
        evidence,
        firstBefore,
        firstAfter,
        draftBefore,
        secondBefore,
        secondAfter,
        observed,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
}
