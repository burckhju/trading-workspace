import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { prepareLearningQualification } from "./support/journal-evidence";
import { localLearningRequest } from "./support/journal-request-guard.mjs";

// Match the canonical origin used by the existing real-write browser cases.
test.use({ baseURL: "http://localhost:8080", serviceWorkers: "block" });

// Requires the separately identified CI Compose stack + Python fixtures. Never a user stack.
test("real PostgreSQL: captured full exit, review, journal, lesson and stale correction", async ({
  page,
  request: rawRequest,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.JOURNAL_E2E_WRITES_ALLOWED !== "1",
    "Explicit disposable PostgreSQL journal browser qualification required",
  );
  test.setTimeout(120_000);
  expect(process.env.CI).toBe("true");
  expect(baseURL).toBe("http://localhost:8080");
  const qualification = await prepareLearningQualification(
    page,
    baseURL,
    testInfo,
  );
  const request = localLearningRequest(rawRequest);
  const api = `${baseURL}/api/api/v1`;
  const post = async (
    path: string,
    data?: object,
    headers?: Record<string, string>,
  ) => {
    const response = await request.post(api + path, { data, headers });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  };
  const suffix = crypto.randomUUID();
  const runId = process.env.JOURNAL_E2E_RUN_ID!;
  const issuer = await post(
    "/market-reference-data/issuers",
    {
      legal_name: `Journal CI ${runId} ${suffix}`,
      display_name: "Synthetic journal CI",
    },
    {
      "X-Actor-ID": `journal-evidence:${runId}`,
      "X-Actor-Name": "Synthetic journal CI",
    },
  );
  const venue = (
    await (
      await request.get(api + "/market-reference-data/trading-venues")
    ).json()
  ).items.find((v: { mic: string }) => v.mic === "XETR");
  const underlying = await post("/underlyings", {
    name: `Synthetic journal ${suffix}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venue.id,
      ticker: `J${suffix.slice(0, 7)}`,
      currency_code: "EUR",
    },
  });
  const product = await post("/warrants", {
    issuer_id: issuer.id,
    underlying_id: underlying.id,
    display_name: `Synthetic Journal Call ${suffix}`,
    option_direction: "CALL",
    strike: "500",
    strike_currency_code: "EUR",
    maturity_date: "2099-12-31",
    ratio: "0.1",
  });
  const buy = await post("/trade-position/purchases/external", {
    product_id: product.id,
    quantity: 10,
    price_per_unit: "0.55",
    executed_on: "2026-08-17",
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
  });
  const tid = buy.trade.id;
  const rejected = await request.post(
    api + `/post-trade/trades/${tid}/observation`,
  );
  expect(rejected.status(), await rejected.text()).toBe(422);
  expect((await rejected.json()).code).toBe("POST_TRADE_NOT_ELIGIBLE");
  const sale = await post(`/trade-position/trades/${tid}/sales`, {
    quantity: 10,
    price_per_unit: "0.65",
    executed_on: "2026-08-18",
    execution_timezone: "Europe/Berlin",
    request_id: crypto.randomUUID(),
  });
  expect(sale.position.is_closed).toBe(true);
  expect(Number(sale.position.realized_gross_pnl)).toBe(1);
  const observation = await post(`/post-trade/trades/${tid}/observation`);
  const root = resolve(process.cwd(), "..");
  execFileSync(
    process.env.JOURNAL_E2E_PYTHON ?? "python",
    [
      resolve(root, "tests/e2e/support/seed_journal_prices.py"),
      observation.underlying_listing_id,
      "0",
      "19",
    ],
    {
      cwd: root,
      env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
      stdio: "pipe",
    },
  );
  const incomplete = await (
    await request.get(api + `/post-trade/trades/${tid}/observation`)
  ).json();
  expect(incomplete.available_observation_count).toBe(19);
  expect(incomplete.is_complete).toBe(false);
  execFileSync(
    process.env.JOURNAL_E2E_PYTHON ?? "python",
    [
      resolve(root, "tests/e2e/support/seed_journal_prices.py"),
      observation.underlying_listing_id,
      "19",
      "20",
    ],
    {
      cwd: root,
      env: { ...process.env, PYTHONPATH: `${root}/backend:${root}` },
      stdio: "pipe",
    },
  );
  await page.goto(`/post-trade?trade_id=${tid}`);
  // FT-011 owner refresh completes only after 20 seeded completed sessions.
  await expect(page.getByText("COMPLETED", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Exit Review anlegen", exact: true })
    .click();
  await page
    .getByLabel("Review-Begründung")
    .fill(
      "Bewusstes synthetisches Review – kein handelbarer Underlying-Vergleich.",
    );
  await page
    .getByRole("button", { name: "Review finalisieren", exact: true })
    .click();
  const journal = page.getByRole("region", {
    name: "Trade-Journal",
    exact: true,
  });
  await journal
    .getByRole("button", { name: "Journalentwurf anlegen", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await journal
    .getByLabel("Was lief gut?")
    .fill("Exit und Reflexion getrennt dokumentiert.");
  await journal
    .getByLabel("Weitere Notizen")
    .fill("Kein virtueller Gewinn wurde als realisiert erfasst.");
  await expect(
    journal.getByRole("button", { name: "Journal finalisieren", exact: true }),
  ).toBeDisabled();
  await journal
    .getByRole("button", { name: "Journalentwurf speichern", exact: true })
    .click();
  await expect(
    journal.getByRole("button", { name: "Journal finalisieren", exact: true }),
  ).toBeEnabled();
  await page.reload();
  await expect(journal.getByLabel("Was lief gut?")).toHaveValue(
    "Exit und Reflexion getrennt dokumentiert.",
  );
  await journal
    .getByRole("button", { name: "Journal finalisieren", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await expect(journal.getByLabel("Was lief gut?")).toHaveCount(0);
  const getHistory = async () => {
    const response = await request.get(api + `/learning/trades/${tid}/journal`);
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const original = (await getHistory()).versions[0].version;
  await journal
    .getByRole("button", {
      name: "Journalversion als Evidence übergeben",
      exact: true,
    })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await journal.getByLabel("Lesson-Titel").fill("Synthetische Journal-Lesson");
  await journal.getByLabel("Lesson-Kategorie").fill("Prozess");
  await journal
    .getByLabel("Lesson-Inhalt")
    .fill(
      "Meine ausdrückliche Interpretation: Dokumentation prüfen, keine automatische Handelsregel.",
    );
  await journal
    .getByRole("button", { name: "Lesson anlegen", exact: true })
    .click();
  const lessonLink = journal.getByRole("link", {
    name: "Angelegte Lesson öffnen",
    exact: true,
  });
  await expect(lessonLink).toBeVisible();
  const lessonPath = (await lessonLink.getAttribute("href"))!;
  const lessonId = lessonPath.split("/").at(-1)!;
  const persisted = await request.get(api + `/learning/lessons/${lessonId}`);
  expect(persisted.status(), await persisted.text()).toBe(200);
  const before = await persisted.json();
  await post(
    `/trade-position/trades/${tid}/executions/${sale.execution.id}/corrections`,
    {
      side: "SELL",
      quantity: 10,
      price_per_unit: "0.60",
      executed_on: "2026-08-18",
      execution_timezone: "Europe/Berlin",
    },
  );
  await journal
    .getByRole("button", { name: "Quellenstand neu laden", exact: true })
    .click();
  await expect(journal.getByText(/Quellenprüfung jetzt: STALE/)).toBeVisible();
  expect((await getHistory()).versions[0].version).toEqual(original);
  await lessonLink.click();
  await expect(page.getByText(/Quellenprüfung jetzt: STALE/)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Genau diese Journalversion öffnen" }),
  ).toHaveAttribute(
    "href",
    `/post-trade?trade_id=${tid}&journal_version_id=${original.id}`,
  );
  const after = await (
    await request.get(api + `/learning/lessons/${lessonId}`)
  ).json();
  expect(after).toEqual(before);
  await page.screenshot({
    path: testInfo.outputPath("journal-real-postgres-stale.png"),
    fullPage: true,
  });
  // Explicit FT-011 owner actions make a controlled new journal possible.
  await page.goto(`/post-trade?trade_id=${tid}`);
  await page
    .getByRole("button", { name: "Review-Quellenstand prüfen", exact: true })
    .click();
  await expect(
    page.getByText("Dieser Review ist STALE und muss erneut geprüft werden."),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Neue Review-Version vorbereiten",
      exact: true,
    })
    .click();
  await page
    .getByLabel("Review-Begründung")
    .fill("Neue Bewertung nach bestätigter Ausführungskorrektur.");
  await page
    .getByRole("button", { name: "Review finalisieren", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Folgeversion vorbereiten", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await expect(journal.getByLabel("Was lief gut?")).toHaveValue(
    original.what_went_well,
  );
  await journal
    .getByLabel("Was würde ich anders machen?")
    .fill("Ausführungsbeleg vor dem Review prüfen.");
  await journal
    .getByRole("button", { name: "Journalentwurf speichern", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journal finalisieren", exact: true })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await expect(journal.getByLabel("Was lief gut?")).toHaveCount(0);
  const corrected = await getHistory();
  expect(corrected.versions).toHaveLength(2);
  expect(corrected.versions[0].version.status).toBe("FINALIZED");
  expect(corrected.versions[0].version.supersedes_version_id).toBe(original.id);
  expect(corrected.versions[0].source_currentness).toBe("CURRENT");
  expect(corrected.versions[1].source_currentness).toBe("STALE");
  expect(corrected.versions[1].version).toEqual(original);
  expect(
    await (await request.get(api + `/learning/lessons/${lessonId}`)).json(),
  ).toEqual(before);
  await page.screenshot({
    path: testInfo.outputPath("journal-real-postgres-successor.png"),
    fullPage: true,
  });

  // Continue the same genuine database journey into explicit Lesson source review.
  await journal
    .getByRole("button", {
      name: "Journalversion als Evidence übergeben",
      exact: true,
    })
    .click();
  await journal
    .getByRole("button", { name: "Journalaktion bestätigen", exact: true })
    .click();
  await expect(journal.getByLabel("Lesson-Titel")).toBeVisible();
  const evidence2 = (await getHistory()).versions[0].learning_evidence_id;
  expect(evidence2).toBeTruthy();
  const reviewContext = async () => {
    const response = await request.get(
      api + `/learning/lessons/${lessonId}/review-context`,
    );
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const originalLessonContext = await reviewContext();
  const oldLessonVersion = originalLessonContext.history[0];
  const reviewWrites: {
    body: Record<string, unknown>;
    key: string | undefined;
  }[] = [];
  page.on("request", (req) => {
    if (
      req.method() === "POST" &&
      req.url().endsWith(`/learning/lessons/${lessonId}/review-commands`)
    )
      reviewWrites.push({
        body: req.postDataJSON(),
        key: req.headers()["idempotency-key"],
      });
  });
  await page.goto(lessonPath);
  const lessonReview = page.getByRole("region", {
    name: "Lesson-Prüfung und Historie",
    exact: true,
  });
  await lessonReview
    .getByRole("button", {
      name: "Quellenbezogene Prüfung beginnen",
      exact: true,
    })
    .click();
  expect(reviewWrites).toHaveLength(0);
  const confirmReview = lessonReview.getByRole("button", {
    name: "Prüfentscheidung verbindlich bestätigen",
    exact: true,
  });
  await expect(confirmReview).toBeDisabled();
  await lessonReview
    .getByLabel(/Begründung der Prüfentscheidung/)
    .fill(
      "Die zugrunde liegende Ausführung und das Journal wurden korrigiert.",
    );
  await confirmReview.click();
  await expect(
    lessonReview.getByText(/Lesson-Status: REVIEW_RECOMMENDED/),
  ).toBeVisible();
  expect(reviewWrites).toHaveLength(1);
  expect(reviewWrites[0].body).toMatchObject({
    operation: "OPEN_SOURCE_REVIEW",
    expected_current_version_id: oldLessonVersion.version.id,
    expected_current_state: "CURRENT",
    expected_open_signal_id: null,
    confirmed: true,
  });
  expect((await reviewContext()).history).toEqual(
    originalLessonContext.history,
  );
  await lessonReview
    .getByRole("button", {
      name: "Weitere ausdrückliche Prüfung vorbereiten",
      exact: true,
    })
    .click();
  await lessonReview
    .getByRole("button", {
      name: "Neue Lesson-Version vorbereiten",
      exact: true,
    })
    .click();
  await expect(lessonReview.getByLabel("Bezug 1", { exact: true })).toHaveValue(
    "SUPPORTS",
  );
  await expect(
    lessonReview.getByLabel("Vorhandene Evidence ergänzen"),
  ).toBeEnabled();
  await lessonReview
    .getByLabel("Vorhandene Evidence ergänzen")
    .selectOption(evidence2);
  await lessonReview
    .getByRole("button", {
      name: "Ausgewählte Evidence hinzufügen",
      exact: true,
    })
    .click();
  await expect(lessonReview.getByLabel("Bezug 2", { exact: true })).toHaveValue(
    "CONTEXTUAL",
  );
  await lessonReview
    .getByLabel("Bezug 1", { exact: true })
    .selectOption("CONTEXTUAL");
  await lessonReview
    .getByLabel(/Begründung der Prüfentscheidung/)
    .fill(
      "Ich beziehe mich ausdrücklich auf das korrigierte Journal, alte Quelle bleibt Kontext.",
    );
  await expect(confirmReview).toBeDisabled(); // No inferred SUPPORTS on a newly added source.
  await lessonReview
    .getByLabel("Bezug 2", { exact: true })
    .selectOption("SUPPORTS");
  await lessonReview
    .getByLabel("Ausdrückliche Interpretation der neuen Lesson-Version")
    .fill(
      "Meine überprüfte Interpretation anhand der ausdrücklich gewählten Journal-Folgeversion.",
    );
  await confirmReview.click();
  await expect(
    page.getByText("Version 2 · CURRENT", { exact: true }),
  ).toBeVisible();
  const latest = await reviewContext();
  expect(latest.history).toHaveLength(2);
  expect(latest.history[1]).toEqual(oldLessonVersion);
  expect(latest.history[0].version.supersedes_version_id).toBe(
    oldLessonVersion.version.id,
  );
  expect(
    latest.history[0].evidence_links
      .map((link: { learning_evidence_id: string; relation: string }) => [
        link.learning_evidence_id,
        link.relation,
      ])
      .sort(),
  ).toEqual(
    [
      [before.evidence[0].learning_evidence_id, "CONTEXTUAL"],
      [evidence2, "SUPPORTS"],
    ].sort(),
  );
  expect(latest.signals).toEqual([]); // Source ageing was not relabelled a contradiction.
  expect(reviewWrites).toHaveLength(2);
  expect(reviewWrites[1].body).toMatchObject({
    operation: "NEW_VERSION",
    expected_current_version_id: oldLessonVersion.version.id,
    expected_current_state: "REVIEW_RECOMMENDED",
    expected_open_signal_id: null,
    confirmed: true,
  });
  expect(reviewWrites[0].key).toBeTruthy();
  expect(reviewWrites[1].key).not.toBe(reviewWrites[0].key);
  await page.reload();
  await expect(
    page.getByText("Version 2 · CURRENT", { exact: true }),
  ).toBeVisible();
  await lessonReview
    .getByLabel("Lesson-Version ansehen")
    .selectOption(oldLessonVersion.version.id);
  const historical = lessonReview.getByRole("article", {
    name: "Lesson-Snapshot Version 1",
    exact: true,
  });
  await expect(
    historical.getByText(before.content, { exact: true }),
  ).toBeVisible();
  await expect(
    lessonReview.getByRole("button", {
      name: "Quellenbezogene Prüfung beginnen",
      exact: true,
    }),
  ).toHaveCount(0);
  await historical
    .getByText(
      `SUPPORTS · Evidence ${before.evidence[0].learning_evidence_id}`,
      { exact: true },
    )
    .click();
  await expect(
    historical.getByText("Quellversion jetzt: SUPERSEDED", { exact: true }),
  ).toBeVisible();
  await expect(
    historical.getByText("Review-Quelle jetzt: STALE", { exact: true }),
  ).toBeVisible();
  expect((await getHistory()).versions[1].version).toEqual(original);
  expect(reviewWrites).toHaveLength(2); // Reload/history/source reads generate nothing.
  await page.screenshot({
    path: testInfo.outputPath("lesson-review-historical-source.png"),
    fullPage: true,
  });
  await qualification.readWindow(
    "journal-lesson-read-only-sources",
    async () => ({
      trade_id: tid,
      initial_execution_ids: [buy.execution.id, sale.execution.id],
      journal: await getHistory(),
      lesson: await reviewContext(),
    }),
  );
  qualification.assertNoUnexpectedRequests();
});
