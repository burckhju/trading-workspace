import { useCallback, useEffect, useRef, useState } from 'react';

import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import {
  effectiveExecutions,
  executionDateContext,
  executionDateCorrection,
  todayInZone,
} from '../services/executionDateCorrection';
import type { TradeTimelineEntryResponse } from '../types/api';

function dateLabel(entry: TradeTimelineEntryResponse) {
  return entry.execution_side === 'SELL' ? 'Verkaufsdatum' : 'Kaufdatum';
}

export function ExecutionDatesPanel({
  tradeId,
  cancelled = false,
  onChanged,
}: {
  tradeId: string;
  cancelled?: boolean;
  onChanged: () => Promise<void>;
}) {
  const [entries, setEntries] = useState<TradeTimelineEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TradeTimelineEntryResponse | null>(null);
  const [date, setDate] = useState('');
  const [keepTime, setKeepTime] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const lock = useRef(false);
  const mounted = useRef(true);
  const generation = useRef(0);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const current = ++generation.current;
      setLoading(true);
      setLoadError(null);
      try {
        const history = await tradeManagementApiClient.timeline(tradeId, signal);
        if (!signal?.aborted && current === generation.current) {
          setEntries(effectiveExecutions(history));
        }
      } catch (error) {
        if (!signal?.aborted && current === generation.current) {
          setLoadError(error instanceof Error ? error.message : 'Buchungen nicht verfügbar.');
        }
      } finally {
        if (!signal?.aborted && current === generation.current) setLoading(false);
      }
    },
    [tradeId],
  );

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void load(controller.signal);
    return () => {
      mounted.current = false;
      controller.abort();
      generation.current += 1;
    };
  }, [load]);

  useEffect(() => {
    function changed(event: Event) {
      if ((event as CustomEvent<{ tradeId: string }>).detail?.tradeId === tradeId) void load();
    }
    window.addEventListener(tradeTimelineChangedEvent, changed);
    return () => window.removeEventListener(tradeTimelineChangedEvent, changed);
  }, [load, tradeId]);

  function edit(entry: TradeTimelineEntryResponse) {
    try {
      const context = executionDateContext(entry);
      setSelected(entry);
      setDate(context.date);
      setKeepTime(context.hasTime);
      setConfirmed(false);
      setMessage(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Buchung bitte prüfen.');
    }
  }

  async function save() {
    if (!selected || !confirmed || cancelled || lock.current || loading || loadError) return;
    if (!entries.some((entry) => entry.id === selected.id)) {
      setMessage('Die Buchung wurde inzwischen korrigiert. Bitte den aktuellen Eintrag auswählen.');
      return;
    }
    lock.current = true;
    setBusy(true);
    setMessage(null);
    let saved = false;
    try {
      const payload = executionDateCorrection(selected, date, keepTime);
      await tradeManagementApiClient.correctExecution(tradeId, selected.id, payload);
      saved = true;
      if (!mounted.current) return;
      setSelected(null);
      setConfirmed(false);
      setMessage('Datum korrigiert. Die ursprüngliche Buchung bleibt in der Historie erhalten.');
      await onChanged();
    } catch (error) {
      if (!mounted.current) return;
      const detail = error instanceof Error ? error.message : 'Bitte Buchung und Datum prüfen.';
      setMessage(
        saved
          ? `Datum gespeichert, Ansicht noch nicht aktualisiert. Bitte neu laden. ${detail}`
          : `Korrektur nicht bestätigt: ${detail} Vor erneutem Speichern den aktuellen Stand prüfen.`,
      );
      setConfirmed(false);
    } finally {
      if (mounted.current) {
        await load();
        setBusy(false);
      }
      lock.current = false;
    }
  }

  const context = selected ? executionDateContext(selected) : null;
  const unchanged = context && date === context.date && (keepTime || !context.hasTime);
  const stale = selected && !entries.some((entry) => entry.id === selected.id);

  return (
    <section
      aria-label="Kauf- und Verkaufsdaten"
      className="rounded-xl border border-slate-800 p-5"
    >
      <h2 className="text-lg font-semibold">Kauf- und Verkaufsdaten</h2>
      <p className="mt-2 text-sm text-slate-400">
        Das Ausführungsdatum gehört zur einzelnen Kauf-, Nachkauf- oder Verkaufsbuchung, nicht zur
        Anlage des Produkts. Hier lassen sich auch bereits erfasste Daten korrigieren. Stückzahl und
        Preis bleiben dabei unverändert; die Position wird neu berechnet.
      </p>
      {cancelled && (
        <p className="mt-3">Stornierter Trade: Die Datumsangaben sind schreibgeschützt.</p>
      )}
      {message && (
        <p role="status" className="mt-3">
          {message}
        </p>
      )}
      {loading && <p className="mt-3">Buchungsdaten werden geladen…</p>}
      {loadError && (
        <p role="alert" className="mt-3">
          {loadError}
        </p>
      )}
      <button
        type="button"
        disabled={busy}
        onClick={() => void load()}
        className="mt-3 rounded border p-2"
      >
        Buchungsdaten neu laden
      </button>
      {!loading && !loadError && entries.length === 0 && (
        <p className="mt-3">Keine Kauf-/Verkaufsbuchungen vorhanden.</p>
      )}
      <div className="mt-4 space-y-3">
        {entries.map((entry) => (
          <article
            key={entry.id}
            aria-label={`Buchung ${entry.id}`}
            className="rounded border border-slate-800 p-3"
          >
            <p className="font-medium">
              {dateLabel(entry)} · {entry.quantity} Stück · Preis {entry.price_per_unit}
            </p>
            <p className="mt-1 text-sm">
              Ausgeführt: {entry.executed_on ?? new Date(entry.occurred_at).toLocaleString('de-DE')}
              {entry.executed_on && ` (Uhrzeit unbekannt, ${entry.execution_timezone})`}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Erfasst: {new Date(entry.recorded_at).toLocaleString('de-DE')} · Buchung {entry.id}
            </p>
            {!cancelled && (
              <button
                type="button"
                disabled={busy || loading || !!loadError}
                onClick={() => edit(entry)}
                className="mt-2 rounded border p-2"
              >
                {dateLabel(entry)} korrigieren
              </button>
            )}
          </article>
        ))}
      </div>
      {selected && context && !cancelled && (
        <form
          aria-label="Ausführungsdatum korrigieren"
          className="mt-4 space-y-3 rounded border border-sky-800 p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <p>
            Buchung {selected.id} · {selected.quantity} Stück · Preis {selected.price_per_unit}
          </p>
          <label className="block">
            {dateLabel(selected)} korrigieren
            <input
              aria-label={`${dateLabel(selected)} korrigieren`}
              type="date"
              required
              max={todayInZone(context.timezone)}
              value={date}
              disabled={busy}
              onChange={(event) => {
                setDate(event.target.value);
                setConfirmed(false);
              }}
              className="mt-1 block rounded border bg-slate-950 p-2"
            />
          </label>
          <p className="text-sm text-slate-400">
            Zeitzone: {context.timezone}. Maßgeblich ist die tatsächliche Ausführung, nicht das
            Eingabedatum.
          </p>
          {context.hasTime ? (
            <label className="block">
              <input
                type="checkbox"
                checked={keepTime}
                disabled={busy}
                onChange={(event) => {
                  setKeepTime(event.target.checked);
                  setConfirmed(false);
                }}
              />{' '}
              Bisherige Uhrzeit beibehalten (
              {new Date(selected.occurred_at).toLocaleTimeString('de-DE')})
            </label>
          ) : null}
          {!keepTime && (
            <p className="text-sm text-amber-300">
              Es wird nur das bestätigte Datum gespeichert. Die genaue Uhrzeit gilt als unbekannt.
            </p>
          )}
          <p className="text-sm text-slate-400">
            Es entsteht kein weiterer Kauf oder Verkauf. Die Korrektur erhält einen eigenen
            Erfassungszeitpunkt; der alte Eintrag bleibt sichtbar.
          </p>
          {stale && (
            <p role="alert">
              Diese Buchung wurde bereits ersetzt. Bitte den aktuellen Eintrag auswählen.
            </p>
          )}
          <label className="block">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy || !!stale}
              onChange={(event) => setConfirmed(event.target.checked)}
            />{' '}
            Ich bestätige das tatsächliche Ausführungsdatum dieser Buchung.
          </label>
          <button
            type="submit"
            disabled={
              busy || loading || !!loadError || !!stale || !!unchanged || !confirmed || !date
            }
            className="rounded border border-sky-700 p-2 disabled:opacity-50"
          >
            Datumsänderung speichern
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setSelected(null);
              setConfirmed(false);
            }}
            className="ml-3 rounded border p-2"
          >
            Abbrechen
          </button>
        </form>
      )}
    </section>
  );
}
