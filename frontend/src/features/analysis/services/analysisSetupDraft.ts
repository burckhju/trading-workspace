import { MarketTransportError } from '../../market/services/http';
import {
  defaultAnalysisParameters,
  newAnalysisModelVersion,
  type AnalysisDetail,
  type AnalysisParameters,
  type AnalysisRun,
  type AnalysisRunDetail,
  type AnalysisSummary,
  type RunAnalysisRequest,
} from '../types/api';

export const numericAnalysisFields = [
  ['short_window', 'Kurzfristiges Fenster'],
  ['medium_window', 'Mittelfristiges Fenster'],
  ['long_window', 'Langfristiges Fenster'],
  ['volatility_window', 'Volatilitätsfenster'],
  ['range_window', 'Spannenfenster'],
  ['minimum_required_observations', 'Mindestanzahl Beobachtungen'],
  ['maximum_data_age_days', 'Maximales Datenalter in Tagen'],
  ['rounding_scale', 'Dezimalstellen'],
] as const;

type NumericField = (typeof numericAnalysisFields)[number][0];
export type AnalysisDraft = Record<NumericField, string> & {
  start_date: string;
  end_date: string;
  price_field: string;
  momentum_windows: string;
  annualization_factor: string;
};

function parametersToDraft(
  parameters: AnalysisParameters,
): Omit<AnalysisDraft, 'start_date' | 'end_date'> {
  return {
    price_field: parameters.price_field,
    short_window: String(parameters.short_window),
    medium_window: String(parameters.medium_window),
    long_window: String(parameters.long_window),
    momentum_windows: parameters.momentum_windows.join(', '),
    volatility_window: String(parameters.volatility_window),
    range_window: String(parameters.range_window),
    minimum_required_observations: String(parameters.minimum_required_observations),
    maximum_data_age_days: String(parameters.maximum_data_age_days),
    annualization_factor: parameters.annualization_factor,
    rounding_scale: String(parameters.rounding_scale),
  };
}

export function initialAnalysisDraft(
  candidateRepair: boolean,
  historicalSource: boolean,
): AnalysisDraft {
  const today = new Date();
  const start = new Date(today);
  start.setUTCDate(start.getUTCDate() - (candidateRepair ? 400 : 365));
  return {
    ...parametersToDraft(defaultAnalysisParameters),
    start_date: historicalSource ? '' : start.toISOString().slice(0, 10),
    end_date: historicalSource ? '' : today.toISOString().slice(0, 10),
  };
}

function calendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return (
    Number.isFinite(parsed.getTime()) &&
    parsed.getUTCFullYear() > 0 &&
    parsed.toISOString().slice(0, 10) === value
  );
}

function integer(value: string, minimum: number): number {
  if (!/^\d+$/.test(value.trim())) return NaN;
  const result = Number(value);
  return Number.isSafeInteger(result) && result >= minimum ? result : NaN;
}

