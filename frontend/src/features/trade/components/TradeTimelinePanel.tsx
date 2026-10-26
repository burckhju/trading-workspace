import { executionCurrencyText } from '../services/executionCurrency';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';
import type { TradeTimelineEntryResponse } from '../types/api';

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('de-DE');
}

function formatNumber(value: string): string {
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 10 }).format(Number(value));
}

function entryTitle(entry: TradeTimelineEntryResponse): string {
  if (entry.kind === 'CANCELLATION') return 'Fehleingabe storniert (kein Verkauf)';
  if (entry.kind === 'EXECUTION') {
    return entry.execution_side === 'SELL' ? 'Verkauf erfasst' : 'Kauf erfasst';
  }
  if (entry.management_event_type === 'STOP_CHANGED') return 'Stop geändert';
  if (entry.management_event_type === 'TARGET_CHANGED') return 'Target geändert';
  if (entry.management_event_type === 'THESIS_UPDATED') return 'These aktualisiert';
  return 'Management-Notiz';
}

function entryDetail(entry: TradeTimelineEntryResponse): string {
  if (entry.kind === 'EXECUTION') {
    const quantity = entry.quantity ?? '—';
    const price = entry.price_per_unit ?? '—';
    return `${quantity} Stück · ${price} je Einheit`;
  }
  if (entry.numeric_value !== null) return formatNumber(entry.numeric_value);
  return entry.text_value ?? '—';
}

/** Read-only presentation of the booking area's single timeline read. */
export function TradeTimelinePanel({ entries }: { entries: TradeTimelineEntryResponse[] }) {
  const replacements = new Map(
    entries.filter((entry) => entry.supersedes_id).map((entry) => [entry.supersedes_id, entry.id]),
  );
  return (
    <section className="rounded-xl border border-slate-800 p-5" aria-labelledby="timeline-title">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Historie</p>
        <h2 id="timeline-title" className="mt-1 text-lg font-semibold">
          Trade Timeline
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Executions und Managemententscheidungen in ihrer unveränderlichen Historie. Korrekturen
          bleiben nachvollziehbar und ersetzen ältere Einträge nicht unsichtbar.
        </p>
      </div>

      {entries.length === 0 && (
        <p className="mt-4 text-sm text-slate-400">Noch keine Timeline-Einträge vorhanden.</p>
      )}
      {entries.length > 0 && (
        <ol className="mt-4 space-y-3">
          {entries.map((entry) => (
            <li
              key={entry.id}
              aria-label={`Historischer Eintrag ${entry.id}`}
              className="rounded-lg border border-slate-800 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{entryTitle(entry)}</p>
                  <p className="mt-1 text-sm text-slate-400">{entryDetail(entry)}</p>
                  {entry.kind === 'EXECUTION' && (
                    <p className="text-xs text-slate-400">
                      Ausführungswährung:{' '}
                      {executionCurrencyText(
                        entry.currency_resolution,
                        entry.currency_confirmation,
                      )}
                    </p>
                  )}
                  {entry.price_binding && (
                    <p className="text-xs text-slate-400">
                      {entry.price_binding.basis === 'WARRANT' ? 'Optionsschein' : 'Basiswert'} ·{' '}
                      {entry.price_binding.currency} · {entry.price_binding.instrument_id}
                    </p>
                  )}
                </div>
                <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
                  {entry.kind === 'EXECUTION'
                    ? entry.execution_side
                    : entry.kind === 'CANCELLATION'
                      ? 'CANCELLED'
                      : 'MANAGEMENT'}
                </span>
              </div>
              <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Wirksam / ausgeführt</dt>
                  <dd className="mt-1">
                    {entry.executed_on ? (
                      `${entry.executed_on} (Uhrzeit unbekannt, ${entry.execution_timezone})`
                    ) : (
                      <time dateTime={entry.occurred_at}>
                        {formatDateTime(entry.occurred_at)} · {entry.occurred_at}
                      </time>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Erfasst</dt>
                  <dd className="mt-1">
                    <time dateTime={entry.recorded_at}>
                      {formatDateTime(entry.recorded_at)} · {entry.recorded_at}
                    </time>
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Eintrag</dt>
                  <dd className="mt-1 break-all">{entry.id}</dd>
                </div>
              </dl>
              {entry.supersedes_id && (
                <p className="mt-3 text-xs text-amber-300">
                  Korrektur eines früheren Eintrags · ersetzt {entry.supersedes_id}
                </p>
              )}
              {replacements.has(entry.id) && (
                <p className="mt-2 break-all text-xs text-slate-400">
                  Ersetzt durch {replacements.get(entry.id)} · nur als historische Quelle erhalten
                </p>
              )}
              {entry.kind === 'EXECUTION' && (
                <ExecutionCurrencySources resolution={entry.currency_resolution} />
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
