import { useCallback, useEffect, useState } from 'react';

import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import type { ProductPositionValuationResponse } from '../types/api';

function formatDecimal(value: string | null): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 10 }).format(Number(value));
}

function formatQuoteAge(value: ProductPositionValuationResponse): string {
  if (value.quote_age_seconds === null) return 'Alter unbekannt';
  if (value.quote_age_seconds < 60) return `${value.quote_age_seconds} Sek.`;
  return `${Math.floor(value.quote_age_seconds / 60)} Min.`;
}

function statusText(value: ProductPositionValuationResponse): string {
  switch (value.status) {
    case 'AVAILABLE':
      return 'Produktkurs verfügbar';
    case 'INDICATIVE':
      return 'Indikative Auswertung';
    case 'LAST_AVAILABLE':
      return 'Letzter verfügbarer Produktkurs';
    case 'STALE':
      return 'Produktkurs veraltet';
    case 'MISSING':
      return 'Produktkurs fehlt';
    case 'UNAVAILABLE':
      return 'Produktkurs nicht verfügbar';
    case 'ERROR':
      return 'Produktkurs prüfen';
  }
}

function reasonText(reason: string): string {
  switch (reason) {
    case 'REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS':
      return 'Auswertung und Überwachung verwenden den verfügbaren Handels- oder Schlusskurs. Dieser Referenzkurs ist kein aktuelles Kauf- oder Verkaufsangebot. Stop und Target werden weiterhin anhand des Underlyings überwacht.';
    case 'WARRANT_QUOTE_STALE':
      return 'Der letzte Produktkurs ist zu alt für eine belastbare aktuelle Depotbewertung. Eine indikative Analyse zum letzten verfügbaren Kurs bleibt möglich.';
    case 'MARKET_CLOSED_LAST_AVAILABLE_QUOTE':
      return 'Der Handel ist geschlossen. Angezeigt wird der letzte plausible Kurs der vorherigen Handelssitzung; die Bewertung ist indikativ.';
    case 'WARRANT_QUOTE_TIME_INCONSISTENT':
      return 'Der Datenzeitpunkt des Produktkurses liegt nach dem Abrufzeitpunkt. Der Kurs wird nicht für die Depotbewertung verwendet.';
    case 'WARRANT_QUOTE_CAPABILITY_NOT_CONFIGURED':
      return 'Für das gehaltene Produkt ist derzeit keine verifizierte Kursquelle konfiguriert.';
    case 'WARRANT_LISTING_PROVENANCE_UNAVAILABLE':
      return 'Für diesen Trade ist kein eindeutiges historisches WarrantListing dokumentiert; das System rät keinen Börsenplatz.';
    case 'WARRANT_QUOTE_MISSING':
      return 'Der Quote-Provider hat für das konkrete WarrantListing keinen Kurs geliefert.';
    case 'WARRANT_BID_MISSING':
      return 'Es liegt kein Bid vor. Deshalb werden Marktwert und unrealized P&L nicht geschätzt.';
    case 'WARRANT_QUOTE_CURRENCY_MISMATCH':
      return 'Die Quote-Währung passt nicht zur Währung des dokumentierten WarrantListings.';
    case 'WARRANT_QUOTE_LISTING_MISMATCH':
      return 'Der gelieferte Quote gehört nicht zum dokumentierten WarrantListing.';
    case 'NO_USABLE_WARRANT_QUOTE':
      return 'Keine der geprüften Kursquellen hat einen eindeutig zugeordneten Bid, Handels- oder Schlusskurs geliefert.';
    default:
      return reason;
  }
}

function priceTypeText(type: string | null | undefined): string {
  if (type === 'LAST_TRADE') return 'Letzter Handelspreis';
  if (type === 'PREVIOUS_CLOSE') return 'Schlusspreis des letzten Handelstages';
  return 'Bid';
}

function warningText(warning: string): string {
  if (warning === 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY') {
    return 'Kurszeitpunkt unbekannt – indikative Analyse';
  }
  if (warning === 'REFERENCE_PRICE_INDICATIVE_ANALYSIS_ONLY') {
    return 'Handels- oder Schlusskurs – indikative Analyse';
  }
  return 'Kursdaten veraltet – nur indikative Analyse';
}

