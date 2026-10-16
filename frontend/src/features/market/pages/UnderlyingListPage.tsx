import { FormEvent, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ErrorNotice, LoadingNotice } from '../components/ApiFeedback';
import { StatusBadge } from '../components/StatusBadge';
import { marketApiClient } from '../services/client';
import {
  UNDERLYING_PAGE_SIZE as PAGE_SIZE,
  readUnderlyingListView,
  underlyingListParams,
  underlyingListUrl,
  withUnderlyingListReturnTo,
  type UnderlyingListView,
} from '../services/underlyingListNavigation';
import type {
  CurrencyResponse,
  LifecycleStatus,
  ProviderInstrumentSearchItemResponse,
  TradingVenueResponse,
  UnderlyingSearchResponse,
} from '../types/api';

function isStockSuggestion(item: ProviderInstrumentSearchItemResponse): boolean {
  return item.instrument_type?.toLowerCase().includes('stock') ?? false;
}

function providerPrefillUrl(item: ProviderInstrumentSearchItemResponse): string {
  const parameters = new URLSearchParams({
    source: item.provider,
    ticker: item.provider_symbol,
    exchange: item.provider_exchange_code,
  });
  if (item.name) parameters.set('name', item.name);
  if (item.isin) parameters.set('isin', item.isin);
  if (item.currency) parameters.set('currency', item.currency);
  return `/underlyings/new?${parameters.toString()}`;
}

