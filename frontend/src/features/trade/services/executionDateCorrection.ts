import { localToday } from './capture';
import type { ExecutionCorrectionRequest, TradeTimelineEntryResponse } from '../types/api';

export function effectiveExecutions(entries: TradeTimelineEntryResponse[]) {
  const executions = entries.filter((entry) => entry.kind === 'EXECUTION');
  const superseded = new Set(executions.map((entry) => entry.supersedes_id));
  return executions.filter((entry) => !superseded.has(entry.id));
}

export function executionDateContext(entry: TradeTimelineEntryResponse) {
  const timezone = entry.executed_on
    ? entry.execution_timezone
    : Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (!timezone) throw new Error('Die Zeitzone der gespeicherten Ausführung fehlt.');
  return {
    date: entry.executed_on ?? localToday(new Date(entry.occurred_at)),
    timezone,
    hasTime: !entry.executed_on,
  };
}

export function todayInZone(timezone: string): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const value = (type: string) => parts.find((part) => part.type === type)?.value;
  return `${value('year')}-${value('month')}-${value('day')}`;
}

/** Change the confirmed calendar date, never the quantity, price or capture timestamp. */
export function executionDateCorrection(
  entry: TradeTimelineEntryResponse,
  date: string,
  keepTime: boolean,
): ExecutionCorrectionRequest {
  const { timezone, hasTime } = executionDateContext(entry);
  const check = new Date(`${date}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    Number.isNaN(check.getTime()) ||
    check.toISOString().slice(0, 10) !== date ||
    date > todayInZone(timezone)
  ) {
    throw new Error('Bitte ein gültiges Kauf-/Verkaufsdatum bis heute wählen.');
  }
  if (
    !entry.execution_side ||
    entry.quantity === null ||
    entry.price_per_unit === null ||
    entry.kind !== 'EXECUTION'
  ) {
    throw new Error('Die gespeicherte Kauf-/Verkaufsbuchung ist unvollständig.');
  }
  const amounts = {
    side: entry.execution_side,
    quantity: entry.quantity,
    price_per_unit: entry.price_per_unit,
  };
  if (!keepTime || !hasTime) {
    return { ...amounts, executed_on: date, execution_timezone: timezone };
  }
  const original = new Date(entry.occurred_at);
  if (Number.isNaN(original.getTime())) throw new Error('Der gespeicherte Zeitpunkt ist ungültig.');
  if (date === localToday(original)) return { ...amounts, executed_at: entry.occurred_at };

  // Preserve the local clock and every fractional second of the recorded source.
  // Candidate offsets on both sides of a DST transition detect skipped/ambiguous times.
  const wall = new Date(`${date}T00:00:00Z`);
  wall.setUTCHours(original.getHours(), original.getMinutes(), original.getSeconds());
  const offsets = new Set(
    [-36, 0, 36].map((hours) => new Date(wall.getTime() + hours * 3600000).getTimezoneOffset()),
  );
  const candidates = [...offsets]
    .map((offset) => new Date(wall.getTime() + offset * 60000))
    .filter(
      (candidate) =>
        localToday(candidate) === date &&
        candidate.getHours() === original.getHours() &&
        candidate.getMinutes() === original.getMinutes() &&
        candidate.getSeconds() === original.getSeconds(),
    );
  if (candidates.length !== 1) {
    throw new Error(
      'Die bisherige Uhrzeit ist am neuen Datum wegen der Zeitumstellung nicht eindeutig ' +
        'oder nicht vorhanden. Bitte die tatsächliche Ausführung prüfen; keine Uhrzeit schätzen.',
    );
  }
  const fraction = entry.occurred_at.match(/T\d{2}:\d{2}:\d{2}(\.\d+)/)?.[1] ?? '';
  const instant = candidates[0].toISOString().replace(/\.\d{3}Z$/, `${fraction}Z`);
  if (new Date(instant).getTime() > Date.now()) {
    throw new Error('Die Ausführung darf nicht in der Zukunft liegen.');
  }
  return { ...amounts, executed_at: instant };
}
