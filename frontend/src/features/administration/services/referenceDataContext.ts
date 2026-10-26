import { chartClient } from '../../analysis/services/chartClient';
import { candidateApiClient } from '../../candidate/services/client';
import type { CandidateLiveWorkflow, CandidateLiveWorkflowStep } from '../../candidate/types/api';
import { marketApiClient } from '../../market/services/client';
import type { ListingResponse, UnderlyingDetailResponse } from '../../market/types/api';
import { resolveListingMapping } from './referenceMapping';
import {
  topDownAdminClient,
  type MarketReference,
  type ProviderMapping,
  type Sector,
} from './topDownAdminClient';

export const WORKFLOW_SETUP_ACTIONS = {
  ASSIGN_BROAD_MARKET_BENCHMARK: 'stockMarket',
  ASSIGN_SECTOR: 'stockSector',
  ASSIGN_SECTOR_REFERENCE: 'sectorReference',
  ASSIGN_REFERENCE_LISTING: 'proxy',
  CREATE_EODHD_MAPPING: 'listingMapping',
  VALIDATE_EODHD_MAPPING: 'listingValidate',
  IMPORT_DAILY_PRICE_HISTORY: 'listingImport',
} as const;

export type WorkflowSetupAction = keyof typeof WORKFLOW_SETUP_ACTIONS;
export type SetupAction =
  | (typeof WORKFLOW_SETUP_ACTIONS)[WorkflowSetupAction]
  | 'bootstrap'
  | 'sector'
  | 'reference'
  | 'referenceMapping'
  | 'referenceValidate'
  | 'basis'
  | 'referenceImport';

export interface ReferenceDataContext {
  action: SetupAction;
  workflowAction: WorkflowSetupAction | null;
  candidateId: string;
  underlyingId: string;
  listingId: string;
  sectorId: string;
  referenceId: string;
  mappingId: string;
  resourceId: string;
  actionParams: Record<string, string>;
  stepCode: string;
  returnTo: string;
  key: string;
}

export interface ResolvedReferenceDataContext extends ReferenceDataContext {
  underlying: UnderlyingDetailResponse | null;
  listing: ListingResponse | null;
  reference: MarketReference | null;
  sector: Sector | null;
  mapping: ProviderMapping | null;
  workflow: CandidateLiveWorkflow | null;
  workflowStep: CandidateLiveWorkflowStep | null;
}

const setupActions = new Set<string>([
  ...Object.values(WORKFLOW_SETUP_ACTIONS),
  'bootstrap',
  'sector',
  'reference',
  'referenceMapping',
  'referenceValidate',
  'basis',
  'referenceImport',
]);

const identityKeys = {
  underlying_id: 'underlyingId',
  listing_id: 'listingId',
  sector_id: 'sectorId',
  reference_id: 'referenceId',
  market_reference_id: 'referenceId',
  mapping_id: 'mappingId',
} as const;

export function isWorkflowSetupAction(action: string): action is WorkflowSetupAction {
  return Object.prototype.hasOwnProperty.call(WORKFLOW_SETUP_ACTIONS, action);
}

function uniqueParameter(params: URLSearchParams, name: string): string {
  const values = [
    ...new Set(
      params
        .getAll(name)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  ];
  if (values.length > 1) throw new Error(`Widersprüchliche Angaben für ${name}.`);
  return values[0] ?? '';
}

function actionParameters(params: URLSearchParams): Record<string, string> {
  const raw = uniqueParameter(params, 'action_params');
  if (!raw) return {};
  let value: unknown;
  try {
    value = JSON.parse(raw) as unknown;
  } catch {
    throw new Error('Die Aktionsparameter sind nicht lesbar. Bitte den Kontext erneut öffnen.');
  }
  if (
    !value ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    Object.values(value).some((item) => typeof item !== 'string')
  ) {
    throw new Error('Die Aktionsparameter müssen eindeutige Textkennungen enthalten.');
  }
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, (item as string).trim()]),
  );
}

function mergeIdentity(current: string, incoming: string, label: string): string {
  if (current && incoming && current !== incoming) {
    throw new Error(`Widersprüchliche ${label}: Der Schreibvorgang bleibt gesperrt.`);
  }
  return current || incoming;
}