export function UnderlyingListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = readUnderlyingListView(searchParams);
  const { query: submittedQuery, lifecycle, venueId, currencyCode, offset } = view;
  const [query, setQuery] = useState(submittedQuery);
  const returnTo = underlyingListUrl(view);

  useEffect(() => setQuery(submittedQuery), [submittedQuery]);

  function updateView(patch: Partial<UnderlyingListView>) {
    setSearchParams(underlyingListParams({ ...view, ...patch }));
  }

  const [result, setResult] = useState<UnderlyingSearchResponse | null>(null);
  const [providerSuggestions, setProviderSuggestions] = useState<
    ProviderInstrumentSearchItemResponse[]
  >([]);
  const [providerError, setProviderError] = useState<unknown>(null);
  const [providerLoading, setProviderLoading] = useState(false);
  const [venues, setVenues] = useState<TradingVenueResponse[]>([]);
  const [currencies, setCurrencies] = useState<CurrencyResponse[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      marketApiClient.listTradingVenues(controller.signal),
      marketApiClient.listCurrencies(controller.signal),
    ])
      .then(([venueResponse, currencyResponse]) => {
        setVenues(venueResponse.items);
        setCurrencies(currencyResponse.items);
      })
      .catch((reason: unknown) => {
        if (
          !controller.signal.aborted &&
          !(reason instanceof DOMException && reason.name === 'AbortError')
        )
          setError(reason);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setProviderError(null);
    setProviderSuggestions([]);
    setProviderLoading(false);

    void (async () => {
      try {
        const localResult = await marketApiClient.searchUnderlyings(
          {
            query: submittedQuery || undefined,
            lifecycleStatus: lifecycle || undefined,
            tradingVenueId: venueId || undefined,
            currencyCode: currencyCode || undefined,
            offset,
            limit: PAGE_SIZE,
          },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        // A deleted or filtered-out last item can make the remembered page empty.
        // Preserve filters and return to the nearest page that still exists.
        if (offset > 0 && offset >= localResult.total) {
          const lastOffset = Math.max(0, Math.ceil(localResult.total / PAGE_SIZE) - 1) * PAGE_SIZE;
          setSearchParams(
            (current) =>
              underlyingListParams({ ...readUnderlyingListView(current), offset: lastOffset }),
            { replace: true },
          );
          return;
        }
        setResult(localResult);
        setLoading(false);

        const canUseProviderFallback =
          submittedQuery.length >= 2 &&
          localResult.total === 0 &&
          offset === 0 &&
          !venueId &&
          !currencyCode &&
          lifecycle !== 'INACTIVE';
        if (!canUseProviderFallback) return;

        setProviderLoading(true);
        try {
          const providerResult = await marketApiClient.searchProviderInstruments(
            submittedQuery,
            10,
            controller.signal,
          );
          if (!controller.signal.aborted) setProviderSuggestions(providerResult.items);
        } catch (reason: unknown) {
          if (
            !controller.signal.aborted &&
            !(reason instanceof DOMException && reason.name === 'AbortError')
          ) {
            setProviderError(reason);
          }
        } finally {
          if (!controller.signal.aborted) setProviderLoading(false);
        }
      } catch (reason: unknown) {
        if (
          !controller.signal.aborted &&
          !(reason instanceof DOMException && reason.name === 'AbortError')
        )
          setError(reason);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [submittedQuery, lifecycle, venueId, currencyCode, offset, setSearchParams]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    updateView({ offset: 0, query: query.trim() });
  }

  return (
    <section className="w-full space-y-6" aria-labelledby="underlyings-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-400">Stammdaten</p>
          <h1 id="underlyings-title" className="mt-2 text-3xl font-semibold">
            Basiswerte
          </h1>
          <p className="mt-2 text-slate-400">
            Aktien und ihre börslichen Notierungen zentral verwalten.
          </p>
        </div>
        <Link
          to={withUnderlyingListReturnTo('/underlyings/new', returnTo)}
          className="rounded-lg bg-sky-500 px-4 py-2.5 font-semibold text-slate-950 hover:bg-sky-400"
        >
          Basiswert anlegen
        </Link>
      </div>
      <form
        onSubmit={submitSearch}
        className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 md:grid-cols-5"
      >
        <label className="md:col-span-2">
          <span className="mb-1 block text-sm text-slate-300">Suche</span>
          <input
            aria-label="Suche"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name, Ticker, ISIN oder WKN"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
          <span className="mt-1 block text-xs text-slate-500">
            Ohne lokalen Treffer wird automatisch read-only bei EODHD gesucht.
          </span>
        </label>
        <label>
          <span className="mb-1 block text-sm text-slate-300">Status</span>
          <select
            aria-label="Status"
            value={lifecycle}
            onChange={(e) => {
              updateView({ lifecycle: e.target.value as LifecycleStatus | '', offset: 0 });
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="">Alle</option>
            <option value="ACTIVE">Aktiv</option>
            <option value="INACTIVE">Deaktiviert</option>
          </select>
        </label>
        <label>
          <span className="mb-1 block text-sm text-slate-300">Markt</span>
          <select
            aria-label="Markt"
            value={venueId}
            onChange={(e) => {
              updateView({ venueId: e.target.value, offset: 0 });
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="">Alle</option>
            {venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} · {v.mic}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block text-sm text-slate-300">Währung</span>
          <select
            aria-label="Währung"
            value={currencyCode}
            onChange={(e) => {
              updateView({ currencyCode: e.target.value, offset: 0 });
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="">Alle</option>
            {currencies.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} · {c.name}
              </option>
            ))}
          </select>
        </label>
        <button className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-800 md:col-start-5">
          Suchen
        </button>
      </form>
      {error ? (
        <ErrorNotice error={error} />
      ) : loading ? (
        <LoadingNotice />
      ) : result && result.items.length === 0 ? (
        <div className="space-y-4 rounded-xl border border-dashed border-slate-700 p-6">
          <div className="text-center">
            <h2 className="font-semibold">Keine lokalen Basiswerte gefunden</h2>
            <p className="mt-2 text-sm text-slate-400">
              {submittedQuery
                ? 'Die lokale Suche ist leer. EODHD wird nur als externer Vorschlagskatalog verwendet.'
                : 'Filter anpassen oder einen neuen Basiswert anlegen.'}
            </p>
          </div>

          {providerLoading && (
            <p role="status" className="text-center text-sm text-slate-400">
              EODHD wird durchsucht …
            </p>
          )}
          {providerError !== null && (
            <p
              role="status"
              className="rounded-lg border border-amber-900 p-3 text-sm text-amber-200"
            >
              Die lokale Suche funktioniert. EODHD konnte für diesen Suchlauf nicht abgefragt
              werden.
            </p>
          )}
          {providerSuggestions.length > 0 && (
            <section aria-labelledby="eodhd-suggestions-title" className="space-y-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-amber-400">Externe Vorschläge</p>
                <h3 id="eodhd-suggestions-title" className="mt-1 font-semibold">
                  EODHD-Treffer – vor Übernahme prüfen
                </h3>
              </div>
              <div className="grid gap-3">
                {providerSuggestions.map((item) => {
                  const stockSuggestion = isStockSuggestion(item);
                  return (
                    <article
                      key={`${item.provider_symbol}:${item.provider_exchange_code}`}
                      className="rounded-lg border border-slate-800 bg-slate-950/50 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{item.name ?? item.provider_symbol}</p>
                          <p className="mt-1 text-sm text-slate-400">
                            {item.provider_symbol} · {item.provider_exchange_code}
                            {item.currency ? ` · ${item.currency}` : ''}
                            {item.isin ? ` · ${item.isin}` : ''}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            Typ: {item.instrument_type ?? 'nicht angegeben'} · Quelle:{' '}
                            {item.provider}
                          </p>
                        </div>
                        {stockSuggestion ? (
                          <Link
                            to={withUnderlyingListReturnTo(providerPrefillUrl(item), returnTo)}
                            className="rounded-lg border border-amber-700 px-3 py-2 text-sm text-amber-100"
                          >
                            Als Basiswert übernehmen
                          </Link>
                        ) : (
                          <span className="max-w-xs text-right text-xs text-slate-500">
                            Kein Aktien-Treffer – wird nicht als STOCK-Basiswert übernommen.
                          </span>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          )}
        </div>
      ) : result ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Primäre Notierung</th>
                  <th className="px-4 py-3">ISIN</th>
                  <th className="px-4 py-3">WKN</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Letzte Änderung</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {result.items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-900/70">
                    <td className="px-4 py-4">
                      <Link
                        className="font-medium text-sky-300 hover:underline"
                        to={withUnderlyingListReturnTo(`/underlyings/${item.id}`, returnTo)}
                      >
                        {item.name}
                      </Link>
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {item.primary_listing
                        ? `${item.primary_listing.ticker} · ${item.primary_listing.trading_venue_name} · ${item.primary_listing.currency_code}`
                        : '—'}
                    </td>
                    <td className="px-4 py-4 font-mono text-xs">{item.isin ?? '—'}</td>
                    <td className="px-4 py-4 font-mono text-xs">{item.wkn ?? '—'}</td>
                    <td className="px-4 py-4">
                      <div className="flex gap-2">
                        <StatusBadge status={item.lifecycle_status} />
                        <StatusBadge status={item.quality_status} />
                      </div>
                    </td>
                    <td className="px-4 py-4 text-slate-400">
                      {new Date(item.updated_at).toLocaleString('de-DE')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span role="status" aria-live="polite" aria-atomic="true">
              {result.total} Treffer · Seite {offset / PAGE_SIZE + 1} von{' '}
              {Math.max(1, Math.ceil(result.total / PAGE_SIZE))}
            </span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => updateView({ offset: Math.max(0, offset - PAGE_SIZE) })}
                className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
              >
                Zurück
              </button>
              <button
                disabled={offset + PAGE_SIZE >= result.total}
                onClick={() => updateView({ offset: offset + PAGE_SIZE })}
                className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
              >
                Weiter
              </button>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
