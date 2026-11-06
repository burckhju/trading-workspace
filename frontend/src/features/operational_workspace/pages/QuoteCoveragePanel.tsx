import { useEffect, useRef, useState } from 'react';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

type Route = {
  provider: string;
  listing_id: string;
  mic: string;
  currency: string;
  mapping_id?: string | null;
  mapping_status: string | null;
  provider_identity: string | null;
  provider_exchange_code: string | null;
  validated_at: string | null;
  configured: boolean;
  route_reason: string;
  observation_status: string;
  bid: string | null;
  ask: string | null;
  reference_price: string | null;
  reference_price_type: string | null;
  observed_at: string | null;
  retrieved_at: string | null;
  age_seconds: number | null;
  max_quote_age_seconds?: number | null;
  feed_delay_seconds: number | null;
  trading_status: string | null;
  refresh_error: string | null;
  quote_time_text?: string | null;
  quote_time_basis?: string | null;
};

type RefreshJob = {
  lane: string;
  status: string;
  reason: string | null;
  checked_at: string | null;
  next_run_at: string | null;
};

type Item = {
  warrant_id: string;
  name: string;
  isin: string | null;
  wkn: string | null;
  issuer: string;
  issuer_probe_eligible: boolean;
  coverage: string;
  routes: Route[];
  refresh_status: string;
  refresh_reason: string | null;
  checked_at: string | null;
  next_run_at: string | null;
  discovery_reasons: string[];
  refresh_jobs?: RefreshJob[];
};

type Report = {
  assessed_at: string;
  scheduler_enabled: boolean;
  scheduler_leader: boolean;
  source_order: string[];
  configured_sources: string[];
  items: Item[];
  assessment_scope?: string;
  execution_usable?: boolean;
};

const labels: Record<string, string> = {
  BID_WITHIN_AGE_BUDGET: 'Geldkurs innerhalb Altersgrenze',
  HISTORICAL_BID_ONLY: 'Nur historischer Geldkurs',
  OLDER_BID: 'Historischer Geldkurs / Abruf prüfen',
  REFERENCE_ONLY: 'Nur Last-/Schlusskurs',
  NO_VERIFIED_QUOTE: 'Noch kein verifizierter Kurs gespeichert',
  NO_VERIFIED_OBSERVATION: 'Noch kein verifizierter Kurs gespeichert',
  NO_USABLE_ROUTE: 'Keine nutzbare Kurszuordnung',
  INACTIVE_PRODUCT: 'Produkt oder Emittent inaktiv',
  ROUTE_UNAVAILABLE: 'Kursweg nicht nutzbar',
  IDENTITY_CHANGED: 'Identität geändert – neu prüfen',
  INVALID_STORED_OBSERVATION: 'Gespeicherte Kursdaten nicht gültig',
  ROUTE_IDENTITY_VERIFIED: 'Identität verifiziert',
  VALIDATED_MAPPING_REQUIRED: 'Verifizierte Zuordnung fehlt',
  MAPPING_DISABLED: 'Zuordnung ausdrücklich deaktiviert',
  MAPPING_INVALID: 'Zuordnung ungültig',
  MAPPING_IDENTITY_UNVERIFIED: 'Zuordnungsidentität nicht bestätigt',
  QUOTE_CURRENCY_INACTIVE: 'Kurswährung inaktiv',
  LISTING_OR_VENUE_INACTIVE: 'Notierung oder Handelsplatz inaktiv',
  ISIN_REQUIRED: 'ISIN fehlt',
  MIXED: 'Unterschiedliche Abrufstände – Details prüfen',
  ISSUER_QUOTES: 'Emittentenabruf',
  WARRANT_QUOTES: 'Weitere Kursquellen',
  QUOTE_TIMESTAMP_UNKNOWN: 'Kurszeitpunkt nicht belegt',
  DISABLED: 'Automatischer Abruf aus',
  NOT_SCHEDULED: 'Noch nicht eingeplant',
  PENDING: 'Erster Abruf steht aus',
  RUNNING: 'Abruf läuft',
  AVAILABLE: 'Schedulerlauf abgeschlossen',
  MISSING: 'Letzter Abruf ohne Kurs',
  ERROR: 'Letzter Abruf fehlgeschlagen',
  DEFERRED: 'Wiederholung nach Abruflimit',
};

function label(value: string) {
  return labels[value] ?? value;
}
function date(value: string | null) {
  if (!value) return 'Unbekannt';
  if (!/(Z|[+-]\d{2}:\d{2})$/i.test(value) || !Number.isFinite(Date.parse(value))) {
    return `${value} (kein belegter Zeitpunkt mit Zeitzone)`;
  }
  return `${new Date(value).toLocaleString('de-DE', { timeZone: 'UTC' })} UTC`;
}

