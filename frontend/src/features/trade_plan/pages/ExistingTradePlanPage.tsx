import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { marketApiClient } from '../../market/services/client';
import type { UnderlyingDetailResponse } from '../../market/types/api';
import { tradePlanApiClient } from '../services/client';
import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

function nextStep(status: TradePlanVersionResponse['status']): string {
  if (status === 'DRAFT') return 'Zur Prüfung einreichen';
  if (status === 'READY_FOR_REVIEW') return 'Explizit freigeben';
  if (status === 'APPROVED') return 'Produktauswahl starten';
  if (status === 'ABANDONED') return 'Kein weiterer Schritt – TradePlan wurde aufgegeben';
  return 'Versionsstand prüfen';
}

export function ExistingTradePlanPage({ tradePlanId }: { tradePlanId: string }) {
  const [detail, setDetail] = useState<TradePlanDetailResponse | null>(null);
  const [versions, setVersions] = useState<TradePlanVersionResponse[]>([]);
  const [underlying, setUnderlying] = useState<UnderlyingDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      const [nextDetail, history] = await Promise.all([
        tradePlanApiClient.get(tradePlanId, signal),
        tradePlanApiClient.versions(tradePlanId, signal),
      ]);
      setDetail(nextDetail);
      setVersions(history);
      try {
        setUnderlying(await marketApiClient.getUnderlying(nextDetail.plan.underlying_id, signal));
      } catch {
        setUnderlying(null);
      }
    },
    [tradePlanId],
  );

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    void refresh(controller.signal)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setMessage(
            error instanceof Error ? error.message : 'TradePlan konnte nicht geladen werden.',
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [refresh]);

  async function mutate(action: 'submit' | 'approve') {
    if (!detail) return;
    setBusy(true);
    setMessage(null);
    try {
      const current = detail.latest_version;
      if (action === 'submit') {
        await tradePlanApiClient.submitForReview(detail.plan.id, current.id);
      } else {
        await tradePlanApiClient.approve(detail.plan.id, current.id);
      }
      await refresh();
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Statusänderung fehlgeschlagen.');
    } finally {
      setBusy(false);
    }
  }

  const current = detail?.latest_version ?? null;

  return (
    <main className="w-full space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            FT-007 · Bestehender TradePlan
          </p>
          <h1 className="mt-1 text-2xl font-semibold">
            {detail ? tradePlanReference(detail.plan.id) : 'TradePlan'}
          </h1>
          {underlying && (
            <p className="mt-2 text-sm text-slate-400">
              {underlying.name}
              {underlying.primary_listing?.ticker ? ` · ${underlying.primary_listing.ticker}` : ''}
              {underlying.isin ? ` · ${underlying.isin}` : ''}
              {underlying.wkn ? ` · ${underlying.wkn}` : ''}
            </p>
          )}
        </div>
        <Link
          to="/trade-plans/overview"
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm"
        >
          Zur Übersicht
        </Link>
      </header>

      {message && (
        <p role="status" className="rounded-lg border border-slate-700 p-3 text-sm">
          {message}
        </p>
      )}
      {busy && !detail && <p className="text-sm text-slate-400">TradePlan wird geladen …</p>}

      {detail && current && (
        <>
          <section className="rounded-xl border border-sky-900 bg-sky-950/20 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-sky-400">Aktueller Stand</p>
                <h2 className="mt-1 text-xl font-semibold">
                  Version {current.version} · {current.status}
                </h2>
              </div>
              <span className="rounded-full border border-sky-800 px-3 py-1 text-xs">
                {current.direction}
              </span>
            </div>
            <p className="mt-4 whitespace-pre-wrap text-sm">{current.thesis}</p>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-slate-500">Entry</dt>
                <dd className="mt-1">
                  {current.entry.price ?? current.entry.trigger ?? current.entry.type}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Stop</dt>
                <dd className="mt-1">{current.invalidation.stop_price ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Target 1</dt>
                <dd className="mt-1">{current.targets[0]?.price ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Nächster Schritt</dt>
                <dd className="mt-1 font-medium">{nextStep(current.status)}</dd>
              </div>
            </dl>
            <div className="mt-5 flex flex-wrap gap-3">
              {current.status === 'DRAFT' && (
                <button
                  disabled={busy}
                  onClick={() => void mutate('submit')}
                  className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
                >
                  Zur Prüfung einreichen
                </button>
              )}
              {current.status === 'READY_FOR_REVIEW' && (
                <button
                  disabled={busy}
                  onClick={() => void mutate('approve')}
                  className="rounded-lg border border-emerald-700 px-4 py-2 text-sm disabled:opacity-50"
                >
                  Explizit freigeben
                </button>
              )}
              {current.status === 'APPROVED' && (
                <Link
                  to={`/product-selection?trade_plan_id=${encodeURIComponent(detail.plan.id)}&trade_plan_version_id=${encodeURIComponent(current.id)}`}
                  className="rounded-lg border border-emerald-700 px-4 py-2 text-sm"
                >
                  Produktauswahl starten
                </Link>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-slate-800 p-5">
            <h2 className="text-lg font-semibold">Versionshistorie</h2>
            <ol className="mt-4 space-y-2">
              {versions.map((version) => (
                <li key={version.id} className="rounded-lg border border-slate-800 p-3 text-sm">
                  <span className="font-medium">
                    Version {version.version} · {version.status}
                  </span>
                  <span className="ml-2 text-slate-500">
                    {new Date(version.created_at).toLocaleString('de-DE')}
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <details className="rounded-xl border border-slate-800 p-4 text-xs text-slate-500">
            <summary className="cursor-pointer">Technische Provenance anzeigen</summary>
            <div className="mt-2 space-y-1 break-all">
              <p>TradePlan-ID {detail.plan.id}</p>
              <p>Underlying-ID {detail.plan.underlying_id}</p>
              <p>TradePlanVersion-ID {current.id}</p>
            </div>
          </details>
        </>
      )}
    </main>
  );
}
