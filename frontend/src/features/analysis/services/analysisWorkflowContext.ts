import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow, CandidateLiveWorkflowStep } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import type { AnalysisDetail, AnalysisRunDetail, AnalysisSummary } from '../types/api';
import { analysisApiClient } from './client';

export interface AnalysisSetupContext {
  analysisId: string;
  underlyingId: string;
  listingId: string;
  instrumentId: string;
  candidateId: string;
  evaluationId: string;
  sourceVersion: number | null;
  workflowAction: 'RUN_MARKET_ANALYSIS' | null;
  stepCode: string;
  resourceId: string;
  actionParams: Record<string, string>;
  overviewContext: string;
  returnTo: string;
  key: string;
}

export interface ResolvedAnalysisSetupContext {
  context: AnalysisSetupContext;
  detail: AnalysisDetail | null;
  underlying: UnderlyingDetailResponse | null;
  listing: ListingResponse | null;
  source: AnalysisRunDetail | null;
  workflow: CandidateLiveWorkflow | null;
  workflowStep: CandidateLiveWorkflowStep | null;
  returnTo: string;
}

const identityParameters = {
  analysis_id: 'analysisId',
  underlying_id: 'underlyingId',
  listing_id: 'listingId',
  market_data_instrument_id: 'instrumentId',
} as const;

function uniqueParameter(params: URLSearchParams, name: string): string {
  const values = [...new Set(params.getAll(name).map((value) => value.trim()))];
  if (values.length > 1) throw new Error(`Widersprüchliche Angaben für ${name}.`);
  return values[0] ?? '';
}

function identifierParameter(params: URLSearchParams, name: string): string {
  const value = uniqueParameter(params, name);
  if (params.has(name) && !value)
    throw new Error(`Die ausdrücklich übergebene Kennung ${name} ist leer.`);
  return requireIdentifier(value, name);
}

function mergeIdentity(current: string, incoming: string, name: string): string {
  if (current && incoming && current !== incoming)
    throw new Error(`Widersprüchliche ${name}. Der Analyseauftrag bleibt gesperrt.`);
  return current || incoming;
}

function requireIdentifier(value: string, name: string): string {
  if (value && !/^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(value))
    throw new Error(`Die Kennung ${name} ist nicht eindeutig lesbar.`);
  return value;
}

function parseActionParams(params: URLSearchParams): Record<string, string> {
  const raw = uniqueParameter(params, 'action_params');
  if (!params.has('action_params')) return {};
  let value: unknown;
  try {
    value = JSON.parse(raw) as unknown;
  } catch {
    throw new Error('Die Analyse-Aktionsparameter sind nicht lesbar. Bitte den Link neu öffnen.');
  }
  if (
    !value ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    Object.values(value).some((item) => typeof item !== 'string')
  )
    throw new Error('Die Analyse-Aktionsparameter müssen eindeutige Textwerte enthalten.');
  return Object.fromEntries(
    Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, (item as string).trim()]),
  );
}

/** Only existing overview filters may participate in an internal return route. */
export function sanitizeOverviewContext(value: string): string {
  const source = new URLSearchParams(value);
  const result = new URLSearchParams();
  for (const name of [
    'offset',
    'underlying_id',
    'status',
    'quality_status',
    'analysis_time_from',
    'analysis_time_to',
    'sort_by',
    'sort_direction',
  ]) {
    const item = uniqueParameter(source, name);
    if (item) result.set(name, item);
  }
  return result.toString();
}

function detailReturnParams(context: Partial<AnalysisSetupContext>): URLSearchParams {
  const params = new URLSearchParams();
  if (context.candidateId) {
    params.set('candidate_id', context.candidateId);
    if (context.evaluationId) params.set('evaluation_id', context.evaluationId);
  }
  const overview = sanitizeOverviewContext(context.overviewContext ?? '');
  if (overview) params.set('overview_context', overview);
  return params;
}

