import { randomUUID } from "node:crypto";
import { expect } from "@playwright/test";
import type {
  GovernedModelSummary,
  GovernedModelVersion,
} from "../../../frontend/src/features/model/types/hypothesisProposal";
import type {
  ApprovedModelVersion,
  ModelApprovalSummary,
} from "../../../frontend/src/features/model/types/proposalApproval";
import type { RuntimeActivation } from "../../../frontend/src/features/model/types/runtimeActivation";

type CommandMethod = "POST" | "PUT" | "PATCH";
type Role = "MARKET" | "SECTOR" | "UNDERLYING";
type Identified = { id: string };

export interface SeededPrices {
  mode: "learning" | "analyses" | "warning";
  start_date: string;
  end_date: string;
  row_count: number;
  listing_ids: string[];
  warning_rows: number;
  sources: Array<{
    analysis_id: string | null;
    listing_id: string | null;
    market_reference_id: string | null;
    instrument_id: string;
    provider_symbol: string;
  }>;
  synthetic: boolean;
}

export interface GovernanceSetupApi {
  runId: string;
  databaseState(): { fingerprint: string; [key: string]: unknown };
  command<T = Record<string, unknown>>(
    path: string,
    data?: object,
    method?: CommandMethod,
    headers?: Record<string, string>,
  ): Promise<T>;
  getJson<T = Record<string, unknown>>(path: string): Promise<T>;
  seedPrices(
    mode: "learning" | "analyses" | "warning",
    ...ids: string[]
  ): SeededPrices | Promise<SeededPrices>;
  record(name: string, body: unknown): void | Promise<void>;
}

interface Underlying {
  id: string;
  name: string;
  primary_listing: { id: string; ticker: string; currency_code: string };
}

interface Observation {
  id: string;
  trade_id: string;
  underlying_listing_id: string;
  status: string;
  available_observation_count: number;
  target_observation_count: number;
  is_complete: boolean;
}

interface Review {
  exit_review_id: string;
  current_version_id: string;
  status: string;
  currentness: string;
  rationale: string;
}

interface Lesson {
  lesson_id: string;
  current_version_id: string;
  version: number;
  current_state: string;
  content: string;
  evidence: Array<{ learning_evidence_id: string; relation: string }>;
  supersedes_version_id?: string;
}

export interface GovernanceEvidence {
  evidence_id: string;
  workspace_id: string;
  provenance_class: string;
  created_at: string;
  source: {
    type: string;
    trade_id: string;
    post_trade_observation_id: string;
    exit_review_id: string;
    exit_review_version_id: string;
  };
}

interface Reference {
  id: string;
  code: string;
  role: string;
  active: boolean;
  reference_type: string;
}

interface AnalysisRun {
  version: number;
  status: string;
  quality_status: string;
  model_id: string;
  model_version: string;
  observation_count: number;
  input_hash: string;
  analysis_time: string;
}

export interface GovernanceAnalysis {
  analysis: {
    id: string;
    underlying_id: string | null;
    listing_id: string | null;
    market_data_instrument_id: string;
  };
  run: AnalysisRun;
  parameters: Record<string, unknown>;
  metrics: Record<string, string | null>;
  notes: string[];
  criteria: Array<{ code: string; classification: string }>;
  snapshot: Array<{
    trading_date: string;
    close: string;
    adjusted_close: string | null;
    quality_status: string;
    provider_symbol: string;
    warnings: string[];
  }>;
}

const analysisParameters = {
  price_field: "ADJUSTED_CLOSE",
  short_window: 20,
  medium_window: 50,
  long_window: 200,
  momentum_windows: [20, 60, 120],
  volatility_window: 20,
  range_window: 52,
  minimum_required_observations: 200,
  maximum_data_age_days: 7,
  annualization_factor: "252",
  rounding_scale: 6,
};

const completeVerification = {
  verified: true,
  model_available: true,
  input_hash_matches: true,
  metrics_match: true,
  criteria_match: true,
  quality_status_match: true,
  notes_match: true,
};

