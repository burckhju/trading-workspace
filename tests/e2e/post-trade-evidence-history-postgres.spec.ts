import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { prepareLearningQualification } from "./support/journal-evidence";
import { localLearningRequest } from "./support/journal-request-guard.mjs";

// Match the canonical origin used by the existing real-write browser cases.
test.use({ baseURL: "http://localhost:8080", serviceWorkers: "block" });

// Requires the separately identified CI Compose stack + Python fixtures. Never a user stack.
test("real PostgreSQL: FT011 history survives correction and opens the exact Lesson version", async ({
  page,
  request: rawRequest,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.FT011_E2E_WRITES_ALLOWED !== "1",
    "Explicit disposable PostgreSQL FT011 evidence browser qualification required",
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
  const history = page.getByRole("region", {
    name: "Bisherige Review-Evidence",
    exact: true,
  });
  await expect(
    history.getByText(
      "Noch keine Review-Evidence für diesen Trade gespeichert.",
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "An Lessons Learned übergeben", exact: true })
    .click();
  await expect(
    history.getByText("Review-Evidence · Review-Version 1", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Lesson-Titel", { exact: true })
    .fill("Explicit FT011 history lesson");
  await page.getByLabel("Lesson-Kategorie", { exact: true }).fill("Process");
  await page
    .getByLabel("Lesson-Inhalt", { exact: true })
    .fill("My original interpretation of this exact exit review.");
  await page
    .getByRole("button", { name: "Lesson anlegen", exact: true })
    .click();
  await expect(
    page.getByText("Bereits interpretiert", { exact: true }),
  ).toBeVisible();
  await history
    .getByRole("button", { name: "Evidence-Historie neu laden", exact: true })
    .click();
  const oldLink = history.getByRole("link", {
    name: /Explicit FT011 history lesson · Version 1 · SUPPORTS/,
  });
  await expect(oldLink).toBeVisible();
  const oldHref = (await oldLink.getAttribute("href"))!;
  const lid = new URL(oldHref, baseURL).pathname.split("/").at(-1)!;
  const lvid = new URL(oldHref, baseURL).searchParams.get("lesson_version_id");
  const originalLesson = await (
    await request.get(api + `/learning/lessons/${lid}/review-context`)
  ).json();
  const getInventory = async () => {
    const result = await request.get(
      api + `/learning/trades/${tid}/ft011-evidence/history`,
    );
    expect(result.status(), await result.text()).toBe(200);
    return result.json();
  };
  const originalInventory = await getInventory();
  const oldEvidence = originalInventory[0].learning_evidence_id;
  const oldReview = originalInventory[0].exit_review_version_id;
  expect(originalInventory[0].lesson_links[0].lesson_version_id).toBe(lvid);
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
  await page.reload();
  await expect(history.getByText(/Quellenprüfung: STALE/)).toBeVisible();
  await expect(
    page.getByText("Bereit für FT-012.", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Noch nicht bereit: EXIT_REVIEW_STALE", { exact: true }),
  ).toBeVisible();
  await expect(oldLink).toHaveAttribute("href", oldHref);
  expect(
    (
      await (
        await request.get(
          api + `/learning/trades/${tid}/ft011-evidence/materialization-status`,
        )
      ).json()
    ).ready,
  ).toBe(false);
  expect((await getInventory())[0].exit_review_version_id).toBe(oldReview);
  expect((await getInventory())[0].lesson_links).toEqual(
    originalInventory[0].lesson_links,
  );
  await page.screenshot({
    path: testInfo.outputPath("ft011-history-not-ready.png"),
    fullPage: true,
  });
  await oldLink.click();
  await expect(
    page.getByRole("article", {
      name: "Lesson-Snapshot Version 1",
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (
      await (
        await request.get(api + `/learning/lessons/${lid}/review-context`)
      ).json()
    ).history,
  ).toEqual(originalLesson.history);
  // New review and materialization are explicit, never a side effect of history reads.
  await page.goto(`/post-trade?trade_id=${tid}`);
  await page
    .getByRole("button", { name: "Review-Quellenstand prüfen", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Neue Review-Version vorbereiten",
      exact: true,
    })
    .click();
  await page
    .getByLabel("Review-Begründung")
    .fill("Explicit new review after confirmed execution correction.");
  await page
    .getByRole("button", { name: "Review finalisieren", exact: true })
    .click();
  await page
    .getByRole("button", { name: "An Lessons Learned übergeben", exact: true })
    .click();
  await expect(history.getByRole("article")).toHaveCount(2);
  const newInventory = await getInventory();
  const newEvidence = newInventory.find(
    (v: { learning_evidence_id: string }) =>
      v.learning_evidence_id !== oldEvidence,
  ).learning_evidence_id;
  // Explicit Lesson owner commands deliberately choose a different relation for V2.
  const commands = `/learning/lessons/${lid}/review-commands`;
  const command = async (data: object) => {
    const response = await request.post(api + commands, {
      data,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    expect(response.status(), await response.text()).toBe(200);
  };
  const getContext = async () => {
    const response = await request.get(
      api + `/learning/lessons/${lid}/review-context`,
    );
    expect(response.status(), await response.text()).toBe(200);
    return response.json();
  };
  const pinned = (c: {
    lesson: { current_version_id: string; current_state: string };
  }) => ({
    expected_current_version_id: c.lesson.current_version_id,
    expected_current_state: c.lesson.current_state,
    expected_open_signal_id: null,
    reason: "Explicit source correction with preserved V1.",
    confirmed: true,
  });
  await command({
    ...pinned(await getContext()),
    operation: "OPEN_SOURCE_REVIEW",
    reviewed_evidence_ids: [oldEvidence],
  });
  await command({
    ...pinned(await getContext()),
    operation: "NEW_VERSION",
    main_category: "Process",
    content: "My explicit successor interpretation.",
    evidence: [
      { learning_evidence_id: newEvidence, relation: "SUPPORTS" },
      { learning_evidence_id: oldEvidence, relation: "CONTRADICTS" },
    ],
  });
  await page.reload();
  const historicalLink = history.getByRole("link", {
    name: "Explicit FT011 history lesson · Version 1 · SUPPORTS · historisch",
    exact: true,
  });
  await expect(historicalLink).toHaveAttribute("href", oldHref);
  await expect(
    history.getByRole("link", { name: /Version 2 · CONTRADICTS/ }),
  ).toBeVisible();
  await historicalLink.click();
  await page.reload();
  const selected = page.getByRole("article", {
    name: "Lesson-Snapshot Version 1",
    exact: true,
  });
  await expect(
    selected.getByText(
      "My original interpretation of this exact exit review.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByLabel("Lesson-Version ansehen")).toHaveValue(lvid!);
  await expect(
    page.getByRole("button", {
      name: "Quellenbezogene Prüfung beginnen",
      exact: true,
    }),
  ).toHaveCount(0);
  expect((await getContext()).history[1]).toEqual(originalLesson.history[0]);
  await page.screenshot({
    path: testInfo.outputPath("ft011-exact-lesson-history.png"),
    fullPage: true,
  });
  await page.goto(
    `/lessons/${lid}?lesson_version_id=${crypto.randomUUID()}#lesson-history`,
  );
  await expect(
    page.getByText(/Die angeforderte Lesson-Version wurde nicht gefunden/),
  ).toBeVisible();
  await expect(
    page.getByRole("article", { name: /Lesson-Snapshot Version/ }),
  ).toHaveCount(0);
  await qualification.readWindow(
    "ft011-exact-history-read-only-sources",
    async () => ({
      trade_id: tid,
      initial_execution_ids: [buy.execution.id, sale.execution.id],
      evidence: await getInventory(),
      lesson: await getContext(),
    }),
  );
  qualification.assertNoUnexpectedRequests();
});