function chartReturnTo(params: URLSearchParams, context: ReferenceDataContext): string {
  // Only this page's documented query fields may form an internal return route.
  const supplied = uniqueParameter(params, 'chart_context');
  const result = new URLSearchParams();
  if (supplied) {
    const source = new URLSearchParams(supplied);
    for (const name of ['underlying', 'period', 'end', 'field']) {
      const value = uniqueParameter(source, name);
      if (value) result.set(name, value);
    }
    for (const target of source.getAll('target')) result.append('target', target);
  } else if (context.referenceId) {
    result.set('target', `reference:${context.referenceId}`);
  } else if (context.listingId) {
    result.set('target', `listing:${context.listingId}`);
  } else if (context.underlyingId) {
    result.set('underlying', context.underlyingId);
  }
  return `/market-charts${result.size ? `?${result.toString()}` : ''}`;
}

/** Parse all supplied identities once; resource_id has exactly one action-specific meaning. */
export function parseReferenceDataContext(params: URLSearchParams): ReferenceDataContext {
  const rawAction = uniqueParameter(params, 'action');
  const workflowAction = isWorkflowSetupAction(rawAction) ? rawAction : null;
  if (rawAction && !workflowAction && !setupActions.has(rawAction)) {
    throw new Error(`Unbekannte Einrichtungsaktion: ${rawAction}.`);
  }
  const context: ReferenceDataContext = {
    action: workflowAction
      ? WORKFLOW_SETUP_ACTIONS[workflowAction]
      : ((rawAction || 'bootstrap') as SetupAction),
    workflowAction,
    candidateId: uniqueParameter(params, 'candidate_id'),
    underlyingId: '',
    listingId: '',
    sectorId: '',
    referenceId: '',
    mappingId: '',
    resourceId: uniqueParameter(params, 'resource_id'),
    actionParams: actionParameters(params),
    stepCode: uniqueParameter(params, 'step_code'),
    returnTo: '',
    key: '',
  };
  for (const [parameter, property] of Object.entries(identityKeys)) {
    const value = mergeIdentity(
      uniqueParameter(params, parameter),
      context.actionParams[parameter] ?? '',
      parameter,
    );
    context[property] = mergeIdentity(context[property], value, parameter);
  }
  if (!rawAction) {
    context.action = context.referenceId
      ? 'referenceImport'
      : context.listingId
        ? 'listingImport'
        : context.sectorId
          ? 'sectorReference'
          : context.underlyingId
            ? 'stockSector'
            : 'bootstrap';
  }
  if (context.candidateId && !workflowAction) {
    throw new Error('Im Kandidatenkontext fehlt eine eindeutige Workflow-Aktion.');
  }
  if (context.resourceId) {
    const property =
      workflowAction === 'ASSIGN_SECTOR_REFERENCE'
        ? 'sectorId'
        : workflowAction === 'ASSIGN_REFERENCE_LISTING'
          ? 'referenceId'
          : workflowAction === 'VALIDATE_EODHD_MAPPING'
            ? 'mappingId'
            : workflowAction === 'CREATE_EODHD_MAPPING' ||
                workflowAction === 'IMPORT_DAILY_PRICE_HISTORY'
              ? 'listingId'
              : null;
    if (!property) throw new Error('Diese Aktion besitzt keinen eindeutigen resource_id-Vertrag.');
    context[property] = mergeIdentity(context[property], context.resourceId, 'Ressourcenkennung');
  }
  if (
    ['referenceMapping', 'referenceValidate', 'basis', 'referenceImport'].includes(
      context.action,
    ) &&
    (context.listingId || context.underlyingId)
  ) {
    throw new Error('Ein direktes Index-Mapping besitzt keine Listing- oder Basiswertidentität.');
  }
  if (workflowAction) {
    const required =
      context.action === 'stockMarket' || context.action === 'stockSector'
        ? context.underlyingId
        : context.action === 'sectorReference'
          ? context.sectorId
          : context.action === 'proxy'
            ? context.referenceId
            : context.action === 'listingValidate'
              ? context.mappingId
              : context.listingId;
    if (!required) {
      throw new Error(
        'Das erforderliche Ausgangsobjekt fehlt. Bitte den Workflow-Link neu öffnen.',
      );
    }
  }
  context.returnTo = context.candidateId
    ? `/candidates?candidate=${encodeURIComponent(context.candidateId)}`
    : chartReturnTo(params, context);
  context.key = JSON.stringify({ ...context, key: undefined });
  return context;
}

function stepContext(step: CandidateLiveWorkflowStep): ReferenceDataContext {
  return parseReferenceDataContext(
    new URLSearchParams({
      action: step.action ?? '',
      resource_id: step.resource_id ?? '',
      ...step.action_params,
    }),
  );
}

