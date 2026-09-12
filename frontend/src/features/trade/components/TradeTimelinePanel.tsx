import { useCallback, useEffect, useState } from 'react';

import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
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
    const quantity = entry.quantity ?? 0;
    const price = entry.price_per_unit ? formatNumber(entry.price_per_unit) : '—';
    return `${quantity} Stück · ${price} je Einheit`;
  }
  if (entry.numeric_value !== null) return formatNumber(entry.numeric_value);
  return entry.text_value ?? '—';
}

export function TradeTimelinePanel({ tradeId }: { tradeId: string }) {
  const [entries, setEntries] = useState<TradeTimelineEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        setEntries(await tradeManagementApiClient.timeline(tradeId, signal));
      } catch (reason: unknown) {
        if (!signal?.aborted) {
          setError(
            reason instanceof Error ? reason.message : 'Timeline konnte nicht geladen werden.',
          );
        }
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [tradeId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    function refresh(event: Event) {
      const detail = (event as CustomEvent<{ tradeId?: string }>).detail;
      if (detail?.tradeId === tradeId) void load();
    }

    window.addEventListener(tradeTimelineChangedEvent, refresh);
    return () => window.removeEventListener(tradeTimelineChangedEvent, refresh);
  }, [load, tradeId]);

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

      {loading && <p className="mt-4 text-sm text-slate-400">Timeline wird geladen…</p>}
      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-slate-700 p-3 text-sm">
          {error}
        </p>
      )}
      {!loading && !error && entries.length === 0 && (
        <p className="mt-4 text-sm text-slate-400">Noch keine Timeline-Einträge vorhanden.</p>
      )}
      {!loading && !error && entries.length > 0 && (
        <ol className="mt-4 space-y-3">
          {entries.map((entry) => (
            <li key={entry.id} className="rounded-lg border border-slate-800 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{entryTitle(entry)}</p>
                  <p className="mt-1 text-sm text-slate-400">{entryDetail(entry)}</p>
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
                    {entry.executed_on
                      ? `${entry.executed_on} (Uhrzeit unbekannt, ${entry.execution_timezone})`
                      : formatDateTime(entry.occurred_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Erfasst</dt>
                  <dd className="mt-1">{formatDateTime(entry.recorded_at)}</dd>
                </div>
              </dl>
              {entry.supersedes_id && (
                <p className="mt-3 text-xs text-amber-300">
                  Korrektur eines früheren Eintrags · ersetzt {entry.supersedes_id.slice(0, 8)}…
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
