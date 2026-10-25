import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingSummaryResponse } from '../../market/types/api';
import { ExistingTradePlanPage } from './ExistingTradePlanPage';
import { TradePlanPage as BaseTradePlanPage } from './TradePlanPage';

export function TradePlanWorkflowPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnderlyingSummaryResponse[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const searchRequest = useRef<AbortController | null>(null);
  const currentContext = searchParams.toString();
  const selectedUnderlyingId = searchParams.get('underlying_id') ?? '';
  const existingTradePlanId = searchParams.get('trade_plan_id') ?? '';
  // A partial candidate handoff must be validated, never treated as a manual origin.
  const candidateOrigin =
    searchParams.has('candidate_id') || searchParams.has('candidate_evaluation_id');

  useEffect(() => {
    setResults([]);
    setSearchMessage(null);
    setSearching(false);
    return () => searchRequest.current?.abort();
  }, [currentContext]);

  async function searchUnderlyings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    searchRequest.current?.abort();
    const controller = new AbortController();
    searchRequest.current = controller;
    setSearching(true);
    setSearchMessage(null);
    setResults([]);
    try {
      const response = await marketApiClient.searchUnderlyings(
        { query: value, lifecycleStatus: 'ACTIVE', limit: 10 },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setResults(response.items);
      if (response.items.length === 0) setSearchMessage('Keine aktiven Basiswerte gefunden.');
    } catch (error: unknown) {
      if (!controller.signal.aborted)
        setSearchMessage(
          error instanceof Error ? error.message : 'Basiswertsuche konnte nicht ausgeführt werden.',
        );
    } finally {
      if (!controller.signal.aborted) setSearching(false);
    }
  }

  function selectUnderlying(item: UnderlyingSummaryResponse) {
    searchRequest.current?.abort();
    setSearchParams(new URLSearchParams({ underlying_id: item.id }));
    setResults([]);
  }

  if (
    (searchParams.has('trade_plan_id') &&
      (!existingTradePlanId.trim() || searchParams.getAll('trade_plan_id').length !== 1)) ||
    (searchParams.has('trade_plan_version_id') && !existingTradePlanId)
  ) {
    return (
      <section className="space-y-3">
        <h1 className="text-2xl font-semibold">TradePlan-Kontext prüfen</h1>
        <p role="alert">
          Plan und Version wurden unvollständig oder mehrdeutig übergeben. Bitte einen Plan aus der
          Übersicht öffnen.
        </p>
        <Link to="/trade-plans/overview" className="underline">
          Zur TradePlan-Übersicht
        </Link>
      </section>
    );
  }
  if (existingTradePlanId) return <ExistingTradePlanPage tradePlanId={existingTradePlanId} />;

  return (
    <main className="min-w-0 space-y-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-007 · Anlage</p>
        <h1 className="mt-1 text-2xl font-semibold">Neuen TradePlan anlegen</h1>
        <p className="mt-2 text-sm text-slate-400">
          Basiswert und Ursprung einmal wählen, danach den Planinhalt erfassen.
        </p>
      </header>
      {!candidateOrigin && !searchParams.has('underlying_id') && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">Basiswert für manuellen TradePlan auswählen</h2>
          <p className="mt-1 text-sm text-slate-400">Suche nach Name, Ticker, ISIN oder WKN.</p>
          <form
            onSubmit={(event) => void searchUnderlyings(event)}
            className="mt-4 flex flex-wrap gap-2"
          >
            <input
              aria-label="Basiswert suchen"
              value={query}
              onChange={(event) => {
                searchRequest.current?.abort();
                setSearching(false);
                setResults([]);
                setSearchMessage(null);
                setQuery(event.target.value);
              }}
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
          {searching && (
            <p role="status" className="mt-3 text-sm">
              Basiswerte werden gesucht …
            </p>
          )}
          {searchMessage && (
            <p role="status" className="mt-3 text-sm text-slate-400">
              {searchMessage}
            </p>
          )}
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
                    <span className="mt-1 block text-xs text-slate-400">
                      {[item.primary_listing?.ticker, item.isin, item.wkn]
                        .filter(Boolean)
                        .join(' · ') || 'Keine weiteren Kennungen'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-sm">
            <Link to="/candidates" className="underline">
              Aus gespeicherter Kandidatenbewertung planen
            </Link>
          </p>
        </section>
      )}
      {(candidateOrigin || selectedUnderlyingId || searchParams.has('underlying_id')) && (
        <BaseTradePlanPage key={searchParams.toString()} />
      )}
    </main>
  );
}