function matchingStep(
  context: ReferenceDataContext,
  workflow: CandidateLiveWorkflow,
): CandidateLiveWorkflowStep | null {
  const matches = workflow.steps.filter((step) => {
    if (
      step.status !== 'BLOCKED' ||
      step.action !== context.workflowAction ||
      (context.stepCode && step.code !== context.stepCode) ||
      (context.resourceId && step.resource_id !== context.resourceId)
    ) {
      return false;
    }
    const expected = stepContext(step);
    const properties = [...new Set(Object.values(identityKeys))];
    if (
      properties.some(
        (property) =>
          context[property] && expected[property] && context[property] !== expected[property],
      )
    ) {
      return false;
    }
    return Object.entries(context.actionParams).every(([parameter, value]) => {
      const property = Object.prototype.hasOwnProperty.call(identityKeys, parameter)
        ? identityKeys[parameter as keyof typeof identityKeys]
        : null;
      return property ? value === expected[property] : value === step.action_params?.[parameter];
    });
  });
  const identities = new Set(
    matches.map((step) => {
      const expected = stepContext(step);
      return JSON.stringify([
        expected.underlyingId,
        expected.listingId,
        expected.sectorId,
        expected.referenceId,
        expected.mappingId,
        step.action_params,
      ]);
    }),
  );
  if (identities.size > 1) {
    throw new Error('Der Link ist mehreren blockierten Schritten zuzuordnen. Bitte neu öffnen.');
  }
  return matches[0] ?? null;
}

/** These are ordinary stored-data reads, never provider discovery or a mutation. */
export async function resolveReferenceDataContext(
  context: ReferenceDataContext,
  signal?: AbortSignal,
  options: { requireBlockedStep?: boolean } = {},
): Promise<ResolvedReferenceDataContext> {
  const result: ResolvedReferenceDataContext = {
    ...context,
    underlying: null,
    listing: null,
    reference: null,
    sector: null,
    mapping: null,
    workflow: null,
    workflowStep: null,
  };
  let mappingValues: ProviderMapping[] | null = null;
  if (context.candidateId) {
    result.workflow = await candidateApiClient.liveWorkflow(context.candidateId, signal);
    if (result.workflow.candidate_id !== context.candidateId) {
      throw new Error('Die gelesene Readiness gehört zu einem anderen Kandidaten.');
    }
    result.workflowStep = matchingStep(context, result.workflow);
    if (!result.workflowStep && options.requireBlockedStep !== false) {
      throw new Error(
        'Dieser konkrete Schritt ist im aktuellen Kandidaten-Workflow nicht mehr blockiert oder seine Identitäten haben sich geändert. Bitte zum Kandidaten zurückkehren.',
      );
    }
    if (result.workflowStep) {
      const expected = stepContext(result.workflowStep);
      for (const property of [...new Set(Object.values(identityKeys))]) {
        result[property] = mergeIdentity(result[property], expected[property], property);
      }
      result.stepCode = result.workflowStep.code;
    }
    if (
      ['stockMarket', 'stockSector'].includes(result.action) &&
      result.underlyingId !== result.workflow.underlying_id
    ) {
      throw new Error('Die Zuordnung betrifft nicht den Basiswert dieses Kandidaten.');
    }
  }
  if (['listingMapping', 'listingValidate', 'listingImport'].includes(result.action)) {
    const mappings = await topDownAdminClient.mappings(signal);
    mappingValues = mappings;
    if (!result.listingId && result.mappingId) {
      const identified = mappings.filter((item) => item.id === result.mappingId);
      if (
        identified.length !== 1 ||
        !identified[0].listing_id ||
        identified[0].provider !== 'EODHD'
      ) {
        throw new Error('Das Mapping ist keiner eindeutigen EODHD-Notierung zugeordnet.');
      }
      result.listingId = identified[0].listing_id;
    }
    if (result.listingId) {
      result.mapping = resolveListingMapping(
        mappings,
        result.listingId,
        result.mappingId || undefined,
      );
      if (result.mapping) result.mappingId = result.mapping.id;
      if (
        result.workflowAction &&
        ['listingValidate', 'listingImport'].includes(result.action) &&
        !result.mapping
      ) {
        throw new Error('Für diese Notierung fehlt ein eindeutiges EODHD-Mapping.');
      }
    }
  }
  if (result.listingId && !result.underlyingId) {
    const date = new Date().toISOString().slice(0, 10);
    const comparison = await chartClient.series(
      [`listing:${result.listingId}`],
      date,
      date,
      'CLOSE',
      signal,
    );
    const identities = comparison.series.map((series) => series.identity);
    if (
      identities.length !== 1 ||
      identities[0].listing_id !== result.listingId ||
      !identities[0].underlying_id
    ) {
      throw new Error(
        'Die tatsächliche Zugehörigkeit dieser Notierung ist nicht eindeutig lesbar.',
      );
    }
    result.underlyingId = identities[0].underlying_id;
  }
  const [underlying, references, sectors] = await Promise.all([
    result.underlyingId ? marketApiClient.getUnderlying(result.underlyingId, signal) : null,
    result.referenceId ? topDownAdminClient.references(signal) : [],
    result.sectorId ? topDownAdminClient.sectors(signal) : [],
  ]);
  if (underlying) {
    if (underlying.id !== result.underlyingId)
      throw new Error('Der gelesene Basiswert passt nicht zum Kontext.');
    result.underlying = underlying;
    if (
      !result.listingId &&
      ['proxy', 'listingMapping', 'listingValidate', 'listingImport'].includes(result.action)
    ) {
      const primaries = underlying.listings.filter((item) => item.is_primary);
      if (primaries.length > 1)
        throw new Error('Für diesen Basiswert ist keine eindeutige Primary-Notierung vorhanden.');
      result.listingId = primaries[0]?.id ?? '';
    }
    if (result.listingId) {
      result.listing = underlying.listings.find((item) => item.id === result.listingId) ?? null;
      if (!result.listing || result.listing.underlying_id !== underlying.id) {
        throw new Error('Notierung und Basiswert gehören nicht zusammen. Schreiben ist gesperrt.');
      }
    }
  }
  if (mappingValues && result.listingId) {
    result.mapping = resolveListingMapping(
      mappingValues,
      result.listingId,
      result.mappingId || undefined,
    );
    if (result.mapping) result.mappingId = result.mapping.id;
  }
  if (result.referenceId) {
    const matches = references.filter((item) => item.id === result.referenceId);
    if (matches.length !== 1) throw new Error('Die Marktreferenz fehlt oder ist nicht eindeutig.');
    result.reference = matches[0];
    if (result.action === 'sectorReference' && result.reference.reference_type !== 'SECTOR_INDEX') {
      throw new Error('Für einen Sektor muss eine geeignete Sektorreferenz gewählt werden.');
    }
  }
  if (result.sectorId) {
    const matches = sectors.filter((item) => item.id === result.sectorId);
    if (matches.length !== 1) throw new Error('Der Sektor fehlt oder ist nicht eindeutig.');
    result.sector = matches[0];
  }
  if (signal?.aborted) throw new DOMException('Kontext wurde verlassen.', 'AbortError');
  return result;
}

