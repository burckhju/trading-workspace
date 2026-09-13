import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { PlanPurchaseStatus } from '../components/PlanPurchaseStatus';
import { purchaseLabels } from '../services/purchaseStatus';
import {
  tradePlanOverviewApiClient,
  type TradePlanOverviewItem,
  type PurchaseStatus,
} from '../services/overviewClient';

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

export function TradePlanOverviewPage() {
  const [items, setItems] = useState<TradePlanOverviewItem[]>([]);
  const [underlyings, setUnderlyings] = useState<Record<string, UnderlyingDetailResponse>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [revision, setRevision] = useState(0);
  const [filter, setFilter] = useState<PurchaseStatus | 'ALL'>('ALL');
  const visible = items.filter(
    (item) => filter === 'ALL' || (item.execution?.status ?? 'UNKNOWN') === filter,
  );

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setMessage(null);
      try {
        const plans = await tradePlanOverviewApiClient.list(controller.signal);
        if (controller.signal.aborted) return;
        setItems(plans);
        const uniqueIds = [
          ...new Set(
            plans.filter((item) => !item.underlying_name).map((item) => item.underlying_id),
          ),
        ];
        const resolved = await Promise.all(
          uniqueIds.map(async (id) => {
            try {
              return [id, await marketApiClient.getUnderlying(id, controller.signal)] as const;
            } catch {
              return null;
            }
          }),
        );
        if (controller.signal.aborted) return;
        setUnderlyings(
          Object.fromEntries(
            resolved.filter(
              (item): item is readonly [string, UnderlyingDetailResponse] => item !== null,
            ),
          ),
        );
      } catch (error: unknown) {
        if (!controller.signal.aborted) {
          setItems([]);
          setMessage(
            error instanceof Error ? error.message : 'TradePlans konnten nicht geladen werden.',
          );
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [revision]);

  return (
    <main className="w-full space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">FT-007 · Übersicht</p>
          <h1 className="mt-1 text-2xl font-semibold">TradePlans</h1>
          <p className="mt-2 text-sm text-slate-400">
            Planfreigabe und tatsächliche Käufe sind getrennt. APPROVED bedeutet noch nicht gekauft.
          </p>
        </div>
        <Link to="/trade-plans" className="rounded-lg border border-sky-700 px-4 py-2 text-sm">
          Neuen TradePlan anlegen
        </Link>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block">Nach Kaufstatus filtern</span>
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as PurchaseStatus | 'ALL')}
            className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2"
          >
            <option value="ALL">Alle TradePlans</option>
            {Object.entries(purchaseLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => setRevision((value) => value + 1)}
          disabled={loading}
          className="rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-50"
        >
          Übersicht aktualisieren
        </button>
        {!loading && !message && (
          <p role="status" className="text-sm text-slate-400">
            {visible.length} von {items.length} TradePlans
          </p>
        )}
      </div>
      {message && (
        <p role="status" className="rounded-lg border border-red-900 p-3 text-sm">
          {message}
        </p>
      )}
      {loading && <p className="text-sm text-slate-400">TradePlans werden geladen …</p>}
      {!loading && items.length === 0 && !message && (
        <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
          Noch keine TradePlans vorhanden.
        </p>
      )}

      {!loading && items.length > 0 && visible.length === 0 && (
        <p>Keine TradePlans mit diesem Kaufstatus.</p>
      )}
      <div className="space-y-3">
        {!loading &&
          visible.map((item) => {
            const underlying = underlyings[item.underlying_id];
            const ticker = underlying?.primary_listing?.ticker;
            const selectionSearch = new URLSearchParams({
              trade_plan_id: item.id,
              trade_plan_version_id: item.latest_version_id,
            }).toString();
            return (
              <article key={item.id} className="rounded-xl border border-slate-800 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      {tradePlanReference(item.id)}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold">
                      {item.underlying_name ?? underlying?.name ?? 'Basiswert wird nicht aufgelöst'}
                    </h2>
                    <p className="mt-1 text-sm text-slate-400">
                      {[
                        ticker,
                        item.underlying_isin ?? underlying?.isin,
                        item.underlying_wkn ?? underlying?.wkn,
                      ]
                        .filter(Boolean)
                        .join(' · ') || 'Keine sichtbaren Kennungen'}
                    </p>
                  </div>
                  <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
                    <span className="text-slate-400">Planfreigabe: </span>
                    {item.status}
                  </span>
                </div>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-slate-500">Version</dt>
                    <dd className="mt-1">{item.latest_version}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Ursprung</dt>
                    <dd className="mt-1">
                      {item.origin_type === 'MANUAL' ? 'Manuell' : 'CandidateEvaluation'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Erstellt</dt>
                    <dd className="mt-1">{new Date(item.created_at).toLocaleString('de-DE')}</dd>
                  </div>
                </dl>
                <PlanPurchaseStatus item={item} />
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    to={`/trade-plans?trade_plan_id=${encodeURIComponent(item.id)}`}
                    className="inline-flex rounded-lg border border-slate-600 px-4 py-2 text-sm"
                  >
                    Öffnen
                  </Link>
                  {item.status === 'APPROVED' && (
                    <Link
                      to={`/product-selection?${selectionSearch}`}
                      className="inline-flex rounded-lg border border-emerald-700 px-4 py-2 text-sm"
                    >
                      {item.execution?.status === 'NOT_STARTED'
                        ? 'Produkt auswählen'
                        : 'Produktauswahl öffnen'}
                    </Link>
                  )}
                </div>
              </article>
            );
          })}
      </div>
    </main>
  );
}
