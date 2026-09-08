import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import {
  tradePlanOverviewApiClient,
  type TradePlanOverviewItem,
} from '../../trade_plan/services/overviewClient';
import { ProductSelectionPage } from './ProductSelectionPage';

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

export function ProductSelectionWorkflowPage() {
  const [searchParams] = useSearchParams();
  const hasContext =
    Boolean(searchParams.get('run_id')?.trim()) ||
    (Boolean(searchParams.get('trade_plan_id')?.trim()) &&
      Boolean(searchParams.get('trade_plan_version_id')?.trim()));
  const [plans, setPlans] = useState<TradePlanOverviewItem[]>([]);
  const [underlyings, setUnderlyings] = useState<Record<string, UnderlyingDetailResponse>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(!hasContext);

  useEffect(() => {
    if (hasContext) return;
    const controller = new AbortController();

    async function load() {
      try {
        const items = await tradePlanOverviewApiClient.list(controller.signal);
        const approved = items.filter((item) => item.status === 'APPROVED');
        setPlans(approved);

        const uniqueUnderlyingIds = [...new Set(approved.map((item) => item.underlying_id))];
        const resolved = await Promise.all(
          uniqueUnderlyingIds.map(async (id) => {
            try {
              return [id, await marketApiClient.getUnderlying(id, controller.signal)] as const;
            } catch {
              return null;
            }
          }),
        );
        setUnderlyings(
          Object.fromEntries(
            resolved.filter(
              (item): item is readonly [string, UnderlyingDetailResponse] => item !== null,
            ),
          ),
        );
      } catch (error: unknown) {
        if (!controller.signal.aborted) {
          setMessage(
            error instanceof Error
              ? error.message
              : 'Freigegebene TradePlans konnten nicht geladen werden.',
          );
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [hasContext]);

  const sortedPlans = useMemo(
    () => [...plans].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [plans],
  );

  if (hasContext) return <ProductSelectionPage />;

  return (
    <main className="w-full space-y-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-008 · Einstieg</p>
        <h1 className="mt-1 text-2xl font-semibold">Produktauswahl starten</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Wähle einen freigegebenen TradePlan. Technische IDs werden automatisch übernommen und
          müssen nicht mehr manuell eingegeben werden.
        </p>
      </header>

      {message && (
        <p role="status" className="rounded-lg border border-rose-900 p-3 text-sm text-rose-200">
          {message}
        </p>
      )}
      {loading && (
        <p className="text-sm text-slate-400">Freigegebene TradePlans werden geladen …</p>
      )}

      {!loading && sortedPlans.length === 0 && !message && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="font-semibold">Kein freigegebener TradePlan verfügbar</h2>
          <p className="mt-2 text-sm text-slate-400">
            Für eine Produktauswahl muss zuerst eine TradePlan-Version den Status APPROVED haben.
          </p>
          <Link
            to="/trade-plans/overview"
            className="mt-4 inline-block rounded-lg border border-sky-700 px-4 py-2 text-sm"
          >
            Zu den TradePlans
          </Link>
        </section>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {sortedPlans.map((plan) => {
          const underlying = underlyings[plan.underlying_id];
          const identifiers = [
            underlying?.primary_listing?.ticker,
            underlying?.isin,
            underlying?.wkn,
          ].filter(Boolean);
          const target = new URLSearchParams({
            trade_plan_id: plan.id,
            trade_plan_version_id: plan.latest_version_id,
          });
          return (
            <article key={plan.id} className="rounded-xl border border-slate-800 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    {tradePlanReference(plan.id)}
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">
                    {underlying?.name ?? 'Basiswert'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {identifiers.join(' · ') || 'Keine sichtbaren Kennungen'}
                  </p>
                </div>
                <span className="rounded-full border border-emerald-800 px-3 py-1 text-xs text-emerald-300">
                  APPROVED
                </span>
              </div>

              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Version</dt>
                  <dd className="mt-1">{plan.latest_version}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Freigabe-Kontext</dt>
                  <dd className="mt-1">Aktuell freigegebene Version</dd>
                </div>
              </dl>

              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  to={`/product-selection?${target.toString()}`}
                  className="rounded-lg border border-emerald-700 px-4 py-2 text-sm"
                >
                  Produktauswahl für diesen TradePlan öffnen
                </Link>
                <Link
                  to={`/trade-plans?trade_plan_id=${encodeURIComponent(plan.id)}`}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
                >
                  TradePlan ansehen
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}