export function analysisDetailUrl(
  id: string,
  version?: number | null,
  context: Partial<AnalysisSetupContext> = {},
): string {
  if (!requireIdentifier(id, 'analysis_id')) throw new Error('Die Analysekennung fehlt.');
  const params = detailReturnParams(context);
  if (version !== undefined && version !== null) {
    if (!Number.isSafeInteger(version) || version < 1)
      throw new Error('Die Analyseversion muss eine positive ganze Zahl sein.');
    params.set('version', String(version));
  }
  return `/market-analyses/${encodeURIComponent(id)}${params.size ? `?${params.toString()}` : ''}`;
}

export function analysisContextReturnTo(context: Partial<AnalysisSetupContext>): string {
  if (context.candidateId) {
    const params = new URLSearchParams({ candidate: context.candidateId });
    if (context.evaluationId) params.set('evaluation', context.evaluationId);
    return `/candidates?${params.toString()}`;
  }
  if (context.analysisId)
    return analysisDetailUrl(context.analysisId, context.sourceVersion, {
      overviewContext: context.overviewContext,
    });
  const overview = sanitizeOverviewContext(context.overviewContext ?? '');
  return `/market-analyses${overview ? `?${overview}` : ''}`;
}

function sealContext(context: AnalysisSetupContext): AnalysisSetupContext {
  context.returnTo = analysisContextReturnTo(context);
  context.key = JSON.stringify({ ...context, key: undefined });
  return context;
}

/** Parse once. No query parameter may supply a free return URL or redefine an owner. */
export function parseAnalysisSetupContext(params: URLSearchParams): AnalysisSetupContext {
  const action = uniqueParameter(params, 'action');
  if (action && action !== 'RUN_MARKET_ANALYSIS')
    throw new Error(`Unbekannte Analyseaktion: ${action}.`);
  const actionParams = parseActionParams(params);
  const context: AnalysisSetupContext = {
    analysisId: '',
    underlyingId: '',
    listingId: '',
    instrumentId: '',
    candidateId: identifierParameter(params, 'candidate_id'),
    evaluationId: identifierParameter(params, 'evaluation_id'),
    sourceVersion: null,
    workflowAction: action === 'RUN_MARKET_ANALYSIS' ? action : null,
    stepCode: uniqueParameter(params, 'step_code'),
    resourceId: identifierParameter(params, 'resource_id'),
    actionParams,
    overviewContext: sanitizeOverviewContext(uniqueParameter(params, 'overview_context')),
    returnTo: '',
    key: '',
  };
  for (const [parameter, property] of Object.entries(identityParameters)) {
    if (Object.prototype.hasOwnProperty.call(actionParams, parameter) && !actionParams[parameter])
      throw new Error(`Die ausdrücklich übergebene Aktionskennung ${parameter} ist leer.`);
    context[property] = requireIdentifier(
      mergeIdentity(
        identifierParameter(params, parameter),
        actionParams[parameter] ?? '',
        parameter,
      ),
      parameter,
    );
  }
  const version = uniqueParameter(params, 'source_version');
  if (params.has('source_version')) {
    if (!/^[1-9][0-9]*$/.test(version) || !Number.isSafeInteger(Number(version)))
      throw new Error('Die Quellversion muss eine positive ganze Zahl sein.');
    if (!context.analysisId) throw new Error('Die Quellversion benötigt eine konkrete Analyse.');
    context.sourceVersion = Number(version);
  }
  if (context.evaluationId && !context.candidateId)
    throw new Error('Der Rückweg zur Evaluation benötigt eine konkrete Candidate-ID.');
  if (context.workflowAction) {
    if (!context.candidateId)
      throw new Error('Der Analyse-Reparaturauftrag benötigt einen konkreten Kandidaten.');
    context.listingId = mergeIdentity(context.listingId, context.resourceId, 'Listingkennung');
    if (!context.listingId)
      throw new Error('Die Listingkennung des konkreten Analyse-Schritts fehlt.');
  } else if (context.resourceId || context.stepCode || Object.keys(actionParams).length) {
    throw new Error('Workflow-Parameter benötigen die ausdrückliche Analyseaktion.');
  } else if (context.candidateId && !context.analysisId) {
    throw new Error(
      'Der Candidate-Kontext benötigt eine Analyse oder einen konkreten Workflow-Schritt.',
    );
  }
  if (!context.analysisId && context.instrumentId)
    throw new Error(
      'Eine direkte Referenzanalyse muss über ihre bestehende Analyse geöffnet werden.',
    );
  return sealContext(context);
}