const focus =
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300';

function RouteEvidence({ route }: { route: Route }) {
  const currency = route.currency || 'Währung unbekannt';
  return (
    <div className="my-3 min-w-0 space-y-3 rounded border border-slate-700 p-3">
      <h5 className="font-semibold">
        {route.provider} ·{' '}
        {route.provider_exchange_code === 'ISSUER' ? 'Emittentenindikation' : route.mic} ·{' '}
        {currency}
      </h5>
      <div>
        <h6 className="font-semibold text-slate-300">Quellenidentität und Verfügbarkeit</h6>
        <p>{route.configured ? 'Provider konfiguriert' : 'Provider nicht konfiguriert'}</p>
        <p>Routennachweis: {label(route.route_reason)}</p>
        <dl className="mt-2 space-y-1 text-xs">
          <div>
            <dt>Notierungs-ID</dt>
            <dd>{route.listing_id}</dd>
          </div>
          <div>
            <dt>Provideridentität</dt>
            <dd>{route.provider_identity ?? 'Nicht belegt'}</dd>
          </div>
          <div>
            <dt>Provider-Platzcode</dt>
            <dd>{route.provider_exchange_code ?? 'Nicht belegt'}</dd>
          </div>
          <div>
            <dt>Handelsplatz (MIC)</dt>
            <dd>{route.mic || 'Nicht belegt'}</dd>
          </div>
          <div>
            <dt>Mapping-ID</dt>
            <dd>{route.mapping_id ?? 'Keine gespeicherte Mapping-ID geliefert'}</dd>
          </div>
          <div>
            <dt>Zuordnungsstatus</dt>
            <dd>{route.mapping_status ?? 'Keine gespeicherte Providerzuordnung belegt'}</dd>
          </div>
          <div>
            <dt>Identitätsprüfung</dt>
            <dd>{date(route.validated_at)}</dd>
          </div>
        </dl>
      </div>
      <div>
        <h6 className="font-semibold text-slate-300">Gespeicherte Preisarten</h6>
        <p>Geld: {route.bid == null ? 'nicht vorhanden' : `${route.bid} ${currency}`}</p>
        <p>Brief: {route.ask == null ? 'nicht vorhanden' : `${route.ask} ${currency}`}</p>
        <p>
          Referenz ({route.reference_price_type ?? 'Preisart nicht belegt'}):{' '}
          {route.reference_price == null
            ? 'nicht vorhanden'
            : `${route.reference_price} ${currency} · nur indikativ`}
        </p>
        <p>Handelsstatus: {route.trading_status ?? 'unbekannt'}</p>
      </div>
      <div>
        <h6 className="font-semibold text-slate-300">Kursfrische und Zeitbasis</h6>
        <p>Beobachtungsstatus: {label(route.observation_status)}</p>
        <p>Kurszeit: {date(route.observed_at)}</p>
        <p>Originalzeittext: {route.quote_time_text ?? 'Nicht geliefert'}</p>
        <p>Zeitbasis der Quelle: {route.quote_time_basis ?? 'Nicht geliefert'}</p>
        <p>Zuletzt abgerufen: {date(route.retrieved_at)}</p>
        <p>
          Kursalter am Prüfstand:{' '}
          {route.age_seconds == null ? 'Unbekannt' : `${route.age_seconds} Sekunden`}
        </p>
        <p>
          Altersgrenze laut Quelle:{' '}
          {route.max_quote_age_seconds == null
            ? 'Nicht geliefert'
            : `${route.max_quote_age_seconds} Sekunden`}
        </p>
        <p>
          Quellenverzögerung:{' '}
          {route.feed_delay_seconds == null ? 'unbekannt' : `${route.feed_delay_seconds} Sekunden`}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Alter und Frische stammen aus dem Prüfstand. Ein Originalzeittext ohne belegte Zone bleibt
          unverändert; die Abrufzeit ersetzt keinen Kurszeitpunkt.
        </p>
      </div>
      {route.refresh_error && (
        <div className="text-amber-300">
          <p>Abrufhinweis: {route.refresh_error}</p>
          {(route.bid != null || route.ask != null || route.reference_price != null) && (
            <p>Gespeicherter Ersatzkurs · aktueller Providererfolg nicht bestätigt.</p>
          )}
        </div>
      )}
    </div>
  );
}