/** Compare the Decimal DTO without rounding through JavaScript's binary number type. */
function positiveDecimalKey(value: string): string | null {
  const match = /^\+?(\d+(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?$/.exec(value.trim());
  if (!match) return null;
  const [whole, fraction = ''] = match[1].split('.');
  const digits = `${whole}${fraction}`.replace(/^0+/, '');
  if (!digits) return null;
  const significant = digits.replace(/0+$/, '');
  const exponent =
    BigInt(match[2] ?? '0') - BigInt(fraction.length) + BigInt(digits.length - significant.length);
  return `${significant}e${exponent}`;
}

export function analysisDraftProblem(draft: AnalysisDraft): string {
  if (
    !calendarDate(draft.start_date) ||
    !calendarDate(draft.end_date) ||
    draft.start_date > draft.end_date
  )
    return 'Bitte einen gültigen Zeitraum für den neuen Lauf wählen: Von darf nicht nach Bis liegen.';
  if (!['CLOSE', 'ADJUSTED_CLOSE'].includes(draft.price_field))
    return 'Bitte ein unterstütztes Kursfeld auswählen.';
  for (const [field, label] of numericAnalysisFields) {
    if (
      !Number.isFinite(
        integer(
          draft[field],
          field === 'maximum_data_age_days' || field === 'rounding_scale' ? 0 : 1,
        ),
      )
    )
      return `${label} muss eine ganze Zahl ${field === 'maximum_data_age_days' || field === 'rounding_scale' ? 'ab 0' : 'größer als 0'} sein.`;
  }
  if (
    !(
      Number(draft.short_window) < Number(draft.medium_window) &&
      Number(draft.medium_window) < Number(draft.long_window)
    )
  )
    return 'Die Fenster müssen aufsteigend sein: kurzfristig < mittelfristig < langfristig.';
  if (Number(draft.rounding_scale) > 12)
    return 'Die Dezimalstellen müssen zwischen 0 und 12 liegen.';
  const momentum = draft.momentum_windows.trim()
    ? draft.momentum_windows.split(',').map((value) => integer(value, 1))
    : [];
  if (
    momentum.some(
      (value, index) => !Number.isFinite(value) || (index > 0 && value <= momentum[index - 1]),
    )
  )
    return 'Momentumfenster müssen positive, eindeutig aufsteigende ganze Zahlen sein, durch Kommas getrennt.';
  if (positiveDecimalKey(draft.annualization_factor) === null)
    return 'Der Annualisierungsfaktor muss eine positive Dezimalzahl sein.';
  return '';
}

export function analysisDraftRequest(draft: AnalysisDraft): RunAnalysisRequest {
  const problem = analysisDraftProblem(draft);
  if (problem) throw new Error(problem);
  return {
    start_date: draft.start_date,
    end_date: draft.end_date,
    model_version: newAnalysisModelVersion,
    parameters: {
      price_field: draft.price_field as AnalysisParameters['price_field'],
      short_window: Number(draft.short_window),
      medium_window: Number(draft.medium_window),
      long_window: Number(draft.long_window),
      momentum_windows: draft.momentum_windows.trim()
        ? draft.momentum_windows.split(',').map(Number)
        : [],
      volatility_window: Number(draft.volatility_window),
      range_window: Number(draft.range_window),
      minimum_required_observations: Number(draft.minimum_required_observations),
      maximum_data_age_days: Number(draft.maximum_data_age_days),
      annualization_factor: draft.annualization_factor.trim(),
      rounding_scale: Number(draft.rounding_scale),
    },
  };
}

/** Only known, complete saved parameters may become an explicitly requested proposal. */
export function prepareAnalysisSource(
  draft: AnalysisDraft,
  source: Record<string, unknown>,
): AnalysisDraft {
  const expected = Object.keys(defaultAnalysisParameters);
  if (
    Object.keys(source).some((key) => !expected.includes(key)) ||
    expected.some((key) => !(key in source))
  )
    throw new Error(
      'Die gespeicherten Parameter entsprechen nicht vollständig dem unterstützten Analysevertrag. Keine automatische Übernahme.',
    );
  if (
    numericAnalysisFields.some(
      ([key]) => typeof source[key] !== 'number' || !Number.isSafeInteger(source[key]),
    ) ||
    !Array.isArray(source.momentum_windows) ||
    source.momentum_windows.some(
      (value: unknown) => typeof value !== 'number' || !Number.isSafeInteger(value),
    ) ||
    typeof source.price_field !== 'string' ||
    typeof source.annualization_factor !== 'string'
  )
    throw new Error('Die gespeicherten Analyseparameter sind unvollständig oder nicht lesbar.');
  const proposal = {
    ...draft,
    ...parametersToDraft(source as AnalysisParameters),
  };
  // Dates are not in the source DTO and must never be inferred from snapshot endpoints.
  const problem = analysisDraftProblem({
    ...proposal,
    start_date: '2026-01-01',
    end_date: '2026-01-02',
  });
  if (problem) throw new Error(problem);
  return proposal;
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
const nonempty = (value: unknown): value is string =>
  typeof value === 'string' && Boolean(value.trim());
const timestamp = (value: unknown) => nonempty(value) && Number.isFinite(Date.parse(value));

function receipt(condition: boolean): asserts condition {
  if (!condition)
    throw new MarketTransportError(
      'Die Serverantwort belegt diesen Analyseauftrag nicht eindeutig. Abschluss unbekannt; nur den aktuellen Zustand erneut lesen.',
    );
}

export function validateAnalysisCreateReceipt(
  value: unknown,
  underlyingId: string,
  listingId: string,
): asserts value is AnalysisSummary {
  receipt(record(value));
  receipt(
    nonempty(value.id) &&
      /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(value.id) &&
      value.underlying_id === underlyingId &&
      value.listing_id === listingId &&
      timestamp(value.created_at) &&
      nonempty(value.created_by) &&
      (value.market_data_instrument_id === undefined ||
        value.market_data_instrument_id === null ||
        (nonempty(value.market_data_instrument_id) &&
          /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(value.market_data_instrument_id))),
  );
}

export function validateAnalysisRunReceipt(
  value: unknown,
  detail: AnalysisDetail,
): asserts value is AnalysisRun {
  receipt(record(value));
  const latest = Math.max(0, ...detail.runs.map((run) => run.version));
  receipt(
    typeof value.version === 'number' &&
      Number.isSafeInteger(value.version) &&
      value.version > latest &&
      ['COMPLETED', 'COMPLETED_WITH_WARNINGS', 'NOT_EVALUABLE', 'FAILED'].includes(
        String(value.status),
      ) &&
      ['GOOD', 'LIMITED', 'INSUFFICIENT'].includes(String(value.quality_status)) &&
      value.model_id === 'EOD_TREND_MOMENTUM' &&
      value.model_version === newAnalysisModelVersion &&
      typeof value.observation_count === 'number' &&
      Number.isSafeInteger(value.observation_count) &&
      value.observation_count >= 0 &&
      timestamp(value.analysis_time) &&
      nonempty(value.input_hash),
  );
}

export function validateAnalysisRunReadback(
  value: AnalysisRunDetail,
  detail: AnalysisDetail,
  acknowledged: AnalysisRun,
  request: RunAnalysisRequest,
): void {
  const expected = detail.analysis;
  if (
    value.analysis.id !== expected.id ||
    value.analysis.underlying_id !== expected.underlying_id ||
    value.analysis.listing_id !== expected.listing_id ||
    (value.analysis.market_data_instrument_id ?? null) !==
      (expected.market_data_instrument_id ?? null) ||
    Object.keys(acknowledged).some(
      (key) => value.run[key as keyof AnalysisRun] !== acknowledged[key as keyof AnalysisRun],
    )
  )
    throw new Error(
      'Der nachgelesene Lauf passt nicht zur bestätigten Analyseversion. Der Schreibauftrag bleibt abgeschlossen; bitte nur erneut lesen.',
    );
  const source = prepareAnalysisSource(initialAnalysisDraft(false, false), value.parameters);
  const readParameters = analysisDraftRequest(source).parameters;
  if (
    Object.keys(request.parameters).some((key) => {
      const field = key as keyof AnalysisParameters;
      return field === 'annualization_factor'
        ? positiveDecimalKey(readParameters[field]) !==
            positiveDecimalKey(request.parameters[field])
        : JSON.stringify(readParameters[field]) !== JSON.stringify(request.parameters[field]);
    })
  )
    throw new Error(
      'Die nachgelesenen Parameter passen nicht zum bestätigten Lauf. Bitte nur den Lesestand erneut laden.',
    );
}