export function canonicalSetupUrl(context: ReferenceDataContext): string {
  const params = new URLSearchParams({ action: context.workflowAction ?? context.action });
  for (const [parameter, property] of Object.entries(identityKeys)) {
    if (parameter !== 'market_reference_id' && context[property])
      params.set(parameter, context[property]);
  }
  if (context.candidateId) params.set('candidate_id', context.candidateId);
  if (context.resourceId) params.set('resource_id', context.resourceId);
  if (context.stepCode) params.set('step_code', context.stepCode);
  if (Object.keys(context.actionParams).length)
    params.set('action_params', JSON.stringify(context.actionParams));
  const chartSearch = context.returnTo.startsWith('/market-charts?')
    ? context.returnTo.slice('/market-charts?'.length)
    : '';
  if (chartSearch) params.set('chart_context', chartSearch);
  return `/chart-setup?${params.toString()}`;
}

/** Carry only documented chart state; callers cannot supply an external return address. */
export function withChartSetupContext(setupUrl: string, chartParams: URLSearchParams): string {
  const [pathname, query = ''] = setupUrl.split('?');
  if (pathname !== '/chart-setup') return setupUrl;
  const params = new URLSearchParams(query);
  const chart = new URLSearchParams();
  for (const name of ['underlying', 'period', 'end', 'field']) {
    const value = uniqueParameter(chartParams, name);
    if (value) chart.set(name, value);
  }
  for (const target of chartParams.getAll('target')) chart.append('target', target);
  if (chart.size) params.set('chart_context', chart.toString());
  return `${pathname}?${params.toString()}`;
}