export function QuoteCoveragePanel() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [issuer, setIssuer] = useState('');
  const [onlyGaps, setOnlyGaps] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function load() {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setLoading(true);
    setError(false);
    setReport(null);
    try {
      const value = await requestJson<Report>(
        `${environment.apiBaseUrl}/api/v1/market-data/warrants/quote-coverage`,
        { signal: current.signal },
      );
      if (!current.signal.aborted) setReport(value);
    } catch {
      if (!current.signal.aborted) setError(true);
    } finally {
      if (!current.signal.aborted) setLoading(false);
    }
  }
  const items =
    report?.items.filter(
      (item) =>
        (!issuer || issuer === item.issuer) &&
        (!onlyGaps ||
          item.coverage !== 'BID_WITHIN_AGE_BUDGET' ||
          item.routes.some((route) => route.refresh_error) ||
          ['ERROR', 'MISSING', 'DISABLED', 'NOT_SCHEDULED', 'MIXED', 'DEFERRED'].includes(
            item.refresh_status,
          )),
    ) ?? [];

  return (
    <section
      aria-label="Kursquellen im Depot"
      className="mt-4 min-w-0 border-t border-slate-700 pt-4 [overflow-wrap:anywhere]"
    >
      <h3 className="text-sm font-semibold">Kursquellen im Depot</h3>
      <p className="mt-2 text-sm text-slate-400">
        Gespeicherte Zuordnungen und letzte verifizierte Beobachtungen je Optionsschein. Diese
        Prüfung lädt keine Providerdaten und verändert keine Zuordnung. Kursalter, Abrufstatus und
        Handelsfreigabe sind getrennt; keine Orderfreigabe.
      </p>
      <button
        type="button"
        onClick={() => void load()}
        disabled={loading}
        className={`mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm ${focus}`}
      >
        {loading ? 'Kursquellen werden geladen …' : 'Kursquellen im Depot prüfen'}
      </button>
      <p role="status" className="sr-only">
        {loading
          ? 'Gespeicherte Kursquellen werden gelesen.'
          : report
            ? 'Kursquellen geladen.'
            : ''}
      </p>
      {error && (
        <p role="alert" className="mt-2 text-amber-300">
          Kursquellen konnten nicht geladen werden. Erneut prüfen.
        </p>
      )}
      {report && (
        <>
          <p className="mt-2 text-sm">
            Prüfstand: {date(report.assessed_at)} · {report.items.length} gehaltene Optionsscheine
          </p>
          <p className="mt-2 text-sm text-slate-300">
            Produktabdeckung: Die gelieferte Liste zählt Produkte, keine Positionen oder Kurse. Die
            Einstufung je Produkt stammt vom Backend; einzelne Quellen können davon abweichen.
          </p>
          <dl className="mt-2 space-y-1 text-xs text-slate-400">
            <div>
              <dt>Prüfumfang</dt>
              <dd>
                {report.assessment_scope ??
                  'Scope-Feld nicht geliefert; Ansicht gespeicherter Beobachtungen'}
              </dd>
            </div>
            <div>
              <dt>Ausführungsverwendbarkeit (execution_usable)</dt>
              <dd>
                {report.execution_usable == null
                  ? 'Nicht geliefert'
                  : String(report.execution_usable)}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-sm">
            Automatischer Abruf:{' '}
            {!report.scheduler_enabled
              ? 'ausgeschaltet'
              : report.scheduler_leader
                ? 'aktiv'
                : 'wartet auf Hintergrunddienst'}
            .
          </p>
          <p className="mt-2 text-xs text-slate-400">
            Konfigurierte Quellen: {report.configured_sources.join(', ') || 'Keine'}. Nicht
            konfigurierte Quellen garantieren keine Abdeckung. Eine passende Emittentenbezeichnung
            erlaubt nur die Identitätsprüfung, nicht den Kursabruf ohne verifizierte Zuordnung.
          </p>
          <details className="mt-2 text-xs">
            <summary className={`cursor-pointer ${focus}`}>
              Quellenkonfiguration des Prüfstands
            </summary>
            <ul className="mt-2 list-inside list-disc space-y-1">
              {report.source_order.map((source) => (
                <li key={source}>
                  {source}:{' '}
                  {report.configured_sources.includes(source)
                    ? 'konfiguriert'
                    : 'nicht konfiguriert'}
                </li>
              ))}
            </ul>
            {report.source_order.length === 0 && <p>Keine Quellenreihenfolge geliefert.</p>}
            <p className="mt-2">
              Konfiguration belegt weder Erreichbarkeit noch einen Kurs dieses Produkts.
            </p>
          </details>
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            <label>
              Emittent{' '}
              <select
                aria-label="Kursquellen nach Emittent"
                value={issuer}
                onChange={(event) => setIssuer(event.target.value)}
                className={`max-w-full rounded border border-slate-700 bg-slate-900 p-1 ${focus}`}
              >
                <option value="">Alle Emittenten</option>
                {[...new Set(report.items.map((item) => item.issuer))].sort().map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                className={focus}
                checked={onlyGaps}
                onChange={(event) => setOnlyGaps(event.target.checked)}
              />{' '}
              Nur Prüfbedarf
            </label>
          </div>
          {items.length === 0 && (
            <p className="mt-3 text-sm">Keine gehaltenen Optionsscheine für diese Ansicht.</p>
          )}
          <p className="mt-3 text-xs text-slate-400">
            Breite Tabelle: bei Bedarf im beschrifteten Tabellenbereich horizontal scrollen.
          </p>
          <div
            role="region"
            aria-label="Kursabdeckung je Produkt, horizontal scrollbar"
            tabIndex={0}
            className={`mt-2 max-w-full overflow-x-auto ${focus}`}
          >
            <table className="w-full min-w-[42rem] table-fixed text-left text-sm">
              <caption className="sr-only">Verifizierte Kurswege gehaltener Optionsscheine</caption>
              <thead>
                <tr>
                  <th scope="col" className="w-1/4 p-2">
                    Optionsschein / Emittent
                  </th>
                  <th scope="col" className="w-1/2 p-2">
                    Produktabdeckung und Kursnachweis
                  </th>
                  <th scope="col" className="w-1/4 p-2">
                    Automatischer Abruf
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.warrant_id} className="border-t border-slate-800 align-top">
                    <th scope="row" className="p-2 font-normal">
                      <h4 className="font-semibold">{item.name}</h4>
                      <p>{item.issuer}</p>
                      <p className="text-xs">
                        {item.isin ?? 'ISIN fehlt'} · {item.wkn ?? 'WKN unbekannt'}
                      </p>
                      <p className="mt-2 text-xs">Produkt-ID: {item.warrant_id}</p>
                    </th>
                    <td className="p-2">
                      <p>{label(item.coverage)}</p>
                      <details className="mt-2">
                        <summary className={`cursor-pointer ${focus}`}>
                          Kurswege ({item.routes.length})
                        </summary>
                        <p className="my-2 text-xs text-slate-400">
                          Beobachtungen je Notierung, keine neue Auswahl einer Bewertungsquelle.
                          Emittentenpreise sind keine Börsenkurse. Abrufzeit ersetzt niemals
                          Kurszeit.
                        </p>
                        {item.routes.length === 0 && (
                          <p>
                            Keine passende gespeicherte Notierung oder Providerzuordnung. Stammdaten
                            und Erkennung prüfen.
                          </p>
                        )}
                        {item.routes.map((route) => (
                          <RouteEvidence
                            key={`${route.listing_id}:${route.provider}`}
                            route={route}
                          />
                        ))}
                      </details>
                    </td>
                    <td className="p-2">
                      <p>{label(item.refresh_status)}</p>
                      {item.routes.some((route) => route.refresh_error) && (
                        <p className="mt-1 text-amber-300">
                          Mindestens ein Providerabruf ohne bestätigten Erfolg. Gespeicherte Kurse
                          belegen keine Wiederherstellung.
                        </p>
                      )}
                      {item.refresh_jobs && item.refresh_jobs.length > 0 ? (
                        item.refresh_jobs.map((job) => (
                          <div key={job.lane} className="mt-2 break-words">
                            <p>
                              {label(job.lane)}: {label(job.status)}
                            </p>
                            <p>Letzte Prüfung: {date(job.checked_at)}</p>
                            <p>Nächste Prüfung frühestens: {date(job.next_run_at)}</p>
                            {job.reason && <p className="text-xs">{job.reason}</p>}
                          </div>
                        ))
                      ) : (
                        <>
                          <p>Letzte Prüfung: {date(item.checked_at)}</p>
                          <p>Nächste Prüfung frühestens: {date(item.next_run_at)}</p>
                        </>
                      )}
                      <details className="mt-2">
                        <summary className={`cursor-pointer ${focus}`}>Diagnose</summary>
                        <p>
                          {item.refresh_reason ??
                            (item.refresh_jobs?.length
                              ? 'Abrufnachweise je Auftragsart siehe oben'
                              : 'Noch kein Abrufnachweis in dieser Laufzeit')}
                        </p>
                        {item.discovery_reasons.map((reason) => (
                          <p key={reason}>{reason}</p>
                        ))}
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
