import { useEffect, useRef, useState, type ReactNode } from 'react';
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
const referencePriceTypes: Record<string, string> = {
  LAST_TRADE: 'Letzter Handel (LAST_TRADE)',
  PREVIOUS_CLOSE: 'Vorheriger Schlusskurs (PREVIOUS_CLOSE)',
};

const focusClass =
  'focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300';

function TimeValue({ value }: { value: string | null | undefined }) {
  if (!value) return <>unbekannt</>;
  if (!/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) || !Number.isFinite(Date.parse(value))) {
    return <>{value} · Zeitbasis nicht belegt</>;
  }
  return <time dateTime={value}>{new Date(value).toISOString().replace('.000Z', 'Z')}</time>;
}

function EvidenceField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-sm text-slate-400">{label}</dt>
      <dd className="min-w-0 [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

function availability(value: boolean | null | undefined) {
  return value === true ? 'ja' : value === false ? 'nein' : 'nicht übermittelt';
}

function Observation({ item }: { item: QuoteHistoryReport['items'][number] }) {
  return (
    <li className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
      <h5 className="font-semibold">
        {item.provider} · {statuses[item.status] ?? 'Nicht eingeordneter Erfassungsstatus'}
      </h5>
      <p className="text-sm">
        Statuscode: <span className="[overflow-wrap:anywhere]">{item.status}</span>
        {item.reason && (
          <>
            {' '}
            · Diagnose: <span className="[overflow-wrap:anywhere]">{item.reason}</span>
          </>
        )}
      </p>
      {item.quote === null && <p>Kein Kursbeleg für diese Erfassung gespeichert.</p>}
      <div className="grid min-w-0 gap-4 lg:grid-cols-3">
        <div className="min-w-0 space-y-2">
          <h6 className="font-semibold">Zeitbelege</h6>
          <dl className="space-y-2">
            <EvidenceField label="Originalkurszeit (UTC)">
              <TimeValue value={item.quote?.observed_at} />
            </EvidenceField>
            <EvidenceField label="Erfassungszeit (UTC)">
              <TimeValue value={item.captured_at} />
            </EvidenceField>
            <EvidenceField label="Abrufzeit (UTC)">
              <TimeValue value={item.retrieved_at} />
            </EvidenceField>
            <EvidenceField label="Erfassungsslot (UTC)">
              <TimeValue value={item.slot_at} />
            </EvidenceField>
            <EvidenceField label="Originalzeittext der Quelle (unverändert)">
              {item.quote?.quote_time_text ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Zeitbasis der Quelle">
              {item.quote?.quote_time_basis ?? 'nicht übermittelt'}
            </EvidenceField>
          </dl>
        </div>
        <div className="min-w-0 space-y-2">
          <h6 className="font-semibold">Preisarten und Handelsplatz</h6>
          <dl className="space-y-2">
            <EvidenceField label="Geldkurs (BID)">
              {item.quote?.bid ?? 'nicht vorhanden'}
            </EvidenceField>
            <EvidenceField label="Briefkurs (ASK)">
              {item.quote?.ask ?? 'nicht vorhanden'}
            </EvidenceField>
            <EvidenceField label="Referenzkurs">
              {item.quote?.reference_price ?? 'nicht vorhanden'}
            </EvidenceField>
            <EvidenceField label="Referenz-Preisart">
              {item.quote?.reference_price_type
                ? (referencePriceTypes[item.quote.reference_price_type] ??
                  item.quote.reference_price_type)
                : 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Währung der Preise">
              {item.quote?.currency ?? 'unbekannt'}
            </EvidenceField>
            <EvidenceField label="Handelsplatz (MIC)">
              {item.quote?.venue_mic ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Provider-Platzcode">
              {item.quote?.provider_exchange_code ?? 'nicht übermittelt'}
            </EvidenceField>
          </dl>
        </div>
        <div className="min-w-0 space-y-2">
          <h6 className="font-semibold">Historische Quellenidentität</h6>
          <dl className="space-y-2">
            <EvidenceField label="Erfassungs-ID">{item.id}</EvidenceField>
            <EvidenceField label="ISIN">{item.isin}</EvidenceField>
            <EvidenceField label="Quellsegment / Identität">{item.identity_key}</EvidenceField>
            <EvidenceField label="Historische Listing-ID">
              {item.quote?.warrant_listing_id ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Provider-Symbol">
              {item.quote?.provider_symbol ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Kursbeleg-Fingerprint">
              {item.quote_fingerprint ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Quellenmodus">
              {item.quote?.source_mode ?? 'unbekannt'}
            </EvidenceField>
            <EvidenceField label="Cachezustand zur Erfassung">
              {item.cache_status ?? 'unbekannt'}
            </EvidenceField>
          </dl>
        </div>
      </div>
    </li>
  );
}

// A different product owns a different read, including completed results and errors.
export function WarrantQuoteHistory({ warrantId }: { warrantId: string }) {
  return <ProductQuoteHistory key={warrantId} warrantId={warrantId} />;
}

function ProductQuoteHistory({ warrantId }: { warrantId: string }) {
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
      if (!controller.signal.aborted) {
        if (value.warrant_id !== warrantId) {
          setError(
            'Erfassungsprotokoll gehört zu einem anderen Produkt. Es liegt kein neues Ergebnis vor.',
          );
        } else {
          setReport(value);
        }
      }
    } catch {
      if (!controller.signal.aborted)
        setError('Erfassungsprotokoll nicht erreichbar. Es liegt kein neues Ergebnis vor.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3 [overflow-wrap:anywhere]">
      <summary className={`cursor-pointer font-semibold ${focusClass}`}>
        Kursdaten-Verfügbarkeit und Erfassungsprotokoll
      </summary>
      <p>
        Gespeicherte Beobachtungen aus bereits erlaubten Abrufen. Das Öffnen startet keine
        Providerabfrage. Ein Protokoll wird erst mit dem Lesebutton angefordert.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label>
          Beobachtungsfenster
          <select
            className={`block max-w-full rounded border border-slate-600 bg-slate-950 p-2 ${focusClass}`}
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
          className={`rounded border px-3 py-2 disabled:opacity-50 ${focusClass}`}
        >
          {busy ? 'Protokoll wird geladen …' : 'Gespeichertes Protokoll laden'}
        </button>
      </div>
      <p role="status" className="text-sm text-slate-300">
        {busy ? 'Gespeicherte Beobachtungen werden gelesen.' : report ? 'Protokoll geladen.' : ''}
      </p>
      {error && <p role="alert">{error}</p>}
      {report && (
        <section aria-label="Gespeicherte Kursbeobachtungen" className="min-w-0 space-y-3">
          <h4 className="font-semibold">Erfassungsfenster und Grenzen</h4>
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
            <EvidenceField label="Beginn des Erfassungsfensters (UTC)">
              <TimeValue value={report.window_start} />
            </EvidenceField>
            <EvidenceField label="Ende des Erfassungsfensters (UTC)">
              <TimeValue value={report.window_end} />
            </EvidenceField>
            <EvidenceField label="Erste bekannte Produkterfassung (UTC)">
              {report.collection_started_at === null ? (
                'noch keine'
              ) : (
                <TimeValue value={report.collection_started_at} />
              )}
            </EvidenceField>
            <EvidenceField label="Produkt-ID">{report.warrant_id}</EvidenceField>
          </dl>
          <p className="text-sm text-slate-300">
            Das Fenster begrenzt die Erfassungen, nicht die Originalkurszeiten. Die erste bekannte
            Produkterfassung kann vor diesem Fenster liegen; sie belegt keinen Beginn einer
            vollständigen Kursversorgung.
          </p>
          <p>
            Keine vollständige Handelszeitabdeckung nachgewiesen. Nicht erfasste Intervalle sind
            unbekannt; mehrfach gelesene Cache-Kurse sind keine neuen Originalkurse. Eine Anzahl
            erwarteter oder aus einer Kurshistorie ausgeschlossener Kurspunkte wird nicht geliefert.
          </p>
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
            <EvidenceField label="Erfassungsregel">
              {report.sampling_policy ?? 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="Zeitabdeckungsquote">
              {report.time_coverage_percent === null ? 'nicht verfügbar' : 'nicht übermittelt'}
            </EvidenceField>
            <EvidenceField label="IV-Historie verfügbar (Backendangabe)">
              {availability(report.iv_history_available)}
            </EvidenceField>
            <EvidenceField label="Synchrone Basiswertkurse verfügbar (Backendangabe)">
              {availability(report.underlying_synchronization_available)}
            </EvidenceField>
            <EvidenceField label="Für Ausführung verwendbar (Backendangabe)">
              {availability(report.execution_usable)}
            </EvidenceField>
          </dl>
          {report.sampling_policy === 'FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1' && (
            <p>
              Je Route und historischer Identität bleibt die erste abgeschlossene Erfassung in jedem
              UTC-Fünfminutenintervall erhalten, einschließlich Fehlern. Ein späterer Erfolg ersetzt
              diese erste Erfassung nicht.
            </p>
          )}
          <h4 className="font-semibold">Belegte Beobachtungen je Quellsegment</h4>
          <p className="text-sm text-slate-300">
            Die drei Zähler beschreiben unterschiedliche Einheiten im Erfassungsfenster. UTC-Tage
            mit Erfassung sind keine nachgewiesenen vollständigen Handelstage. Die Statuszahlen
            stammen aus der damaligen Erfassung, nicht aus einer heutigen Qualitätsprüfung.
          </p>
          {report.segments.length === 0 && (
            <p>Noch keine Beobachtungen in diesem Fenster. Daraus folgt keine Entwarnung.</p>
          )}
          <div className="grid min-w-0 gap-3 md:grid-cols-2">
            {report.segments.map((s) => (
              <article
                key={`${s.provider}:${s.identity_key}:${s.isin}`}
                className="min-w-0 space-y-3 rounded border border-slate-700 p-3"
              >
                <h5 className="font-semibold">
                  {s.provider} · {s.isin}
                </h5>
                <dl className="grid min-w-0 gap-3 sm:grid-cols-3 md:grid-cols-1 xl:grid-cols-3">
                  <EvidenceField label="Erfasste Intervalle">
                    <span className="text-xl font-semibold">{s.sampled_slots}</span>{' '}
                    {s.sampled_slots === 1 ? 'UTC-Slot' : 'UTC-Slots'}
                  </EvidenceField>
                  <EvidenceField label="Unterschiedliche Kursbelege">
                    <span className="text-xl font-semibold">{s.distinct_quote_evidence}</span>{' '}
                    {s.distinct_quote_evidence === 1 ? 'Kursbeleg' : 'Kursbelege'}
                  </EvidenceField>
                  <EvidenceField label="UTC-Tage mit Erfassung">
                    <span className="text-xl font-semibold">{s.observed_utc_days}</span>{' '}
                    {s.observed_utc_days === 1 ? 'UTC-Tag' : 'UTC-Tage'}
                  </EvidenceField>
                </dl>
                <dl className="space-y-2">
                  <EvidenceField label="Quellsegment / Identität">{s.identity_key}</EvidenceField>
                  <EvidenceField label="Erste Erfassung im Fenster (UTC)">
                    <TimeValue value={s.first_capture_at} />
                  </EvidenceField>
                  <EvidenceField label="Letzte Erfassung im Fenster (UTC)">
                    <TimeValue value={s.last_capture_at} />
                  </EvidenceField>
                </dl>
                <details className="min-w-0 space-y-2">
                  <summary className={`cursor-pointer ${focusClass}`}>
                    Statuszahlen dieses Quellsegments
                  </summary>
                  {Object.keys(s.statuses).length === 0 ? (
                    <p>Keine Statuszahlen übermittelt.</p>
                  ) : (
                    <table className="w-full table-fixed text-left text-sm">
                      <caption className="pb-2 text-left text-slate-300">
                        Erfasste Status im Fenster, einschließlich Fehlern und fehlenden Kursen
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col" className="border-b border-slate-700 py-2 pr-2">
                            Status bei Erfassung
                          </th>
                          <th scope="col" className="w-24 border-b border-slate-700 py-2">
                            Anzahl Intervalle
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(s.statuses).map(([code, n]) => (
                          <tr key={code}>
                            <th
                              scope="row"
                              className="border-b border-slate-800 py-2 pr-2 align-top font-normal"
                            >
                              {statuses[code] ?? 'Nicht eingeordneter Erfassungsstatus'}
                              <span className="block text-xs text-slate-400 [overflow-wrap:anywhere]">
                                {code}
                              </span>
                            </th>
                            <td className="border-b border-slate-800 py-2 align-top">{n}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </details>
              </article>
            ))}
          </div>
          <details className="min-w-0 space-y-2">
            <summary className={`cursor-pointer ${focusClass}`}>
              Erfassungsbelege mit Originalzeiten ({report.items.length} geliefert)
            </summary>
            <p>
              Höchstens {report.item_limit} zuletzt erfasste Beobachtungen dieses Fensters über alle
              Quellsegmente zusammen. Die Segmentzähler gelten für das ganze Fenster und können
              größer sein. Diese Detailauswahl belegt keine vollständige Kurshistorie.
            </p>
            {report.items.length === 0 ? (
              <p>Keine Detailbelege in dieser Antwort.</p>
            ) : (
              <ul aria-label="Einzelne gespeicherte Erfassungsbelege" className="min-w-0 space-y-3">
                {report.items.map((item) => (
                  <Observation key={item.id} item={item} />
                ))}
              </ul>
            )}
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
