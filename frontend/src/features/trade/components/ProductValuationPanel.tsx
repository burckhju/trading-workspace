import { useCallback, useEffect, useState } from 'react';

import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import type { ProductPositionValuationResponse } from '../types/api';

function formatDecimal(value: string | null): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 10 }).format(Number(value));
}

function statusText(value: ProductPositionValuationResponse): string {
  switch (value.status) {
    case 'AVAILABLE':
      return 'Produktkurs verfügbar';
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
    case 'WARRANT_QUOTE_CAPABILITY_NOT_CONFIGURED':
      return 'Für das gehaltene WarrantListing ist derzeit kein verifizierter Bid/Ask-Transport konfiguriert.';
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
      return 'Keine der geprüften Kursquellen hat einen belastbaren Bid für das dokumentierte Listing geliefert.';
    default:
      return reason;
  }
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

      {value.status === 'AVAILABLE' ? (
        <>
          <p className="mt-3 text-xs text-slate-500">
            Indikative LONG-Bewertung zum Bid des exakt dokumentierten WarrantListings. Stop und
            Target werden weiterhin ausschließlich anhand des Underlyings überwacht.
          </p>
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
              <dt className="text-slate-500">Marktwert (Bid)</dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(value.market_value)} {value.currency}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Unrealized gross P&amp;L</dt>
              <dd className="mt-1 font-medium">
                {formatDecimal(value.unrealized_gross_pnl)} {value.currency}
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-xs text-slate-500">
            Bewertungsquelle: {value.selected_source ?? '—'} · Quote {value.symbol ?? '—'} ·{' '}
            {value.quote_observed_at
              ? new Date(value.quote_observed_at).toLocaleString('de-DE')
              : 'Zeitpunkt unbekannt'}
          </p>
        </>
      ) : (
        <div className="mt-3 space-y-2 text-sm text-slate-400">
          <p>{reasonText(value.reason)}</p>
          <p>
            Fehlende Produktdaten werden nicht als unauffällige Position interpretiert und erzeugen
            keine automatische Kauf- oder Verkaufsentscheidung.
          </p>
        </div>
      )}

      {value.source_attempts.length > 0 && (
        <details className="mt-5 text-xs text-slate-500">
          <summary className="cursor-pointer">Geprüfte Kursquellen anzeigen</summary>
          <ol className="mt-3 space-y-2">
            {value.source_attempts.map((attempt) => (
              <li key={attempt.source} className="rounded-lg border border-slate-800 p-3">
                <p className="font-medium text-slate-300">
                  {attempt.source} · {attempt.status}
                  {attempt.delayed ? ' · verzögert' : ''}
                </p>
                <p className="mt-1 break-all">{attempt.reason}</p>
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
