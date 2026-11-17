import { environment } from '../../../services/environment';
import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderLossReport, LossEpisodeView } from '../hebeltraderLoss';

const missingRules = ['B05', 'B06', 'F207_2_PROTECTION', 'F207_5_LIFECYCLE_ACCEPTANCE'];

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(text);
}
function count(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}
function clock(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(
      value,
    ) &&
    !value.endsWith('-00:00') &&
    Number.isFinite(Date.parse(value)) &&
    new Date(value.slice(0, 10)).toISOString().slice(0, 10) === value.slice(0, 10)
  );
}
function decimal(value: unknown): boolean {
  return (
    typeof value === 'string' &&
    value.length <= 100 &&
    /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value)
  );
}
function assessment(value: unknown): boolean {
  return (
    object(value) &&
    text(value.id) &&
    text(value.owner_basis_id) &&
    clock(value.evaluated_at) &&
    clock(value.recorded_at) &&
    ['LOSS', 'RECOVERED', 'NOT_ASSESSABLE', 'NOT_REACHED', 'CLOSED'].includes(
      String(value.outcome),
    ) &&
    strings(value.reasons) &&
    value.reasons.length > 0 &&
    (value.bid_at === null || clock(value.bid_at)) &&
    (value.bid === null || decimal(value.bid)) &&
    decimal(value.gross_entry) &&
    (value.currency === null ||
      (typeof value.currency === 'string' && /^[A-Z]{3}$/.test(value.currency))) &&
    count(value.remaining_quantity) &&
    (value.completed_sessions_at_bid === null || count(value.completed_sessions_at_bid)) &&
    (!['LOSS', 'RECOVERED'].includes(String(value.outcome)) ||
      (value.bid !== null && value.bid_at !== null && value.completed_sessions_at_bid !== null))
  );
}
function episode(value: unknown): boolean {
  if (
    !object(value) ||
    !['id', 'alert_id', 'opening_assessment_id'].every((key) => text(value[key])) ||
    !count(value.episode_number) ||
    value.episode_number === 0 ||
    !clock(value.opened_at)
  )
    return false;
  if (value.closed_at === null) {
    return value.close_reason === null && value.closing_assessment_id === null;
  }
  return clock(value.closed_at) && text(value.close_reason) && text(value.closing_assessment_id);
}

export function verifyHebeltraderLoss(
  value: unknown,
  tradeId: string,
  positionId: string,
): HebeltraderLossReport {
  const invalid = () =>
    new Error(
      'Der gespeicherte B04/B57-Regelstand passt nicht zum Positions- und Betriebsvertrag.',
    );
  if (
    !object(value) ||
    value.trade_id !== tradeId ||
    value.position_id !== positionId ||
    value.definition_version !== 'hebeltrader-b04-b57-v1' ||
    value.rule_scope !== 'B04_B57_WITH_B58_INPUTS' ||
    value.baseline_id !== 'HEBELTRADER_CONFIRMED_BASELINE' ||
    value.baseline_version !== '1.0.0' ||
    value.implementation_status !== 'B04_B57_IMPLEMENTED' ||
    value.full_baseline_activated !== false ||
    value.read_status !== 'READ_ONLY' ||
    !clock(value.read_at) ||
    !['NOT_ACTIVATED', 'BLOCKED_SOURCE', 'SCOPE_ENABLED'].includes(
      String(value.activation_status),
    ) ||
    typeof value.runner_enabled !== 'boolean' ||
    !strings(value.source_qualification_references) ||
    !strings(value.remaining_scope) ||
    value.remaining_scope.length !== missingRules.length ||
    !missingRules.every((rule) => (value.remaining_scope as string[]).includes(rule)) ||
    !count(value.assessment_count) ||
    !count(value.episode_count) ||
    !(value.latest_assessment === null || assessment(value.latest_assessment)) ||
    !(value.active_episode === null || episode(value.active_episode)) ||
    !Array.isArray(value.recent_episodes) ||
    value.recent_episodes.length > 50 ||
    !value.recent_episodes.every(episode)
  )
    throw invalid();
  const report = value as unknown as HebeltraderLossReport;
  if (
    (report.assessment_count === 0) !== (report.latest_assessment === null) ||
    report.episode_count < report.recent_episodes.length ||
    (report.episode_count === 0) !== (report.recent_episodes.length === 0) ||
    new Set(report.recent_episodes.map((item) => item.id)).size !== report.recent_episodes.length ||
    (report.activation_status === 'SCOPE_ENABLED' &&
      report.source_qualification_references.length === 0) ||
    (report.activation_status === 'BLOCKED_SOURCE' &&
      report.source_qualification_references.length !== 0)
  )
    throw invalid();
  const openEpisodes = report.recent_episodes.filter((item) => item.closed_at === null);
  if (
    openEpisodes.length > 1 ||
    (report.active_episode === null && openEpisodes.length !== 0) ||
    (report.active_episode !== null &&
      (openEpisodes.length !== 1 ||
        report.active_episode.closed_at !== null ||
        Object.keys(report.active_episode).some(
          (key) =>
            report.active_episode![key as keyof LossEpisodeView] !==
            openEpisodes[0][key as keyof LossEpisodeView],
        )))
  )
    throw invalid();
  return report;
}

export async function readHebeltraderLoss(
  tradeId: string,
  positionId: string,
  signal?: AbortSignal,
): Promise<HebeltraderLossReport> {
  let value: unknown;
  try {
    value = await requestJson<unknown>(
      `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(tradeId)}/hebeltrader-loss?position_id=${encodeURIComponent(positionId)}`,
      { signal },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error(
      error instanceof MarketApiError && error.status === 403
        ? 'Keine Berechtigung für den B04/B57-Regelstand dieser Position.'
        : 'Der gespeicherte B04/B57-Regelstand konnte nicht gelesen werden. Der Zustand einer Verlustepisode ist damit nicht geklärt.',
    );
  }
  return verifyHebeltraderLoss(value, tradeId, positionId);
}