export function ProductValuationPanel({ tradeId }: { tradeId: string }) {
  const [value, setValue] = useState<ProductPositionValuationResponse | null>(null);
  const [closed, setClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const position = await tradeManagementApiClient.position(tradeId, signal);
        if (position.is_closed) {
          setClosed(true);
          setValue(null);
          setError(null);
          return;
        }

        const next = await tradeManagementApiClient.productValuation(tradeId, signal);
        setClosed(false);
        setValue(next);
        setError(null);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === 'AbortError') return;
        setError(
          caught instanceof Error
            ? caught.message
            : 'Produktbewertung konnte nicht geladen werden.',
        );
      }
    },
    [tradeId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);

    function onTimelineChanged(event: Event) {
      const detail = (event as CustomEvent<{ tradeId?: string }>).detail;
      if (detail?.tradeId === tradeId) void load();
    }

    window.addEventListener(tradeTimelineChangedEvent, onTimelineChanged);
    return () => {
      controller.abort();
      window.removeEventListener(tradeTimelineChangedEvent, onTimelineChanged);
    };
  }, [load, tradeId]);

  if (closed) return null;

  if (error) {
    return (
      <section className="rounded-xl border border-rose-900 bg-rose-950/20 p-5">
        <h2 className="text-lg font-semibold">Produktbewertung</h2>
        <p className="mt-2 text-sm text-rose-200">{error}</p>
      </section>
    );
  }

  if (value === null) {
    return (
      <section className="rounded-xl border border-slate-800 p-5">
        <h2 className="text-lg font-semibold">Produktbewertung</h2>
        <p className="mt-2 text-sm text-slate-400">Produktkurs wird geprüft …</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-800 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Gehaltenes Produkt</p>
          <h2 className="mt-1 text-lg font-semibold">Produktbewertung</h2>
        </div>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
          {statusText(value)}
        </span>
      </div>

      {(value.analysis_usable || value.valuation_usable) && value.analysis_warning && (
        <div
          role="status"
          className="mt-3 rounded-lg border border-amber-700 bg-amber-950/30 p-3 text-sm text-amber-200"
        >
          <p className="font-medium">{warningText(value.analysis_warning)}</p>
          <p className="mt-1">
            Analyseergebnisse und Empfehlungen auf dieser Kursbasis beziehen sich auf den letzten
            verfügbaren Kurs. Sie entscheiden, wie Sie Quelle und Aktualität für Ihre Auswertung
            gewichten. Dieser Referenzwert garantiert keinen ausführbaren Orderpreis.
          </p>
          <p className="mt-1">
            Kursstand:{' '}
            {value.quote_observed_at
              ? new Date(value.quote_observed_at).toLocaleString('de-DE')
              : 'Zeitpunkt unbekannt'}{' '}
            · {formatQuoteAge(value)}
          </p>
        </div>
      )}

      {value.valuation_usable || value.analysis_usable ? (
        <>
          <p className="mt-3 text-xs text-slate-500">
            {value.status === 'LAST_AVAILABLE' ||
            value.status === 'STALE' ||
            value.status === 'INDICATIVE'
              ? reasonText(value.reason)
              : 'Indikative LONG-Bewertung zum Bid des exakt dokumentierten WarrantListings. Stop und Target werden weiterhin ausschließlich anhand des Underlyings überwacht.'}
          </p>
          {value.reference_price_type && value.reference_price_type !== 'BID' && (
            <p className="mt-3 text-sm">
              {priceTypeText(value.reference_price_type)}:{' '}
              <strong>
                {formatDecimal(value.reference_price ?? null)} {value.currency}
              </strong>{' '}
              · Bid/Ask liegen für diese Beobachtung nicht vor.
            </p>
          )}
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500">Bid</dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(value.bid)} {value.currency}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Ask</dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(value.ask)} {value.currency}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">
                {value.reference_price_type === 'LAST_TRADE'
                  ? 'Indikativer Wert (letzter Handelspreis)'
                  : value.reference_price_type === 'PREVIOUS_CLOSE'
                    ? 'Indikativer Wert (Schlusskurs)'
                    : value.analysis_warning
                      ? 'Indikativer Wert (letzter Bid)'
                      : 'Marktwert (Bid)'}
              </dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(
                  value.analysis_usable ? value.analysis_market_value : value.market_value,
                )}{' '}
                {value.currency}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">
                {value.analysis_warning
                  ? 'Indikativer unrealized gross P&L'
                  : 'Unrealized gross P&L'}
              </dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(
                  value.analysis_usable
                    ? value.analysis_unrealized_gross_pnl
                    : value.unrealized_gross_pnl,
                )}{' '}
                {value.currency}
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-xs text-slate-500">
            Bewertungsquelle: {value.quote_provider ?? value.selected_source ?? '—'} · Instrument{' '}
            {value.provider_identity ?? value.symbol ?? '—'} ·{' '}
            {value.quote_observed_at
              ? new Date(value.quote_observed_at).toLocaleString('de-DE')
              : 'Zeitpunkt unbekannt'}{' '}
            · {formatQuoteAge(value)}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Kursart: {priceTypeText(value.reference_price_type)} · Handelsplatz:{' '}
            {value.quote_venue_mic ?? value.provider_exchange_code ?? 'unbekannt'} ·
            Provider-Platzcode: {value.provider_exchange_code ?? 'unbekannt'} · Feed-Verzögerung:{' '}
            {value.quote_delay_seconds == null ? 'unbekannt' : `${value.quote_delay_seconds} Sek.`}{' '}
            · Handelsstatus: {value.trading_status ?? 'unbekannt'}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Abgerufen:{' '}
            {value.quote_retrieved_at
              ? new Date(value.quote_retrieved_at).toLocaleString('de-DE')
              : 'unbekannt'}{' '}
            · Ausgewertet:{' '}
            {value.quote_assessed_at
              ? new Date(value.quote_assessed_at).toLocaleString('de-DE')
              : 'unbekannt'}
          </p>
          {value.spread_absolute != null && (
            <p className="mt-2 text-sm">
              Spread: {formatDecimal(value.spread_absolute)} {value.currency} /{' '}
              {formatDecimal(value.spread_percent ?? null)} %
            </p>
          )}
          {!value.execution_usable && (
            <p className="mt-2 text-xs text-amber-300">
              Indikative Empfehlungen sind möglich. Dieser Kurs erteilt keine Freigabe zur
              Orderausführung.
            </p>
          )}
        </>
      ) : (
        <div className="mt-3 space-y-2 text-sm text-slate-400">
          <p>{reasonText(value.reason)}</p>
          {value.quote_observed_at && (
            <p>
              Letzter Produktkurs: {new Date(value.quote_observed_at).toLocaleString('de-DE')} ·{' '}
              {formatQuoteAge(value)}
            </p>
          )}
          <p>
            Fehlende oder unzuverlässige Produktdaten werden weder für kursbasierte Empfehlungen
            noch für eine Orderfreigabe verwendet.
          </p>
        </div>
      )}

      {value.source_attempts.length > 0 && (
        <details className="mt-5 text-xs text-slate-500">
          <summary className="cursor-pointer">Geprüfte Kursquellen anzeigen</summary>
          <ol className="mt-3 space-y-2">
            {value.source_attempts.map((attempt, index) => (
              <li
                key={`${attempt.warrant_listing_id ?? index}:${attempt.source}`}
                className="rounded-lg border border-slate-800 p-3"
              >
                <p className="font-medium text-slate-300">
                  {attempt.source} · {attempt.status}
                  {attempt.delayed ? ' · verzögert' : ''}
                </p>
                <p className="mt-1 break-all">{attempt.reason}</p>
                {attempt.reference_price != null && (
                  <p>
                    {priceTypeText(attempt.reference_price_type)}:{' '}
                    {formatDecimal(attempt.reference_price)} {attempt.currency} ·{' '}
                    {attempt.observed_at ? '' : 'Kurszeitpunkt unbekannt'}
                  </p>
                )}
                {attempt.observed_at && (
                  <p className="mt-1">
                    Datenzeitpunkt {new Date(attempt.observed_at).toLocaleString('de-DE')}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