export function canonicalAnalysisSetupUrl(context: Partial<AnalysisSetupContext> = {}): string {
  const params = detailReturnParams(context);
  for (const [parameter, property] of Object.entries(identityParameters)) {
    if (context[property]) params.set(parameter, context[property]);
  }
  if (context.sourceVersion !== undefined && context.sourceVersion !== null)
    params.set('source_version', String(context.sourceVersion));
  if (context.workflowAction) params.set('action', context.workflowAction);
  if (context.resourceId) params.set('resource_id', context.resourceId);
  if (context.stepCode) params.set('step_code', context.stepCode);
  if (context.actionParams && Object.keys(context.actionParams).length)
    params.set('action_params', JSON.stringify(context.actionParams));
  // Validate constructed links using the same contract as incoming legacy links.
  parseAnalysisSetupContext(params);
  return `/market-analyses/setup${params.size ? `?${params.toString()}` : ''}`;
}

function stepIdentities(step: CandidateLiveWorkflowStep) {
  const params = step.action_params ?? {};
  return {
    underlyingId: params.underlying_id ?? '',
    listingId: mergeIdentity(
      params.listing_id ?? '',
      step.resource_id ?? '',
      'Workflow-Listingkennung',
    ),
  };
}

function matchingStep(
  context: AnalysisSetupContext,
  workflow: CandidateLiveWorkflow,
): CandidateLiveWorkflowStep | null {
  const matches = workflow.steps.filter((step) => {
    if (
      step.status !== 'BLOCKED' ||
      step.action !== 'RUN_MARKET_ANALYSIS' ||
      (context.stepCode && step.code !== context.stepCode) ||
      (context.resourceId && step.resource_id !== context.resourceId)
    )
      return false;
    const expected = stepIdentities(step);
    if (
      expected.listingId !== context.listingId ||
      (context.underlyingId && expected.underlyingId !== context.underlyingId)
    )
      return false;
    return Object.entries(context.actionParams).every(([name, value]) => {
      if (name === 'listing_id') return value === expected.listingId;
      if (name === 'underlying_id') return value === expected.underlyingId;
      return value === step.action_params?.[name];
    });
  });
  if (matches.length > 1)
    throw new Error(
      'Mehrere blockierte Analyse-Schritte passen zum Link. Bitte den konkreten Schritt neu öffnen.',
    );
  return matches[0] ?? null;
}

function assertAnalysisIdentity(analysis: AnalysisSummary, context: AnalysisSetupContext): void {
  if (analysis.id !== context.analysisId)
    throw new Error('Die gelesene Analyse gehört zu einer anderen Kennung.');
  if (analysis.listing_id === null) {
    if (
      analysis.underlying_id !== null ||
      !analysis.market_data_instrument_id ||
      context.listingId ||
      context.underlyingId ||
      context.workflowAction
    )
      throw new Error(
        'Die Referenzanalyse benötigt eine eindeutige listingfreie Instrumentidentität.',
      );
  } else if (!analysis.listing_id || !analysis.underlying_id) {
    throw new Error('Die gespeicherte Analyse besitzt keine eindeutige Listingzugehörigkeit.');
  }
  mergeIdentity(context.underlyingId, analysis.underlying_id ?? '', 'Analyse-Basiswertkennung');
  mergeIdentity(context.listingId, analysis.listing_id ?? '', 'Analyse-Listingkennung');
  if (context.instrumentId && context.instrumentId !== analysis.market_data_instrument_id)
    throw new Error('Die Instrumentkennung passt nicht zur gespeicherten Analyse.');
}

