import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type {
  ProviderInstrumentSearchItemResponse,
  UnderlyingSummaryResponse,
} from '../../market/types/api';

type Props = {
  value: string;
  selectedLabel?: string;
  onChange: (id: string, label: string) => void;
  selectLabel?: string;
  emptyOptionLabel?: string;
  required?: boolean;
};

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

export function UnderlyingSearchCombobox({
  value,
  selectedLabel,
  onChange,
  selectLabel = 'Basiswert filtern',
  emptyOptionLabel = 'Alle Basiswerte',
  required = false,
}: Props) {
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [items, setItems] = useState<UnderlyingSummaryResponse[]>([]);
  const [providerSuggestions, setProviderSuggestions] = useState<
    ProviderInstrumentSearchItemResponse[]
  >([]);
  const [providerLoading, setProviderLoading] = useState(false);
  const [providerError, setProviderError] = useState(false);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 10;

  useEffect(() => {
    const controller = new AbortController();
    setProviderSuggestions([]);
    setProviderLoading(false);
    setProviderError(false);

    void (async () => {
      try {
        const page = await marketApiClient.searchUnderlyings(
          {
            query: appliedQuery || undefined,
            lifecycleStatus: 'ACTIVE',
            offset,
            limit,
          },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setItems(page.items);
        setTotal(page.total);

        const canUseProviderFallback = appliedQuery.length >= 2 && page.total === 0 && offset === 0;
        if (!canUseProviderFallback) return;

        setProviderLoading(true);
        try {
          const providerResult = await marketApiClient.searchProviderInstruments(
            appliedQuery,
            10,
            controller.signal,
          );
          if (!controller.signal.aborted) setProviderSuggestions(providerResult.items);
        } catch (error: unknown) {
          if (!(error instanceof DOMException && error.name === 'AbortError')) {
            setProviderError(true);
          }
        } finally {
          if (!controller.signal.aborted) setProviderLoading(false);
        }
      } catch (error: unknown) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          console.error(error);
        }
      }
    })();

    return () => controller.abort();
  }, [appliedQuery, offset]);

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          aria-label="Basiswert suchen"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
          placeholder="Name, ISIN, WKN oder Ticker"
        />
        <button
          type="button"
          onClick={() => {
            setAppliedQuery(query.trim());
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 px-3 py-2"
        >
          Suchen
        </button>
      </div>
      <select
        required={required}
        aria-label={selectLabel}
        value={value}
        onChange={(event) => {
          const selected = items.find((item) => item.id === event.target.value);
          onChange(event.target.value, selected?.name ?? '');
        }}
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
      >
        <option value="">{emptyOptionLabel}</option>
        {value && !items.some((item) => item.id === value) ? (
          <option value={value}>{selectedLabel || value}</option>
        ) : null}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
            {item.primary_listing ? ` · ${item.primary_listing.ticker}` : ''}
          </option>
        ))}
      </select>
      <div className="flex justify-between text-xs text-slate-400">
        <span>{total} Treffer</span>
        <span className="flex gap-3">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            Zurück
          </button>
          <button
            type="button"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            Weiter
          </button>
        </span>
      </div>

      {providerLoading ? (
        <p role="status" className="text-xs text-slate-400">
          Keine lokalen Treffer. EODHD wird durchsucht …
        </p>
      ) : null}
      {providerError ? (
        <p role="status" className="text-xs text-amber-300">
          Die lokale Suche funktioniert. EODHD konnte nicht abgefragt werden.
        </p>
      ) : null}
      {providerSuggestions.length > 0 ? (
        <div className="space-y-2 rounded-lg border border-amber-900/60 p-3">
          <p className="text-xs font-medium text-amber-300">
            EODHD-Treffer sind noch keine Workspace-Basiswerte.
          </p>
          {providerSuggestions.map((item) => {
            const stockSuggestion = isStockSuggestion(item);
            return (
              <div
                key={`${item.provider_symbol}:${item.provider_exchange_code}`}
                className="flex items-start justify-between gap-3 text-xs"
              >
                <span className="min-w-0 text-slate-300">
                  <span className="block truncate font-medium text-slate-200">
                    {item.name ?? item.provider_symbol}
                  </span>
                  <span className="text-slate-500">
                    {item.provider_symbol} · {item.provider_exchange_code}
                    {item.currency ? ` · ${item.currency}` : ''}
                    {item.instrument_type ? ` · ${item.instrument_type}` : ''}
                  </span>
                </span>
                {stockSuggestion ? (
                  <Link
                    to={providerPrefillUrl(item)}
                    className="shrink-0 rounded border border-amber-700 px-2 py-1 text-amber-100"
                  >
                    Basiswert anlegen
                  </Link>
                ) : (
                  <span className="shrink-0 text-slate-500">Nicht als STOCK übernehmen</span>
                )}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
