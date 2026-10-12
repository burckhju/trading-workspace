import { useEffect, useRef, useState } from 'react';
import { dataEvidenceApi } from '../services/dataEvidence';
import type { QuoteHistoryReport } from '../types/dataEvidence';

const statuses: Record<string, string> = {
  TWO_SIDED_WITHIN_AGE_LIMIT: 'Geld/Brief innerhalb der Altersgrenze',
  ONE_SIDED: 'Nur eine Kursseite',
  REFERENCE_ONLY: 'Nur Referenzkurs',
  TIMESTAMP_UNKNOWN: 'Originalkurszeit unbekannt',
  TIME_INCONSISTENT: 'Zeitpunkte widersprüchlich',
  STALE: 'Kurs zu alt',
  AGE_POLICY_UNKNOWN: 'Altersgrenze unbekannt',
  REQUEST_FAILED: 'Abruf oder Validierung fehlgeschlagen',
  NO_QUOTE: 'Kein Kurs zurückgegeben',
};

export function WarrantQuoteHistory({ warrantId }: { warrantId: string }) {
  const [days, setDays] = useState(7);
  const [report, setReport] = useState<QuoteHistoryReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function load() {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    setReport(null);
    try {
      const value = await dataEvidenceApi.history(warrantId, days, controller.signal);
      if (!controller.signal.aborted) setReport(value);
    } catch {
      if (!controller.signal.aborted)
        setError('Erfassungsprotokoll nicht erreichbar. Es liegt kein neues Ergebnis vor.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <details className="min-w-0 space-y-3 break-words rounded border border-slate-700 p-3">
      <summary className="cursor-pointer font-semibold">
        Kursdaten-Verfügbarkeit und Erfassungsprotokoll
      </summary>
      <p>
        Gespeicherte Beobachtungen aus bereits erlaubten Abrufen. Das Öffnen startet keine
        Providerabfrage. Je Quelle und UTC-Fünfminutenintervall zählt der erste abgeschlossene
        Abruf, auch bei Fehlern.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label>
          Beobachtungsfenster
          <select
            className="block max-w-full rounded border border-slate-600 bg-slate-950 p-2"
            value={days}
            onChange={(e) => {
              active.current?.abort();
              setBusy(false);
              setReport(null);
              setError('');
              setDays(Number(e.target.value));
            }}
          >
            {[7, 14, 31].map((n) => (
              <option key={n} value={n}>
                {n} Kalendertage
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={() => void load()}
          className="rounded border px-3 py-2 disabled:opacity-50"
        >
          {busy ? 'Protokoll wird geladen …' : 'Gespeichertes Protokoll laden'}
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      {report && (
        <section
          aria-label="Gespeicherte Kursbeobachtungen"
          aria-live="polite"
          className="min-w-0 space-y-3"
        >
          <p>
            Fenster: {report.window_start} bis {report.window_end}. Erste Erfassung:{' '}
            {report.collection_started_at ?? 'noch keine'}.
          </p>
          <p>
            Keine vollständige Handelszeitabdeckung nachgewiesen. Nicht erfasste Intervalle sind
            unbekannt; mehrfach gelesene Cache-Kurse sind keine neuen Originalkurse. Noch keine
            IV-Historie und keine synchronen Basiswertkurse.
          </p>
          {report.segments.length === 0 && (
            <p>Noch keine Beobachtungen in diesem Fenster. Daraus folgt keine Entwarnung.</p>
          )}
          <div className="grid min-w-0 gap-3 md:grid-cols-2">
            {report.segments.map((s) => (
              <div key={`${s.provider}:${s.identity_key}`} className="min-w-0 space-y-1">
                <h5 className="font-semibold">
                  {s.provider} · {s.isin}
                </h5>
                <p>
                  {s.sampled_slots} erfasste Intervalle · {s.distinct_quote_evidence}{' '}
                  unterschiedliche Kursbelege · {s.observed_utc_days} UTC-Tage
                </p>
                <ul className="list-disc pl-5">
                  {Object.entries(s.statuses)
                    .filter(([, n]) => n > 0)
                    .map(([code, n]) => (
                      <li key={code}>
                        {statuses[code] ?? code}: {n}
                      </li>
                    ))}
                </ul>
                <p className="text-xs text-slate-400">Quellsegment: {s.identity_key}</p>
              </div>
            ))}
          </div>
          <details className="min-w-0 space-y-2">
            <summary className="cursor-pointer">
              Letzte {report.item_limit} Beobachtungen mit Originalzeiten
            </summary>
            {report.items.map((item) => (
              <article key={item.id} className="min-w-0 space-y-1 border-t border-slate-700 py-2">
                <p className="font-semibold">
                  {item.provider} · {statuses[item.status] ?? item.status}
                </p>
                <p>
                  Erfasst: {item.captured_at} · Abrufzeit: {item.retrieved_at ?? 'unbekannt'} ·
                  Originalkurszeit: {item.quote?.observed_at ?? 'unbekannt'}
                </p>
                <p>
                  Geld: {item.quote?.bid ?? 'nicht vorhanden'} · Brief:{' '}
                  {item.quote?.ask ?? 'nicht vorhanden'} · Währung:{' '}
                  {item.quote?.currency ?? 'unbekannt'}
                </p>
                {item.quote?.reference_price && (
                  <p>
                    Referenz: {item.quote.reference_price} ({item.quote.reference_price_type})
                  </p>
                )}
                <p>
                  Quellenmodus: {item.quote?.source_mode ?? 'unbekannt'} · Cache:{' '}
                  {item.cache_status ?? 'unbekannt'}
                </p>
                {item.reason && <p>Diagnose: {item.reason}</p>}
                <p className="text-xs text-slate-400">
                  ISIN {item.isin} · Quellsegment {item.identity_key}
                </p>
              </article>
            ))}
          </details>
          <p>
            Kursqualität ist kein Risikoniveau. Das Protokoll verändert weder Stops/Ziele noch
            Benachrichtigungen.
          </p>
        </section>
      )}
    </details>
  );
}