/** Stored-data reads only. Resolve again before a repair write; completed-step readback is explicit. */
export async function resolveAnalysisSetupContext(
  context: AnalysisSetupContext,
  signal?: AbortSignal,
  options: { requireBlockedStep?: boolean } = {},
): Promise<ResolvedAnalysisSetupContext> {
  const resolvedContext = { ...context, actionParams: { ...context.actionParams } };
  const result: ResolvedAnalysisSetupContext = {
    context: resolvedContext,
    detail: null,
    underlying: null,
    listing: null,
    source: null,
    workflow: null,
    workflowStep: null,
    returnTo: '',
  };
  if (context.workflowAction) {
    const workflow = await candidateApiClient.liveWorkflow(context.candidateId, signal);
    if (workflow.candidate_id !== context.candidateId)
      throw new Error('Die gelesene Readiness gehört zu einem anderen Kandidaten.');
    result.workflow = workflow;
    result.workflowStep = matchingStep(context, workflow);
    if (!result.workflowStep && options.requireBlockedStep !== false)
      throw new Error(
        'Dieser konkrete Analyse-Schritt ist nicht mehr blockiert oder seine Identitäten haben sich geändert. Bitte zum Kandidaten zurückkehren.',
      );
    if (result.workflowStep) {
      const expected = stepIdentities(result.workflowStep);
      resolvedContext.underlyingId = mergeIdentity(
        context.underlyingId,
        expected.underlyingId,
        'Workflow-Basiswertkennung',
      );
      resolvedContext.listingId = mergeIdentity(
        context.listingId,
        expected.listingId,
        'Workflow-Listingkennung',
      );
      resolvedContext.stepCode = result.workflowStep.code;
      resolvedContext.actionParams = { ...(result.workflowStep.action_params ?? {}) };
    }
  }
  if (context.analysisId) {
    const detail = await analysisApiClient.get(context.analysisId, signal);
    assertAnalysisIdentity(detail.analysis, resolvedContext);
    if (
      detail.runs.some((run) => !Number.isSafeInteger(run.version) || run.version < 1) ||
      new Set(detail.runs.map((run) => run.version)).size !== detail.runs.length
    )
      throw new Error('Die gespeicherten Analyseversionen sind nicht eindeutig.');
    resolvedContext.underlyingId = detail.analysis.underlying_id ?? '';
    resolvedContext.listingId = detail.analysis.listing_id ?? '';
    resolvedContext.instrumentId = detail.analysis.market_data_instrument_id ?? '';
    result.detail = detail;
    if (context.sourceVersion !== null) {
      const known = detail.runs.filter((run) => run.version === context.sourceVersion);
      if (known.length !== 1)
        throw new Error('Die angeforderte Quellversion gehört nicht eindeutig zu dieser Analyse.');
      const source = await analysisApiClient.getRun(
        context.analysisId,
        context.sourceVersion,
        signal,
      );
      assertAnalysisIdentity(source.analysis, resolvedContext);
      if (
        source.run.version !== context.sourceVersion ||
        source.run.model_id !== known[0].model_id ||
        source.run.model_version !== known[0].model_version ||
        source.run.input_hash !== known[0].input_hash
      )
        throw new Error('Der gelesene Quellstand passt nicht zur angeforderten Analyseversion.');
      result.source = source;
    }
  }
  if (resolvedContext.underlyingId) {
    const underlying = await marketApiClient.getUnderlying(resolvedContext.underlyingId, signal);
    if (underlying.id !== resolvedContext.underlyingId)
      throw new Error('Der gelesene Basiswert gehört nicht zum Analysekontext.');
    result.underlying = underlying;
    const matches = resolvedContext.listingId
      ? underlying.listings.filter((item) => item.id === resolvedContext.listingId)
      : underlying.listings.filter((item) => item.is_primary && item.lifecycle_status === 'ACTIVE');
    if (matches.length > 1 || (resolvedContext.listingId && matches.length !== 1))
      throw new Error('Die Notierung gehört nicht eindeutig zum gewählten Basiswert.');
    if (matches[0]) {
      if (matches[0].underlying_id !== underlying.id)
        throw new Error('Notierung und tatsächlicher Basiswert gehören nicht zusammen.');
      result.listing = matches[0];
      resolvedContext.listingId = matches[0].id;
    }
  } else if (resolvedContext.listingId) {
    throw new Error(
      'Die tatsächliche Basiswertzugehörigkeit dieser Notierung fehlt. Bitte den Kontext neu öffnen.',
    );
  }
  if (signal?.aborted) throw new DOMException('Analysekontext wurde verlassen.', 'AbortError');
  sealContext(resolvedContext);
  result.returnTo = resolvedContext.returnTo;
  return result;
}
