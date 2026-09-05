import { FormEvent, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';
import { ExistingTradePlanPage } from './ExistingTradePlanPage';
import { TradePlanPage as BaseTradePlanPage } from './TradePlanPage';

function underlyingLabel(item: UnderlyingSummaryResponse): string {
  const ticker = item.primary_listing?.ticker;
  const identifiers = [ticker, item.isin, item.wkn].filter(Boolean).join(' · ');
  return identifiers ? `${item.name} · ${identifiers}` : item.name;
}

export function TradePlanWorkflowPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnderlyingSummaryResponse[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);

  const selectedUnderlyingId = searchParams.get('underlying_id') ?? '';
  const existingTradePlanId = searchParams.get('trade_plan_id') ?? '';
  const candidateOrigin =
    searchParams.has('candidate_id') && searchParams.has('candidate_evaluation_id');

  async function searchUnderlyings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;

    setSearching(true);
    setSearchMessage(null);
    try {
      const response = await marketApiClient.searchUnderlyings({
        query: value,
        lifecycleStatus: 'ACTIVE',
        limit: 10,
      });
      setResults(response.items);
      if (response.items.length === 0) {
        setSearchMessage('Keine aktiven Basiswerte gefunden.');
      }
    } catch (error: unknown) {
      setSearchMessage(
        error instanceof Error ? error.message : 'Basiswertsuche konnte nicht ausgeführt werden.',
      );
    } finally {
      setSearching(false);
    }
  }

  function selectUnderlying(item: UnderlyingSummaryResponse) {
    const next = new URLSearchParams(searchParams);
    next.set('underlying_id', item.id);
    next.delete('candidate_id');
    next.delete('candidate_evaluation_id');
    next.delete('trade_plan_id');
    setSearchParams(next);
    setResults([]);
    setQuery(underlyingLabel(item));
    setSearchMessage(`Basiswert gewählt: ${underlyingLabel(item)}`);
  }

  if (existingTradePlanId) {
    return <ExistingTradePlanPage tradePlanId={existingTradePlanId} />;
  }

  return (
    <div className="space-y-6">
      {!candidateOrigin && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">Basiswert für manuellen TradePlan auswählen</h2>
          <p className="mt-1 text-sm text-slate-400">
            Suche nach Name, Ticker, ISIN oder WKN. Die technische Underlying-ID wird intern
            übernommen und muss nicht eingegeben werden.
          </p>
          <form onSubmit={(event) => void searchUnderlyings(event)} className="mt-4 flex gap-2">
            <input
              aria-label="Basiswert suchen"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="z. B. Apple, AAPL, ISIN oder WKN"
              className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            />
            <button
              type="submit"
              disabled={searching || query.trim() === ''}
              className="rounded-lg border border-sky-700 px-4 py-2 disabled:opacity-40"
            >
              Suchen
            </button>
          </form>

          {searchMessage && <p className="mt-3 text-sm text-slate-400">{searchMessage}</p>}

          {results.length > 0 && (
            <ul className="mt-4 space-y-2">
              {results.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => selectUnderlying(item)}
                    className="w-full rounded-lg border border-slate-800 p-3 text-left hover:border-sky-700"
                  >
                    <span className="font-medium">{item.name}</span>
                    <span className="mt-1 block text-xs text-slate-500">
                      {[item.primary_listing?.ticker, item.isin, item.wkn]
                        .filter(Boolean)
                        .join(' · ') || 'Keine weiteren Kennungen'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {selectedUnderlyingId && (
            <p className="mt-4 break-all text-xs text-slate-500">
              Technische Referenz übernommen: {selectedUnderlyingId}
            </p>
          )}
        </section>
      )}

      <BaseTradePlanPage key={searchParams.toString()} />
    </div>
  );
}
