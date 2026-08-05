import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ErrorNotice, LoadingNotice } from '../components/ApiFeedback';
import { StatusBadge } from '../components/StatusBadge';
import { marketApiClient } from '../services/client';
import type {
  AuditEventResponse,
  UnderlyingDetailResponse,
  UnderlyingUsageResponse,
} from '../types/api';

export function UnderlyingDetailPage() {
  const { underlyingId = '' } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState<UnderlyingDetailResponse | null>(null);
  const [audit, setAudit] = useState<AuditEventResponse[]>([]);
  const [usages, setUsages] = useState<UnderlyingUsageResponse[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, auditResult, usageResult] = await Promise.all([
        marketApiClient.getUnderlying(underlyingId),
        marketApiClient.getUnderlyingAuditEvents(underlyingId, { limit: 50 }),
        marketApiClient.getUnderlyingUsages(underlyingId),
      ]);
      setItem(detail);
      setAudit(auditResult.items);
      setUsages(usageResult.items);
    } catch (reason) {
      setError(reason);
    }
  }, [underlyingId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAction(action: 'verify' | 'deactivate' | 'reactivate' | 'delete') {
    if (!item) return;
    if (
      action === 'delete' &&
      !window.confirm('Basiswert endgültig löschen? Die Historie bleibt erhalten.')
    )
      return;
    if (
      action === 'deactivate' &&
      !window.confirm('Basiswert deaktivieren? Er wird in neuen Auswahllisten verborgen.')
    )
      return;
    setBusy(true);
    setError(null);
    try {
      if (action === 'verify')
        await marketApiClient.verifyUnderlying(item.id, { version: item.version });
      if (action === 'deactivate')
        await marketApiClient.deactivateUnderlying(item.id, { version: item.version });
      if (action === 'reactivate')
        await marketApiClient.reactivateUnderlying(item.id, { version: item.version });
      if (action === 'delete') {
        await marketApiClient.deleteUnderlying(item.id, item.version);
        void navigate('/underlyings');
        return;
      }
      await load();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  if (error && !item)
    return (
      <section className="w-full space-y-4">
        <ErrorNotice error={error} />
        <Link to="/underlyings" className="text-sky-300">
          Zurück zur Liste
        </Link>
      </section>
    );
  if (!item) return <LoadingNotice label="Basiswert wird geladen …" />;
  const totalUsage = usages.reduce((sum, usage) => sum + usage.count, 0);

  return (
    <section className="w-full space-y-8" aria-labelledby="underlying-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/underlyings" className="text-sm text-sky-300 hover:underline">
            ← Basiswerte
          </Link>
          <h1 id="underlying-title" className="mt-3 text-3xl font-semibold">
            {item.name}
          </h1>
          <div className="mt-3 flex gap-2">
            <StatusBadge status={item.lifecycle_status} />
            <StatusBadge status={item.quality_status} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/underlyings/${item.id}/edit`}
            className="rounded-lg border border-slate-700 px-4 py-2 hover:bg-slate-800"
          >
            Bearbeiten
          </Link>
          {item.lifecycle_status === 'ACTIVE' ? (
            <button
              disabled={busy}
              onClick={() => void runAction('deactivate')}
              className="rounded-lg border border-amber-700 px-4 py-2 text-amber-300"
            >
              Deaktivieren
            </button>
          ) : (
            <button
              disabled={busy}
              onClick={() => void runAction('reactivate')}
              className="rounded-lg border border-emerald-700 px-4 py-2 text-emerald-300"
            >
              Reaktivieren
            </button>
          )}
          {item.quality_status === 'COMPLETE' && (
            <button
              disabled={busy}
              onClick={() => void runAction('verify')}
              className="rounded-lg bg-sky-500 px-4 py-2 font-semibold text-slate-950"
            >
              Verifizieren
            </button>
          )}
          <button
            disabled={busy}
            onClick={() => void runAction('delete')}
            className="rounded-lg border border-red-800 px-4 py-2 text-red-300"
          >
            Löschen
          </button>
        </div>
      </div>
      {error !== null && <ErrorNotice error={error} />}
      <div className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="text-lg font-semibold">Übersicht</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-slate-500">Basiswertart</dt>
              <dd className="mt-1">Aktie</dd>
            </div>
            <div>
              <dt className="text-slate-500">Version</dt>
              <dd className="mt-1">{item.version}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Erstellt</dt>
              <dd className="mt-1">{new Date(item.created_at).toLocaleString('de-DE')}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Geändert</dt>
              <dd className="mt-1">{new Date(item.updated_at).toLocaleString('de-DE')}</dd>
            </div>
          </dl>
        </article>
        <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="text-lg font-semibold">Identifikatoren</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <div>
              <dt className="text-slate-500">ISIN</dt>
              <dd className="mt-1 font-mono">{item.isin ?? 'Nicht angegeben'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">WKN</dt>
              <dd className="mt-1 font-mono">{item.wkn ?? 'Nicht angegeben'}</dd>
            </div>
          </dl>
        </article>
      </div>
      <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
        <h2 className="text-lg font-semibold">Notierungen</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2">Ticker</th>
                <th>Markt</th>
                <th>Währung</th>
                <th>Status</th>
                <th>Rolle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {item.listings.map((listing) => (
                <tr key={listing.id}>
                  <td className="py-3 font-mono">{listing.ticker}</td>
                  <td>
                    {listing.trading_venue_name ??
                      listing.trading_venue_mic ??
                      listing.trading_venue_id}
                  </td>
                  <td>{listing.currency_code}</td>
                  <td>
                    <StatusBadge status={listing.lifecycle_status} />
                  </td>
                  <td>{listing.is_primary ? 'Primär' : 'Weitere'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <div className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="text-lg font-semibold">Verwendungen</h2>
          {totalUsage === 0 ? (
            <p className="mt-4 text-sm text-slate-400">
              Keine fachlichen Verwendungen vorhanden. Der Basiswert kann grundsätzlich gelöscht
              werden.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {usages.map((usage) => (
                <li
                  key={usage.usage_type}
                  className="flex justify-between rounded-lg bg-slate-950 p-3"
                >
                  <span>{usage.usage_type}</span>
                  <strong>{usage.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="text-lg font-semibold">Änderungshistorie</h2>
          {audit.length === 0 ? (
            <p className="mt-4 text-sm text-slate-400">Noch keine Historieneinträge vorhanden.</p>
          ) : (
            <ol className="mt-4 space-y-4">
              {audit.map((event) => (
                <li key={event.id} className="border-l border-slate-700 pl-4">
                  <div className="flex justify-between gap-3 text-sm">
                    <strong>{event.change_type}</strong>
                    <time className="text-slate-500">
                      {new Date(event.occurred_at).toLocaleString('de-DE')}
                    </time>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{event.actor_display_name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {Object.keys(event.field_changes).join(', ') || 'Statusänderung'}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </article>
      </div>
    </section>
  );
}