export const candidatePolicyA = {
  schema: "TOP_DOWN_CANDIDATE/2.0",
  direction: "LONG",
  market_context_allowed: ["FAVORABLE", "CAUTIOUS"],
};

// The caller verifies the fresh stack before entry and owns every guarded HTTP
// request. Only past price rows are a fixture. No governance step from S2 onward
// and no Candidate evaluation is performed by this explicitly marked setup.
export async function createGovernanceSetup(api: GovernanceSetupApi) {
  const suffix = randomUUID();
  const prefix = `Candidate Governance CI ${api.runId} `;
  const actor = {
    "X-Actor-ID": `candidate-governance:${api.runId}`,
    "X-Actor-Name": "Synthetic candidate governance CI",
  };
  const venues = await api.getJson<{
    items: Array<{ id: string; mic: string }>;
  }>("/market-reference-data/trading-venues");
  const venue = venues.items.find((item) => item.mic === "XETR");
  if (!venue)
    throw new Error(
      "The isolated target must contain the XETR reference venue",
    );
  const underlyingInput = (role: string, ticker: string) => ({
    name: `${prefix}${role} ${suffix}`,
    type: "STOCK",
    primary_listing: {
      trading_venue_id: venue.id,
      ticker,
      currency_code: "EUR",
    },
  });

  // The known global issuer audit is verified with its unique warrant after this
  // three-command group; it is deliberately not exempted for unrelated writes.
  const issuer = await api.command<Identified>(
    "/market-reference-data/issuers",
    {
      legal_name: `${prefix}${suffix}`,
      display_name: "Synthetic candidate governance CI",
    },
    "POST",
    actor,
  );
  const createdLearningUnderlying = await api.command<Identified>(
    "/underlyings",
    underlyingInput("Learning", `CGL${suffix.slice(0, 8)}`),
  );
  const warrant = await api.command<Identified>("/warrants", {
    issuer_id: issuer.id,
    underlying_id: createdLearningUnderlying.id,
    display_name: `${prefix}Learning Call ${suffix}`,
    option_direction: "CALL",
    strike: "100",
    strike_currency_code: "EUR",
    maturity_date: "2099-12-31",
    ratio: "0.1",
  });
  const learningUnderlying = await api.getJson<Underlying>(
    `/underlyings/${createdLearningUnderlying.id}`,
  );
  expect(learningUnderlying.primary_listing.currency_code).toBe("EUR");
  // The mapping owner creates the neutral instrument identity required by the
  // guarded price fixture. This learning-only mapping remains DISABLED.
  const learningMapping = await api.command<Record<string, unknown>>(
    "/market-data/provider-mappings",
    {
      listing_id: learningUnderlying.primary_listing.id,
      provider: "EODHD",
      provider_symbol: `SYNTHETIC-CG-LEARNING-${suffix.slice(0, 8)}`,
      provider_exchange_code: "XETRA",
      actor_id: actor["X-Actor-ID"],
      actor_name: actor["X-Actor-Name"],
    },
    "PUT",
  );
  expect(learningMapping).toMatchObject({
    listing_id: learningUnderlying.primary_listing.id,
    status: "DISABLED",
  });
  const capture = (price: string, day: string) => ({
    quantity: 10,
    price_per_unit: price,
    executed_on: day,
    execution_timezone: "Europe/Berlin",
    request_id: randomUUID(),
  });
  const buy = await api.command<{ trade: Identified; execution: Identified }>(
    "/trade-position/purchases/external",
    {
      product_id: warrant.id,
      ...capture("0.55", "2026-08-17"),
      currency_confirmation: {
        currency_code: "EUR",
        source: "USER_CONFIRMED",
        note: "Synthetic candidate governance qualification, no real trade.",
      },
    },
  );
  const tradeId = buy.trade.id;
  const sale = await api.command<{
    execution: Identified;
    position: { is_closed: boolean };
  }>(`/trade-position/trades/${tradeId}/sales`, capture("0.65", "2026-08-18"));
  expect(sale.position.is_closed).toBe(true);
  const observation = await api.command<Observation>(
    `/post-trade/trades/${tradeId}/observation`,
  );
  expect(observation.underlying_listing_id).toBe(
    learningUnderlying.primary_listing.id,
  );
  const learningPrices = await api.seedPrices(
    "learning",
    tradeId,
    observation.underlying_listing_id,
  );
  expect(learningPrices).toMatchObject({
    mode: "learning",
    row_count: 20,
    synthetic: true,
  });
  // This GET refreshes persisted observation state. It is setup, outside every
  // fingerprinted read window, and must not be described as a pure read.
  const refreshed = await api.getJson<Observation>(
    `/post-trade/trades/${tradeId}/observation`,
  );
  expect(refreshed).toMatchObject({
    id: observation.id,
    trade_id: tradeId,
    underlying_listing_id: observation.underlying_listing_id,
    status: "COMPLETED",
    is_complete: true,
    available_observation_count: 20,
  });
  const draftReview = await api.command<Review>(
    `/post-trade/trades/${tradeId}/exit-review`,
  );
  const savedReview = await api.command<Review>(
    `/post-trade/trades/${tradeId}/exit-review/draft`,
    {
      timing: "NOT_ASSESSABLE",
      process_adherence: "GOOD",
      risk_decision: "ACCEPTABLE",
      overall_exit_decision: "GOOD",
      rationale:
        "Bewusster synthetischer Befund für den Governanceweg; kein Performancenachweis.",
    },
    "PUT",
  );
  expect(savedReview.current_version_id).toBe(draftReview.current_version_id);
  const review = await api.command<Review>(
    `/post-trade/trades/${tradeId}/exit-review/finalize`,
  );
  expect(review).toMatchObject({
    current_version_id: draftReview.current_version_id,
    status: "FINALIZED",
    currentness: "CURRENT",
  });
  const materialization = await api.command<{
    learning_evidence_id: string;
    exit_review_version_id: string;
    created: boolean;
    replayed: boolean;
  }>(
    `/learning/trades/${tradeId}/ft011-evidence/materialize`,
    { expected_exit_review_version_id: review.current_version_id },
    "POST",
    { "Idempotency-Key": randomUUID() },
  );
  expect(materialization).toMatchObject({
    exit_review_version_id: review.current_version_id,
    created: true,
    replayed: false,
  });
  const evidenceId = materialization.learning_evidence_id;
  const evidence = await api.getJson<GovernanceEvidence>(
    `/learning/learning-evidence/${evidenceId}`,
  );
  expect(evidence).toMatchObject({
    evidence_id: evidenceId,
    provenance_class: "FT011",
    source: {
      type: "FT011",
      trade_id: tradeId,
      post_trade_observation_id: observation.id,
      exit_review_id: review.exit_review_id,
      exit_review_version_id: review.current_version_id,
    },
  });
  const originalLesson = await api.command<Lesson>("/learning/lessons", {
    title: "Synthetische Candidate-Governance-Lesson",
    main_category: "Prozess",
    content:
      "L1: Bewusste synthetische Quelle zur technischen Steuerbarkeit der bestehenden Candidate-Policy.",
    tags: [],
    evidence_links: [
      { learning_evidence_id: evidenceId, relation: "SUPPORTS" },
    ],
  });
  const lessonId = originalLesson.lesson_id;
  const l1 = originalLesson.current_version_id;
  expect(originalLesson).toMatchObject({
    version: 1,
    current_state: "CURRENT",
  });
  const laterLesson = await api.command<Lesson>(
    `/learning/lessons/${lessonId}/versions`,
    {
      expected_current_version_id: l1,
      expected_current_state: "CURRENT",
      main_category: "Prozess",
      content:
        "L2: Spätere getrennte synthetische Interpretation; ersetzt keine bewusste Bindung an L1.",
      evidence_links: [
        { learning_evidence_id: evidenceId, relation: "SUPPORTS" },
      ],
    },
  );
  const l2 = laterLesson.current_version_id;
  expect(l2).not.toBe(l1);
  expect(laterLesson).toMatchObject({ version: 2, supersedes_version_id: l1 });
  const lessonHistory = await api.getJson<{
    lesson_id: string;
    versions: Array<{
      version_id: string;
      version: number;
      content: string;
      evidence: Array<{ learning_evidence_id: string; relation: string }>;
    }>;
  }>(`/learning/lessons/${lessonId}/history`);
  expect(lessonHistory.versions).toHaveLength(2);
  expect(
    lessonHistory.versions.find((item) => item.version_id === l1),
  ).toMatchObject({
    version: 1,
    content: originalLesson.content,
    evidence: [{ learning_evidence_id: evidenceId, relation: "SUPPORTS" }],
  });
  const lessonContext = await api.getJson<{
    history: Array<{
      version: { id: string; content: string };
      evidence_links: Array<{ learning_evidence_id: string; relation: string }>;
    }>;
  }>(`/learning/lessons/${lessonId}/review-context`);
  const l1Snapshot = lessonContext.history.find(
    (item) => item.version.id === l1,
  );
  if (!l1Snapshot)
    throw new Error("The exact owner-created Lesson L1 is missing");
  expect(l1Snapshot.evidence_links).toMatchObject([
    { learning_evidence_id: evidenceId, relation: "SUPPORTS" },
  ]);
  const sourceChain = {
    synthetic: true,
    issuer,
    learningUnderlying,
    learningMapping,
    warrant,
    buy,
    sale,
    observation,
    learningPrices,
    refreshed,
    review,
    materialization,
    evidence,
    originalLesson,
    laterLesson,
    lessonHistory,
    l1Snapshot,
  };
  await api.record("S0-learning-owner-source-chain", sourceChain);

  const referenceBase = "/top-down-reference-data";
  const references = await api.command<Reference[]>(
    `${referenceBase}/bootstrap-v1`,
  );
  const broadMarket = references.find((item) => item.code === "DAX");
  if (!broadMarket) throw new Error("The explicit V1 DAX reference is missing");
  expect(broadMarket).toMatchObject({ role: "BROAD_MARKET", active: true });
  const sectorReference = await api.command<Reference>(
    `${referenceBase}/sector-references`,
    {
      code: `CG-SECTOR-${suffix.slice(0, 8)}`,
      name: `${prefix}Synthetic sector reference`,
      region: "SYNTHETIC",
      reference_version: "SYNTHETIC-CANDIDATE-GOVERNANCE",
    },
  );
  expect(sectorReference).toMatchObject({
    reference_type: "SECTOR_INDEX",
    active: true,
  });
  const sector = await api.command<Identified>(`${referenceBase}/sectors`, {
    code: `CG-${suffix.slice(0, 8)}`,
    name: `${prefix}Synthetic sector`,
    classification_system: "SYNTHETIC-CANDIDATE-GOVERNANCE",
    classification_version: "1",
  });
  const analysisActor = { "X-Actor-Name": `candidate-governance:${api.runId}` };
  const sourceOwners: Array<{
    role: Role;
    analysis_id: string;
    run_path: string;
    market_data_instrument_id: string;
    market_reference_id: string | null;
    underlying_id: string | null;
    listing_id: string | null;
  }> = [];
  for (const [role, reference] of [
    ["MARKET", broadMarket],
    ["SECTOR", sectorReference],
  ] as const) {
    const created = await api.command<{
      analysis_id: string;
      market_reference_id: string;
      market_data_instrument_id: string;
    }>(
      `${referenceBase}/market-references/${reference.id}/analyses`,
      undefined,
      "POST",
      analysisActor,
    );
    expect(created.market_reference_id).toBe(reference.id);
    expect(created.market_data_instrument_id).toBeTruthy();
    sourceOwners.push({
      role,
      ...created,
      run_path: `${referenceBase}/market-reference-analyses/${created.analysis_id}/runs`,
      underlying_id: null,
      listing_id: null,
    });
  }
  const createListingSource = async (role: string) => {
    const createdUnderlying = await api.command<Identified>(
      "/underlyings",
      underlyingInput(role, `CG${role.slice(0, 1)}${suffix.slice(0, 8)}`),
    );
    const underlying = await api.getJson<Underlying>(
      `/underlyings/${createdUnderlying.id}`,
    );
    expect(underlying.primary_listing.currency_code).toBe("EUR");
    const mapping = await api.command<
      Identified & { market_data_instrument_id: string }
    >(
      "/market-data/provider-mappings",
      {
        listing_id: underlying.primary_listing.id,
        provider: "EODHD",
        provider_symbol: `SYNTHETIC-CG-${role}-${suffix.slice(0, 8)}`,
        provider_exchange_code: "XETRA",
        actor_id: actor["X-Actor-ID"],
        actor_name: actor["X-Actor-Name"],
      },
      "PUT",
    );
    // No provider validate/import endpoint is called. This existing state command
    // is only for the real underlying listing, never a market/sector substitute.
    const activeMapping = await api.command<Record<string, unknown>>(
      `/market-data/provider-mappings/${mapping.id}/state`,
      {
        enabled: true,
        actor_id: actor["X-Actor-ID"],
        actor_name: actor["X-Actor-Name"],
      },
      "PATCH",
    );
    expect(activeMapping).toMatchObject({
      id: mapping.id,
      status: "ACTIVE",
      validation_message: "Activated administratively",
    });
    const analysis = await api.command<Identified>(
      "/market-analyses",
      {
        underlying_id: underlying.id,
        listing_id: underlying.primary_listing.id,
      },
      "POST",
      analysisActor,
    );
    return { underlying, mapping, activeMapping, analysis };
  };
  const underlyingSource = await createListingSource("UNDERLYING");
  sourceOwners.push({
    role: "UNDERLYING",
    analysis_id: underlyingSource.analysis.id,
    run_path: `/market-analyses/${underlyingSource.analysis.id}/runs`,
    market_data_instrument_id:
      underlyingSource.mapping.market_data_instrument_id,
    market_reference_id: null,
    underlying_id: underlyingSource.underlying.id,
    listing_id: underlyingSource.underlying.primary_listing.id,
  });
  const prices = await api.seedPrices(
    "analyses",
    ...sourceOwners.map((item) => item.analysis_id),
  );
  expect(prices).toMatchObject({
    mode: "analyses",
    row_count: 600,
    warning_rows: 0,
    synthetic: true,
  });
  expect(prices.sources).toHaveLength(3);
  expect(prices.listing_ids).toEqual([
    underlyingSource.underlying.primary_listing.id,
  ]);
  const analyses: GovernanceAnalysis[] = [];
  const legacyAnalyses: GovernanceAnalysis[] = [];
  const analysisRefs = {} as Record<
    Role,
    { analysis_id: string; version: number }
  >;
  const detailsFor = (analysisId: string, version: number) =>
    api.getJson<GovernanceAnalysis>(
      `/market-analyses/${analysisId}/runs/${version}`,
    );
  let verificationCount = 0;
  const verify = async (details: GovernanceAnalysis) => {
    const before = api.databaseState();
    const result = await api.command(
      `/market-analyses/${details.analysis.id}/runs/${details.run.version}/verify`,
    );
    expect(result).toEqual(completeVerification);
    const after = api.databaseState();
    expect(after.fingerprint).toBe(before.fingerprint);
    await api.record(`S0-read-only-verification-${++verificationCount}`, {
      analysis_id: details.analysis.id,
      run_version: details.run.version,
      model_id: details.run.model_id,
      model_version: details.run.model_version,
      before,
      result,
      after,
    });
    return result;
  };
  const insufficientCases = [];
  for (const [index, owner] of sourceOwners.entries()) {
    expect(prices.sources[index]).toMatchObject({
      analysis_id: owner.analysis_id,
      instrument_id: owner.market_data_instrument_id,
      market_reference_id: owner.market_reference_id,
      listing_id: owner.listing_id,
    });
    const runInput = {
      start_date: prices.start_date,
      end_date: prices.end_date,
      parameters: analysisParameters,
    };
    // The legacy object is genuinely executed first, before the new runtime is
    // selected, and is retained unchanged after all four Candidate evaluations.
    const legacyRun = await api.command<AnalysisRun>(owner.run_path, {
      ...runInput,
      model_version: "1.0.0",
    });
    const legacy = await detailsFor(owner.analysis_id, legacyRun.version);
    expect(legacy.run).toMatchObject({
      status: "COMPLETED_WITH_WARNINGS",
      quality_status: "LIMITED",
      model_id: "EOD_TREND_MOMENTUM",
      model_version: "1.0.0",
      observation_count: 200,
    });
    expect(legacy.parameters).toEqual(analysisParameters);
    expect(legacy.snapshot.every((row) => row.quality_status === "VALID")).toBe(
      true,
    );
    expect(legacy.snapshot.every((row) => row.warnings.length === 0)).toBe(
      true,
    );
    await verify(legacy);
    legacyAnalyses.push(legacy);

    if (owner.role === "UNDERLYING") {
      // Both runtime contracts must keep a truly incomplete saved snapshot
      // incomplete even though the owner already stores all 200 current prices.
      for (const modelVersion of ["1.0.0", "1.0.1"]) {
        const incompleteRun = await api.command<AnalysisRun>(owner.run_path, {
          ...runInput,
          start_date: legacy.snapshot[181].trading_date,
          model_version: modelVersion,
        });
        const incomplete = await detailsFor(
          owner.analysis_id,
          incompleteRun.version,
        );
        expect(incomplete.run).toMatchObject({
          status: "NOT_EVALUABLE",
          quality_status: "INSUFFICIENT",
          model_version: modelVersion,
          observation_count: 19,
        });
        const retry = await api.command<AnalysisRun>(
          `/market-analyses/${owner.analysis_id}/runs/${incompleteRun.version}/retry`,
          {
            reason:
              "Synthetic qualification of the exact saved incomplete snapshot",
          },
        );
        const retried = await detailsFor(owner.analysis_id, retry.version);
        expect(retried.run).toMatchObject({
          status: "NOT_EVALUABLE",
          quality_status: "INSUFFICIENT",
          model_version: modelVersion,
          observation_count: 19,
          input_hash: incomplete.run.input_hash,
        });
        expect(retried.snapshot).toEqual(incomplete.snapshot);
        expect(retried.parameters).toEqual(incomplete.parameters);
        expect(retried.metrics).toEqual(incomplete.metrics);
        expect(retried.criteria).toEqual(incomplete.criteria);
        expect(retried.notes).toEqual(incomplete.notes);
        await verify(incomplete);
        await verify(retried);
        insufficientCases.push({ incomplete, retried });
      }
    }
    const run = await api.command<AnalysisRun>(owner.run_path, {
      ...runInput,
      model_version: "1.0.1",
    });
    const details = await detailsFor(owner.analysis_id, run.version);
    expect(details.analysis).toMatchObject({
      id: owner.analysis_id,
      underlying_id: owner.underlying_id,
      listing_id: owner.listing_id,
      market_data_instrument_id: owner.market_data_instrument_id,
    });
    expect(details.run).toMatchObject({
      version: run.version,
      status: "COMPLETED",
      quality_status: "GOOD",
      model_id: "EOD_TREND_MOMENTUM",
      model_version: "1.0.1",
      observation_count: 200,
      input_hash: run.input_hash,
    });
    expect(details.run.input_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(details.run.input_hash).not.toBe(legacy.run.input_hash);
    expect(details.parameters).toEqual(analysisParameters);
    expect(details.snapshot).toEqual(legacy.snapshot);
    expect(details.metrics).toEqual(legacy.metrics);
    expect(details.criteria).toEqual(legacy.criteria);
    expect(details.notes).toEqual([]);
    expect(details.snapshot).toHaveLength(200);
    expect(
      details.snapshot.every((row) => row.quality_status === "VALID"),
    ).toBe(true);
    expect(details.snapshot.every((row) => row.warnings.length === 0)).toBe(
      true,
    );
    expect(
      details.snapshot.every(
        (row) => row.provider_symbol === prices.sources[index].provider_symbol,
      ),
    ).toBe(true);
    expect(details.snapshot[0].trading_date).toBe(prices.start_date);
    expect(details.snapshot[199].trading_date).toBe(prices.end_date);
    const ageDays = Math.floor(
      Date.parse(details.run.analysis_time.slice(0, 10)) / 86_400_000 -
        Date.parse(prices.end_date) / 86_400_000,
    );
    expect(ageDays).toBeGreaterThanOrEqual(1);
    expect(ageDays).toBeLessThanOrEqual(
      analysisParameters.maximum_data_age_days,
    );
    for (const code of ["SHORT_TREND", "MEDIUM_TREND", "LONG_TREND"]) {
      expect(
        details.criteria.find((item) => item.code === code)?.classification,
      ).toBe(index === 0 && code === "SHORT_TREND" ? "NEGATIVE" : "POSITIVE");
    }
    await verify(details);
    expect(await detailsFor(owner.analysis_id, legacy.run.version)).toEqual(
      legacy,
    );
    await verify(legacy);
    analyses.push(details);
    analysisRefs[owner.role] = {
      analysis_id: owner.analysis_id,
      version: run.version,
    };
  }
  expect(new Set(analyses.map((item) => item.analysis.id)).size).toBe(3);
  for (const analysis of analyses.slice(1)) {
    expect(analysis.snapshot.map((row) => row.trading_date)).toEqual(
      analyses[0].snapshot.map((row) => row.trading_date),
    );
    expect(analysis.parameters).toEqual(analyses[0].parameters);
  }

  // A distinct source preserves the independent LIMITED negative contract; its
  // actual saved warning is never removed from the price or snapshot.
  const warningSource = await createListingSource("WARNING");
  const warningPrices = await api.seedPrices(
    "warning",
    warningSource.analysis.id,
  );
  expect(warningPrices).toMatchObject({
    row_count: 200,
    warning_rows: 1,
    synthetic: true,
  });
  const warningRun = await api.command<AnalysisRun>(
    `/market-analyses/${warningSource.analysis.id}/runs`,
    {
      start_date: warningPrices.start_date,
      end_date: warningPrices.end_date,
      model_version: "1.0.1",
      parameters: analysisParameters,
    },
  );
  const warningAnalysis = await detailsFor(
    warningSource.analysis.id,
    warningRun.version,
  );
  expect(warningAnalysis.run).toMatchObject({
    status: "COMPLETED_WITH_WARNINGS",
    quality_status: "LIMITED",
    model_version: "1.0.1",
    observation_count: 200,
  });
  const warning = "Synthetic qualification: source warning must remain visible";
  expect(warningAnalysis.snapshot[199].warnings).toEqual([warning]);
  expect(warningAnalysis.notes).toContain(
    `${warningPrices.end_date}: source warning: ${warning}`,
  );
  await verify(warningAnalysis);
  await api.record(
    "S0-independent-LIMITED-INSUFFICIENT-and-legacy-regressions",
    {
      legacyAnalyses,
      insufficientCases,
      warningSource,
      warningPrices,
      warningAnalysis,
    },
  );
  const assignment = {
    valid_from: prices.start_date,
    source: "SYNTHETIC_CANDIDATE_GOVERNANCE",
    source_reference: `candidate-governance:${api.runId}`,
    quality_status: "GOOD",
  };
  const assignments = [
    await api.command(
      `${referenceBase}/underlyings/${underlyingSource.underlying.id}/benchmark-assignments`,
      {
        ...assignment,
        market_reference_id: broadMarket.id,
        role: "BROAD_MARKET",
      },
    ),
    await api.command(
      `${referenceBase}/underlyings/${underlyingSource.underlying.id}/sector-assignments`,
      { ...assignment, sector_id: sector.id },
    ),
    await api.command(
      `${referenceBase}/sectors/${sector.id}/reference-assignments`,
      { ...assignment, market_reference_id: sectorReference.id },
    ),
  ];
  const candidate = await api.command<Identified>("/candidates", {
    underlying_id: underlyingSource.underlying.id,
  });
  await api.record("S0-analysis-owner-source-chain", {
    synthetic: true,
    sourceOwners,
    underlyingSource,
    prices,
    analysisRefs,
    analyses,
    references,
    broadMarket,
    sectorReference,
    sector,
    assignments,
    candidate,
    quality_boundary:
      "Explicit FT006 1.0.1: VALID original sources with no warnings produce GOOD. Real reference identities; 200 completed weekdays, not certified exchange-calendar coverage.",
  });

  expect(await api.getJson("/model-governance/models")).toEqual([]);
  const initial = await api.command<{
    model: GovernedModelSummary;
    initial_version: GovernedModelVersion;
  }>("/model-governance/models", {
    model_key: "TOP_DOWN_CANDIDATE",
    name: `${prefix}Synthetic Candidate`,
    purpose:
      "Synthetic technical A→B→A controllability; no financial superiority claim.",
    initial_definition: candidatePolicyA,
  });
  expect(initial.initial_version).toMatchObject({
    version: 1,
    status: "DRAFT",
    definition: candidatePolicyA,
  });
  const modelId = initial.model.id;
  const initialApproval = await api.command<ModelApprovalSummary>(
    `/model-governance/models/${modelId}/versions/${initial.initial_version.id}/approve`,
    undefined,
    "POST",
    {
      "X-Correlation-ID": `candidate-governance:${api.runId}:initial-approval`,
    },
  );
  expect(initialApproval).toMatchObject({
    proposal_id: null,
    model_version_id: initial.initial_version.id,
  });
  const versions = await api.getJson<GovernedModelVersion[]>(
    `/model-governance/models/${modelId}/versions`,
  );
  expect(versions).toHaveLength(1);
  expect(versions[0]).toMatchObject({
    id: initial.initial_version.id,
    model_id: modelId,
    version: 1,
    status: "APPROVED",
    definition: candidatePolicyA,
    previous_version_id: null,
  });
  const versionA = versions[0] as ApprovedModelVersion;
  expect(
    await api.getJson(`/model-governance/models/${modelId}/runtime-activation`),
  ).toBeNull();
  const initialActivation = await api.command<RuntimeActivation>(
    `/model-governance/models/${modelId}/versions/${versionA.id}/activate`,
    undefined,
    "POST",
    {
      "X-Correlation-ID": `candidate-governance:${api.runId}:initial-activation`,
    },
  );
  expect(initialActivation).toMatchObject({
    model_id: modelId,
    model_version_id: versionA.id,
    model_version: versionA,
  });
  expect(
    await api.getJson(`/model-governance/models/${modelId}/runtime-activation`),
  ).toEqual(initialActivation);
  expect(await api.getJson(`/candidates/${candidate.id}/evaluations`)).toEqual(
    [],
  );
  expect(
    await api.getJson(`/model-governance/lesson-versions/${l1}/hypotheses`),
  ).toEqual([]);
  expect(
    await api.getJson(`/model-governance/lesson-versions/${l2}/hypotheses`),
  ).toEqual([]);
  await api.record("S1-explicit-initial-model-activation", {
    initial,
    initialApproval,
    versionA,
    initialActivation,
  });
  return {
    modelId,
    versionA,
    initialApproval,
    initialActivation,
    lessonId,
    l1,
    l2,
    evidence,
    evidenceId,
    candidateId: candidate.id,
    analysisRefs,
    analyses,
    legacyAnalyses,
    sourceOwners,
    sourceChain,
  };
}
