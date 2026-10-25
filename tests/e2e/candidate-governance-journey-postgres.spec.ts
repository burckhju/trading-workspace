import { expect, test } from "@playwright/test";
import { prepareGovernanceJourney } from "./support/candidate-governance-journey";
import { createGovernanceSetup } from "./support/candidate-governance-setup";

test.use({
  baseURL: "http://localhost:8080",
  serviceWorkers: "block",
  timezoneId: "Europe/Berlin",
});

test("candidate governance: exact Lesson source, explicit A-B-A and immutable evaluations", async ({
  page,
  context,
  request,
  baseURL,
}, testInfo) => {
  test.skip(
    process.env.CANDIDATE_GOVERNANCE_E2E_WRITES_ALLOWED !== "1",
    "Requires the independently guarded synthetic Candidate governance stack",
  );
  test.setTimeout(120_000);
  expect(baseURL).toBe("http://localhost:8080");
  const q = await prepareGovernanceJourney(context, request, testInfo);
  try {
    const setup = await createGovernanceSetup(q);
    const { modelId, versionA, lessonId, l1, l2, evidenceId, candidateId } =
      setup;
    q.allowLesson(lessonId, [l1, l2], evidenceId);
    q.allowModel(modelId);
    q.allowCandidate(candidateId);
    for (const analysis of setup.analyses)
      q.allowRead(
        `/market-analyses/${analysis.analysis.id}/runs/${analysis.run.version}`,
      );
    q.setPhase("S1-active-A");
    const lessonUrl = `/lessons/${lessonId}?lesson_version_id=${l1}`;
    const candidateUrl = `/candidates?candidate=${candidateId}`;
    const candidate = await context.newPage();
    await candidate.setViewportSize({ width: 1440, height: 1000 });
    const currentActivation = () =>
      q.getJson(`/model-governance/models/${modelId}/runtime-activation`);
    const evaluationHistory = () =>
      q.getJson(`/candidates/${candidateId}/evaluations`);
    const readyButton = candidate.getByRole("button", {
      name: "Top-down neu bewerten",
      exact: true,
    });
    const runtimeRegion = () =>
      page.getByRole("region", { name: "Runtime-Aktivierung", exact: true });
    await candidate.goto(candidateUrl);
    await expect(readyButton).toBeEnabled();
    const originalReadiness = await q.getJson(
      `/candidates/${candidateId}/live-workflow`,
    );
    expect(originalReadiness.can_evaluate).toBe(true);
    expect(
      originalReadiness.steps.find(
        (step: { code: string }) => step.code === "CANDIDATE_RUNTIME_MODEL",
      ),
    ).toMatchObject({ status: "COMPLETE", resource_id: versionA.id });

    const evaluate = async (
      label: string,
      version: number,
      qualified: boolean,
    ) => {
      const receipt = await q.uiCommand(
        candidate,
        label,
        `/candidates/${candidateId}/evaluations/auto`,
        () => readyButton.click(),
        201,
      );
      const body = receipt.body;
      await expect(
        candidate.getByRole("region", {
          name: `Evaluation ${body.id}`,
          exact: true,
        }),
      ).toBeVisible();
      await expect(readyButton).toBeEnabled();
      const history = await evaluationHistory();
      const stored = history.find(
        (item: { id: string }) => item.id === body.id,
      );
      expect(stored).toMatchObject({
        model_id: "TOP_DOWN_CANDIDATE",
        model_version: String(version),
        qualification: qualified ? "QUALIFIED" : "NOT_QUALIFIED",
        // Existing FT006 maps VALID prices to LIMITED. Do not seed false GOOD
        // snapshots or silently change the released analysis model for this test.
        quality_status: "LIMITED",
      });
      expect(
        stored.criteria.find(
          (item: { criterion_id: string }) =>
            item.criterion_id === "TD-MARKET-001",
        ),
      ).toMatchObject({
        actual_value: "CAUTIOUS",
        evaluation: qualified ? "FULFILLED" : "NOT_FULFILLED",
      });
      expect(
        stored.criteria
          .filter(
            (item: { severity: string; criterion_id: string }) =>
              item.severity === "REQUIRED" &&
              item.criterion_id !== "TD-MARKET-001",
          )
          .every(
            (item: { evaluation: string }) => item.evaluation === "FULFILLED",
          ),
      ).toBe(true);
      expect(stored.sources).toHaveLength(3);
      for (const source of stored.sources) {
        const reference =
          setup.analysisRefs[source.role as keyof typeof setup.analysisRefs];
        expect(source).toMatchObject({
          source_type: "ANALYSIS",
          source_id: reference.analysis_id,
          source_version: reference.version,
          model_id: "EOD_TREND_MOMENTUM",
          model_version: "1.0.0",
        });
      }
      await q.record(`${label}-persisted-sources-and-criteria`, stored);
      return stored;
    };
    const firstA = await evaluate("S1-evaluation-A", versionA.version, true);

    await q.readWindow("S2-opening-exact-L1-is-read-only", async () => {
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.goto(lessonUrl);
      await expect(
        page.getByRole("article", {
          name: "Lesson-Snapshot Version 1",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", {
          name: "Hypothese für FT-013 anlegen",
          exact: true,
        }),
      ).toBeEnabled();
      await expect(
        page.getByRole("link", {
          name: "Genau diese Lesson-Version öffnen",
          exact: true,
        }),
      ).toHaveAttribute("href", `${lessonUrl}#lesson-history`);
      expect(
        await q.getJson(`/model-governance/lesson-versions/${l1}/hypotheses`),
      ).toEqual([]);
      expect(
        await q.getJson(`/model-governance/lesson-versions/${l2}/hypotheses`),
      ).toEqual([]);
      return {
        selectedLessonVersion: l1,
        currentLessonVersion: l2,
        activation: await currentActivation(),
      };
    });
    await page
      .getByLabel("Titel", { exact: true })
      .fill("Synthetische Candidate-Steuerbarkeit ab L1");
    await page
      .getByLabel("Hypothese", { exact: true })
      .fill(
        "Bewusste Hypothese aus genau L1/E1: Die vorhandene V2-Policy lässt sich ausdrücklich wechseln und zurückstellen. Keine Aussage über wirtschaftliche Überlegenheit.",
      );
    const hypothesis = (
      await q.uiCommand(
        page,
        "S2-create-hypothesis-from-L1",
        `/model-governance/lesson-versions/${l1}/hypotheses`,
        () =>
          page
            .getByRole("button", {
              name: "Hypothese für FT-013 anlegen",
              exact: true,
            })
            .click(),
        201,
      )
    ).body;
    expect(hypothesis.source_lesson_version_id).toBe(l1);
    expect(hypothesis.source_lesson_version_id).not.toBe(l2);
    await page
      .getByLabel("Governed Model", { exact: true })
      .selectOption(modelId);
    await expect(
      page.getByLabel("APPROVED Base-Version", { exact: true }),
    ).toHaveValue(versionA.id);
    await page
      .getByLabel("Rationale", { exact: true })
      .fill(
        "Synthetischer A-B-A-Nachweis; keine Regel- oder Performanceempfehlung.",
      );
    await expect(
      page.getByRole("button", {
        name: "ModelChangeProposal als DRAFT anlegen",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("radio", { name: "FAVORABLE only", exact: true })
      .check();
    await page.screenshot({
      path: testInfo.outputPath("S2-policy-base-desktop.png"),
      fullPage: true,
    });
    const proposalReceipt = await q.uiCommand(
      page,
      "S2-create-DRAFT-against-A",
      "/model-governance/proposals",
      () =>
        page
          .getByRole("button", {
            name: "ModelChangeProposal als DRAFT anlegen",
            exact: true,
          })
          .click(),
      201,
    );
    const proposal = proposalReceipt.body;
    expect(proposalReceipt.payload).toMatchObject({
      model_id: modelId,
      hypothesis_id: hypothesis.id,
      base_model_version_id: versionA.id,
      proposed_definition: {
        schema: "TOP_DOWN_CANDIDATE/2.0",
        direction: "LONG",
        market_context_allowed: ["FAVORABLE"],
      },
    });
    expect(proposal).toMatchObject({
      status: "DRAFT",
      hypothesis_id: hypothesis.id,
      base_model_version_id: versionA.id,
    });
    expect(
      await q.getJson(`/model-governance/proposals/${proposal.id}/validations`),
    ).toEqual([]);
    expect((await currentActivation()).id).toBe(setup.initialActivation.id);

    // A selected Evidence is not an interpretation. Deliberately enter the
    // synthetic conclusion and rationale; Metrics stays the existing optional {}.
    await page
      .getByLabel("LearningEvidence IDs", { exact: true })
      .fill(evidenceId);
    await page
      .getByLabel("Conclusion", { exact: true })
      .selectOption("INCONCLUSIVE");
    await page.getByLabel("Metrics (JSON)", { exact: true }).fill("{}");
    const notes =
      "Ausdrücklich synthetischer technischer Befund: INCONCLUSIVE zur wirtschaftlichen Wirkung. Kein Backtest, keine Performanceprognose und keine Empfehlung gegen CAUTIOUS.";
    await page.getByLabel("Notes", { exact: true }).fill(notes);
    const localTimestamp = async (iso: string) =>
      page.evaluate((value) => {
        const d = new Date(value);
        const p = (n: number) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
      }, iso);
    const tooEarly = new Date(
      Date.parse(setup.evidence.created_at) - 1000,
    ).toISOString();
    await page
      .getByLabel("Evidence Cutoff", { exact: true })
      .fill(await localTimestamp(tooEarly));
    const rejected = await q.uiCommand(
      page,
      "S3-reject-Evidence-after-cutoff-without-partial-facts",
      `/model-governance/proposals/${proposal.id}/validations`,
      () =>
        page
          .getByRole("button", {
            name: "Proposal retrospektiv validieren",
            exact: true,
          })
          .click(),
      422,
    );
    expect(rejected.body.code).toBe("MODEL_GOVERNANCE_VALIDATION_ERROR");
    await expect(
      page.getByRole("button", {
        name: "Validierungsstand neu laden",
        exact: true,
      }),
    ).toBeVisible();
    await q.readWindow(
      "S3-conscious-readback-after-rejected-validation",
      async () => {
        await page
          .getByRole("button", {
            name: "Validierungsstand neu laden",
            exact: true,
          })
          .click();
        await expect(
          page.getByLabel("Evidence Cutoff", { exact: true }),
        ).toBeEnabled();
        expect(
          await q.getJson(
            `/model-governance/proposals/${proposal.id}/validations`,
          ),
        ).toEqual([]);
        expect((await currentActivation()).model_version_id).toBe(versionA.id);
        return { validations: [], activeVersion: versionA.id };
      },
    );
    const cutoff = await localTimestamp(new Date().toISOString());
    const expectedCutoff = await page.evaluate(
      (value) => new Date(value).toISOString(),
      cutoff,
    );
    expect(Date.parse(expectedCutoff)).toBeGreaterThanOrEqual(
      Date.parse(setup.evidence.created_at),
    );
    await page.getByLabel("Evidence Cutoff", { exact: true }).fill(cutoff);
    const validationReceipt = await q.uiCommand(
      page,
      "S3-record-explicit-synthetic-validation",
      `/model-governance/proposals/${proposal.id}/validations`,
      () =>
        page
          .getByRole("button", {
            name: "Proposal retrospektiv validieren",
            exact: true,
          })
          .click(),
      201,
    );
    expect(validationReceipt.payload).toMatchObject({
      evidence_ids: [evidenceId],
      evidence_cutoff_at: expectedCutoff,
      conclusion: "INCONCLUSIVE",
      metrics: {},
      notes,
    });
    const validation = validationReceipt.body;
    expect(validation).toMatchObject({
      proposal_id: proposal.id,
      evidence_ids: [evidenceId],
      conclusion: "INCONCLUSIVE",
      metrics: {},
      notes,
    });
    expect(Date.parse(validation.evidence_cutoff_at)).toBe(
      Date.parse(expectedCutoff),
    );
    await expect(
      page.getByRole("button", {
        name: "VALIDATED Proposal approven",
        exact: true,
      }),
    ).toBeEnabled();
    expect((await currentActivation()).model_version_id).toBe(versionA.id);

    const approval = (
      await q.uiCommand(
        page,
        "S4-explicit-approval-B-without-activation",
        `/model-governance/proposals/${proposal.id}/approve`,
        () =>
          page
            .getByRole("button", {
              name: "VALIDATED Proposal approven",
              exact: true,
            })
            .click(),
        200,
      )
    ).body;
    const versionB = approval.model_version;
    expect(versionB).toMatchObject({
      model_id: modelId,
      version: 2,
      status: "APPROVED",
      previous_version_id: versionA.id,
      definition: proposal.proposed_definition,
    });
    expect(approval.approval).toMatchObject({
      proposal_id: proposal.id,
      model_version_id: versionB.id,
    });
    await expect(runtimeRegion()).toContainText(
      `Aktuell aktiv: Version ${versionA.version}`,
    );
    await expect(runtimeRegion()).toContainText(
      `Neueste Modellversion: ${versionB.version}`,
    );
    await q.readWindow(
      "S4-approved-B-and-still-active-A-readback",
      async () => {
        expect((await currentActivation()).id).toBe(setup.initialActivation.id);
        const versions = await q.getJson(
          `/model-governance/models/${modelId}/versions`,
        );
        expect(
          versions.find((v: { id: string }) => v.id === versionA.id),
        ).toEqual(versionA);
        expect(
          await q.getJson(
            `/model-governance/proposals/${proposal.id}/validations`,
          ),
        ).toEqual([validation]);
        await page.screenshot({
          path: testInfo.outputPath("S4-approved-B-active-A-desktop.png"),
          fullPage: true,
        });
        return {
          versions,
          approval,
          validation,
          active: await currentActivation(),
        };
      },
    );
    const approvedOnlyA = await evaluate(
      "S4-approval-alone-still-evaluates-A",
      versionA.version,
      true,
    );
    expect(approvedOnlyA.sources).toEqual(firstA.sources);

    // Keep the candidate tab's genuine A-readiness visible while the other tab
    // changes activation. Execution must resolve B afresh, not reuse that read.
    const readinessBeforeSwitch = await q.getJson(
      `/candidates/${candidateId}/live-workflow`,
    );
    expect(
      readinessBeforeSwitch.steps.find(
        (s: { code: string }) => s.code === "CANDIDATE_RUNTIME_MODEL",
      ).resource_id,
    ).toBe(versionA.id);
    await expect(
      candidate.getByText(
        `Active executable model TOP_DOWN_CANDIDATE version ${versionA.version}.`,
        { exact: true },
      ),
    ).toBeVisible();
    await page
      .getByLabel("Genehmigte Zielversion", { exact: true })
      .selectOption(versionB.id);
    const activationB = (
      await q.uiCommand(
        page,
        "S5-explicit-activation-B",
        `/model-governance/models/${modelId}/versions/${versionB.id}/activate`,
        () =>
          runtimeRegion()
            .getByRole("button", { name: "Version 2 aktivieren", exact: true })
            .click(),
      )
    ).body;
    expect(activationB.model_version_id).toBe(versionB.id);
    expect(activationB.id).not.toBe(setup.initialActivation.id);
    const secondB = await evaluate(
      "S5-evaluation-B-after-A-readiness",
      versionB.version,
      false,
    );
    expect(secondB.sources).toEqual(firstA.sources);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: testInfo.outputPath("S5-active-B-mobile.png"),
      fullPage: true,
    });

    await page
      .getByLabel("Genehmigte Zielversion", { exact: true })
      .selectOption(versionA.id);
    const returnA = (
      await q.uiCommand(
        page,
        "S6-explicit-return-to-approved-A",
        `/model-governance/models/${modelId}/versions/${versionA.id}/activate`,
        () =>
          runtimeRegion()
            .getByRole("button", { name: "Version 1 aktivieren", exact: true })
            .click(),
      )
    ).body;
    expect(returnA.model_version_id).toBe(versionA.id);
    expect(
      new Set([returnA.id, activationB.id, setup.initialActivation.id]).size,
    ).toBe(3);
    const thirdA = await evaluate(
      "S6-evaluation-returned-A",
      versionA.version,
      true,
    );
    expect(thirdA.sources).toEqual(firstA.sources);
    expect(thirdA.criteria).toEqual(firstA.criteria);
    expect(
      secondB.criteria.filter(
        (item: { criterion_id: string }) =>
          item.criterion_id !== "TD-MARKET-001",
      ),
    ).toEqual(
      firstA.criteria.filter(
        (item: { criterion_id: string }) =>
          item.criterion_id !== "TD-MARKET-001",
      ),
    );

    await q.readWindow(
      "S7-reload-and-exact-historical-links-read-only",
      async () => {
        await page.reload();
        await expect(runtimeRegion()).toContainText(
          `Aktuell aktiv: Version ${versionA.version}`,
        );
        await expect(runtimeRegion()).toContainText(versionA.id);
        await expect(runtimeRegion()).toContainText(
          `Neueste Modellversion: ${versionB.version}`,
        );
        await expect(
          page.getByText(`Gewählte Evidence: ${evidenceId}`, { exact: true }),
        ).toBeVisible();
        await expect(
          page.getByText(
            `Gespeicherter Cutoff: ${validation.evidence_cutoff_at}`,
            { exact: true },
          ),
        ).toBeVisible();
        await page.screenshot({
          path: testInfo.outputPath("S7-returned-A-governance-mobile.png"),
          fullPage: true,
        });
        const snapshots = [firstA, approvedOnlyA, secondB, thirdA];
        const stored = await evaluationHistory();
        expect(stored).toHaveLength(4);
        for (const snapshot of snapshots)
          expect(
            stored.find((value: { id: string }) => value.id === snapshot.id),
          ).toEqual(snapshot);
        // Follow the actual historical links and reload them. No latest fallback.
        const bLink = candidate.locator(
          `a[href="${candidateUrl}&evaluation=${secondB.id}"]`,
        );
        await expect(bLink).toHaveCount(1);
        await bLink.click();
        const bRegion = candidate.getByRole("region", {
          name: `Evaluation ${secondB.id}`,
          exact: true,
        });
        await expect(bRegion).toContainText("NOT_QUALIFIED");
        await expect(bRegion).toContainText(`Version ${versionB.version}`);
        await candidate.reload();
        await expect(bRegion).toContainText("NOT_QUALIFIED");
        await bRegion
          .getByText("Gespeicherte Analysequellen dieser Evaluation", {
            exact: true,
          })
          .click();
        for (const source of secondB.sources)
          await expect(bRegion).toContainText(source.source_id);
        await candidate.screenshot({
          path: testInfo.outputPath("S7-historical-B-desktop.png"),
          fullPage: true,
        });
        await candidate.setViewportSize({ width: 390, height: 844 });
        await candidate.screenshot({
          path: testInfo.outputPath("S7-historical-B-mobile.png"),
          fullPage: true,
        });
        await candidate
          .locator(`a[href="${candidateUrl}&evaluation=${firstA.id}"]`)
          .click();
        await expect(
          candidate.getByRole("region", {
            name: `Evaluation ${firstA.id}`,
            exact: true,
          }),
        ).toContainText("QUALIFIED");
        const versions = await q.getJson(
          `/model-governance/models/${modelId}/versions`,
        );
        expect(versions).toHaveLength(2);
        expect(
          versions.find((v: { id: string }) => v.id === versionA.id),
        ).toEqual(versionA);
        expect(
          versions.find((v: { id: string }) => v.id === versionB.id),
        ).toEqual(versionB);
        const lesson = await q.getJson(
          `/learning/lessons/${lessonId}/review-context`,
        );
        expect(lesson.lesson.current_version_id).toBe(l2);
        expect(
          lesson.history.find(
            (v: { version: { id: string } }) => v.version.id === l1,
          ).evidence_links,
        ).toEqual(setup.sourceChain.l1Snapshot.evidence_links);
        expect(
          await q.getJson(`/model-governance/lesson-versions/${l2}/hypotheses`),
        ).toEqual([]);
        const l1Hypotheses = await q.getJson(
          `/model-governance/lesson-versions/${l1}/hypotheses`,
        );
        expect(l1Hypotheses).toHaveLength(1);
        expect(l1Hypotheses[0]).toMatchObject({
          id: hypothesis.id,
          source_lesson_version_id: l1,
        });
        for (const analysis of setup.analyses)
          expect(
            await q.getJson(
              `/market-analyses/${analysis.analysis.id}/runs/${analysis.run.version}`,
            ),
          ).toEqual(analysis);
        return {
          lesson,
          l1Hypotheses,
          versions,
          evaluations: stored,
          currentActivation: await currentActivation(),
        };
      },
    );
    await q.record("B-CG-001-complete-source-version-chain", {
      setup: setup.sourceChain,
      hypothesis,
      proposal,
      validation,
      approval,
      activations: [setup.initialActivation, activationB, returnA],
      readinessBeforeSwitch,
      evaluations: [firstA, approvedOnlyA, secondB, thirdA],
      qualificationBoundary:
        "Native source prices VALID; existing FT006 result LIMITED. No GOOD, backtest or economic superiority claim.",
    });
  } finally {
    await q.finish();
  }
});
