import { useEffect, useState } from 'react';
import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';

type Props = {
  value: string;
  selectedLabel?: string;
  onChange: (id: string, label: string) => void;
};

export function UnderlyingSearchCombobox({ value, selectedLabel, onChange }: Props) {
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [items, setItems] = useState<UnderlyingSummaryResponse[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 10;

  useEffect(() => {
    const controller = new AbortController();

    void marketApiClient
      .searchUnderlyings(
        {
          query: appliedQuery || undefined,
          lifecycleStatus: 'ACTIVE',
          offset,
          limit,
        },
        controller.signal,
      )
      .then((page) => {
        setItems(page.items);
        setTotal(page.total);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          console.error(error);
        }
      });

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
        aria-label="Basiswert filtern"
        value={value}
        onChange={(event) => {
          const selected = items.find((item) => item.id === event.target.value);
          onChange(event.target.value, selected?.name ?? '');
        }}
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
      >
        <option value="">Alle Basiswerte</option>
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
    </div>
  );
}
