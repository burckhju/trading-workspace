import { useEffect, useState } from 'react';
import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';

interface Props {
  value: string;
  label?: string;
  disabled?: boolean;
  onChange: (id: string) => void;
}

/** Administration selects existing securities only; searching never invokes a provider. */
export function ExistingUnderlyingSelector({ value, label, disabled, onChange }: Props) {
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<UnderlyingSummaryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    marketApiClient
      .searchUnderlyings(
        { query: search || undefined, lifecycleStatus: 'ACTIVE', offset, limit: 20 },
        controller.signal,
      )
      .then((page) => {
        if (controller.signal.aborted) return;
        setItems(page.items);
        setTotal(page.total);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : 'Basiswerte nicht lesbar.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [search, offset]);
  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-2">
      <legend className="mb-2 text-sm">Vorhandenen Basiswert / ETF auswählen</legend>
      <div className="flex gap-2">
        <input
          aria-label="Basiswert suchen"
          className="min-w-0 flex-1 rounded border border-slate-600 bg-slate-950 p-2"
          placeholder="Name, ISIN, WKN oder Ticker"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button
          type="button"
          className="rounded border border-slate-600 px-3 py-2"
          onClick={() => {
            setSearch(query.trim());
            setOffset(0);
          }}
        >
          Suchen
        </button>
      </div>
      <select
        aria-label="Basiswert / ETF"
        className="w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Bitte wählen</option>
        {value && !items.some((item) => item.id === value) && (
          <option value={value}>{label ?? value}</option>
        )}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} · {item.type}
            {item.isin ? ` · ${item.isin}` : ''}
          </option>
        ))}
      </select>
      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-400">
        <span>
          {loading ? 'Lokale Stammdaten werden gelesen …' : `${total} vorhandene Basiswerte`}
        </span>
        <div className="flex gap-3">
          <button
            type="button"
            disabled={offset === 0 || loading}
            onClick={() => setOffset(Math.max(0, offset - 20))}
          >
            Vorherige
          </button>
          <button
            type="button"
            disabled={offset + 20 >= total || loading}
            onClick={() => setOffset(offset + 20)}
          >
            Weitere
          </button>
        </div>
      </div>
      {error && <p role="alert">{error}</p>}
    </fieldset>
  );
}
