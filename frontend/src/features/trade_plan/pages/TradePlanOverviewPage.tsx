import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import {
  tradePlanOverviewApiClient,
  type TradePlanOverviewItem,
} from '../services/overviewClient';

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

export function TradePlanOverviewPage() {
  const [items, setItems] = useState<TradePlanOverviewItem[]>([]);
  const [underlyings, setUnderlyings] = useState<Record<string, UnderlyingDetailResponse>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const plans = await tradePlanOverviewApiClient.list(controller.signal);
        setItems(plans);
        const uniqueIds = [...new Set(plans.map((item) => item.underlying_id))];
        const resolved = await Promise.all(
          uniqueIds.map(async (id) => {
            try {
              return [id, await marketApiClient.getUnderlying(id, controller.signal)] as const;
            } catch {
              return null;
            }
          }),
        );
        setUnderlyings(
          Object.fromEntries(resolved.filter((item): item is readonly [string, UnderlyingDetailResponse] => item !== null)),
        );
      } catch (error: unknown) {
        if (!controller.signal.aborted) {
          setMessage(error instanceof Error ? error.message : 'TradePlans konnten nicht geladen werden.');
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  return (
    <main className="w-full space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">FT-007 · Übersicht</p>
          <h1 className="mt-1 text-2xl font-semibold">TradePlans</h1>
          <p className="mt-2 text-sm text-slate-400">
            Vorhandene TradePlans nach Erstellzeit, mit aktuellem Status und Version.
          </p>
        </div>
        <Link to="/trade-plans" className="rounded-lg border border-sky-700 px-4 py-2 text-sm">
          Neuen TradePlan anlegen
        </Link>
      </header>

      {message && <p role="status" className="rounded-lg border border-red-900 p-3 text-sm">{message}</p>}
      {loading && <p className="text-sm text-slate-400">TradePlans werden geladen …</p>}
      {!loading && items.length === 0 && !message && (
        <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
          Noch keine TradePlans vorhanden.
        </p>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const underlying = underlyings[item.underlying_id];
          const ticker = underlying?.primary_listing?.ticker;
          return (
            <article key={item.id} className="rounded-xl border border-slate-800 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{tradePlanReference(item.id)}</p>
                  <h2 className="mt-1 text-lg font-semibold">{underlying?.name ?? 'Basiswert wird nicht aufgelöst'}</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {[ticker, underlying?.isin, underlying?.wkn].filter(Boolean).join(' · ') || 'Keine sichtbaren Kennungen'}
                  </p>
                </div>
                <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">{item.status}</span>
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                <div><dt className="text-slate-500">Version</dt><dd className="mt-1">{item.latest_version}</dd></div>
                <div><dt className="text-slate-500">Ursprung</dt><dd className="mt-1">{item.origin_type === 'MANUAL' ? 'Manuell' : 'CandidateEvaluation'}</dd></div>
                <div><dt className="text-slate-500">Erstellt</dt><dd className="mt-1">{new Date(item.created_at).toLocaleString('de-DE')}</dd></div>
              </dl>
              <div className="mt-4">
                <Link
                  to={`/trade-plans?trade_plan_id=${encodeURIComponent(item.id)}`}
                  className="inline-flex rounded-lg border border-slate-600 px-4 py-2 text-sm"
                >
                  Öffnen
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}
