import { useEffect, useRef, useState } from 'react';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

type Route = {
  provider: string;
  listing_id: string;
  mic: string;
  currency: string;
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
  feed_delay_seconds: number | null;
  trading_status: string | null;
  refresh_error: string | null;
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
};

type Report = {
  assessed_at: string;
  scheduler_enabled: boolean;
  scheduler_leader: boolean;
  source_order: string[];
  configured_sources: string[];
  items: Item[];
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
  DISABLED: 'Automatischer Abruf aus',
  NOT_SCHEDULED: 'Noch nicht eingeplant',
  PENDING: 'Erster Abruf steht aus',
  RUNNING: 'Abruf läuft',
  AVAILABLE: 'Letzter Abruf erfolgreich',
  MISSING: 'Letzter Abruf ohne Kurs',
  ERROR: 'Letzter Abruf fehlgeschlagen',
  DEFERRED: 'Wiederholung nach Abruflimit',
};

function label(value: string) {
  return labels[value] ?? value;
}
function date(value: string | null) {
  return value ? new Date(value).toLocaleString('de-DE') : 'Unbekannt';
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
          ['ERROR', 'MISSING', 'DISABLED', 'NOT_SCHEDULED'].includes(item.refresh_status)),
    ) ?? [];

  return (
    <section aria-label="Kursquellen im Depot" className="mt-4 border-t border-slate-700 pt-4">
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
        className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm"
      >
        {loading ? 'Kursquellen werden geladen …' : 'Kursquellen im Depot prüfen'}
      </button>
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
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            <label>
              Emittent{' '}
              <select
                aria-label="Kursquellen nach Emittent"
                value={issuer}
                onChange={(event) => setIssuer(event.target.value)}
                className="rounded border border-slate-700 bg-slate-900 p-1"
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
                checked={onlyGaps}
                onChange={(event) => setOnlyGaps(event.target.checked)}
              />{' '}
              Nur Prüfbedarf
            </label>
          </div>
          {items.length === 0 && (
            <p className="mt-3 text-sm">Keine gehaltenen Optionsscheine für diese Ansicht.</p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Verifizierte Kurswege gehaltener Optionsscheine</caption>
              <thead>
                <tr>
                  <th className="p-2">Optionsschein / Emittent</th>
                  <th className="p-2">Kursnachweis</th>
                  <th className="p-2">Automatischer Abruf</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.warrant_id} className="border-t border-slate-800 align-top">
                    <td className="p-2">
                      <p className="font-semibold">{item.name}</p>
                      <p>{item.issuer}</p>
                      <p className="text-xs">
                        {item.isin ?? 'ISIN fehlt'} · {item.wkn ?? 'WKN unbekannt'}
                      </p>
                    </td>
                    <td className="p-2">
                      <p>{label(item.coverage)}</p>
                      <details className="mt-2">
                        <summary className="cursor-pointer">
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
                          <div
                            key={`${route.listing_id}:${route.provider}`}
                            className="my-3 border-l border-slate-700 pl-2"
                          >
                            <p>
                              {route.provider} ·{' '}
                              {route.provider_exchange_code === 'ISSUER'
                                ? 'Emittentenindikation'
                                : route.mic}{' '}
                              · {route.currency}
                            </p>
                            <p>
                              {route.configured
                                ? label(route.route_reason)
                                : 'Provider nicht konfiguriert'}{' '}
                              · {label(route.observation_status)}
                            </p>
                            {route.bid !== null && (
                              <p>
                                Geld: {route.bid} {route.currency} · Brief:{' '}
                                {route.ask ?? 'nicht vorhanden'}
                              </p>
                            )}
                            {route.reference_price !== null && (
                              <p>
                                Referenz ({route.reference_price_type}): {route.reference_price}{' '}
                                {route.currency} · nur indikativ
                              </p>
                            )}
                            <p>
                              Kurszeit: {date(route.observed_at)} · zuletzt abgerufen:{' '}
                              {date(route.retrieved_at)}
                            </p>
                            {route.age_seconds !== null && (
                              <p>Alter: {Math.floor(route.age_seconds / 60)} Min.</p>
                            )}
                            <p>
                              Quellenverzögerung:{' '}
                              {route.feed_delay_seconds === null
                                ? 'unbekannt'
                                : `${route.feed_delay_seconds} Sekunden`}
                            </p>
                            <p>Handelsstatus: {route.trading_status ?? 'unbekannt'}</p>
                            {route.refresh_error && (
                              <p className="text-amber-300">Abrufhinweis: {route.refresh_error}</p>
                            )}
                            <p className="text-xs">
                              Zuordnung:{' '}
                              {route.mapping_status ??
                                'ISIN-direkt / keine gespeicherte Providerzuordnung'}{' '}
                              · geprüft: {date(route.validated_at)}
                            </p>
                          </div>
                        ))}
                      </details>
                    </td>
                    <td className="p-2">
                      <p>{label(item.refresh_status)}</p>
                      <p>Letzte Prüfung: {date(item.checked_at)}</p>
                      <p>Nächste Prüfung frühestens: {date(item.next_run_at)}</p>
                      <details className="mt-2">
                        <summary>Diagnose</summary>
                        <p>{item.refresh_reason ?? 'Noch kein Abrufnachweis in dieser Laufzeit'}</p>
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
