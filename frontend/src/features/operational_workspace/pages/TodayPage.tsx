import { Link } from 'react-router-dom';

import { useWorkspaceActions } from '../hooks/useWorkspaceActions';
import { workspaceActionTarget } from '../services/workspaceActionTarget';
import type { OperationalAction, OperationalPriority } from '../types';

const sections: { priority: OperationalPriority; title: string; description: string }[] = [
  {
    priority: 'ACTION',
    title: 'Jetzt prüfen',
    description: 'Positionshinweise, Datenprobleme und nächste verfügbare Schritte.',
  },
  {
    priority: 'REVIEW',
    title: 'Nachbereiten',
    description: 'Abgeschlossene Trades mit offenem Nachbereitungsbedarf.',
  },
  {
    priority: 'BLOCKED',
    title: 'Voraussetzungen klären',
    description: 'Hier ist vor dem nächsten Schritt noch eine Voraussetzung offen.',
  },
];

const actionLabels: Record<string, string> = {
  POSITION_ALERT: 'Positionshinweis',
  POSITION_DATA_HEALTH: 'Datenqualität',
  NOTIFICATION_DELIVERY_FAILURE: 'Benachrichtigung',
  INITIAL_PURCHASE: 'Kauferfassung',
  OPEN_POSITION_MANAGEMENT: 'Offene Position',
  POST_TRADE_OBSERVATION: 'Nachbeobachtung',
  EXIT_REVIEW: 'Exit Review',
};

function ActionCard({ action }: { action: OperationalAction }) {
  const productName = action.product_name?.replace(/\s+/g, ' ').trim();
  const hasProduct = action.product_id || Object.hasOwn(actionLabels, action.action_type);
  const target = workspaceActionTarget(action);
  return (
    <li className="min-w-0 rounded-xl border border-slate-800 bg-slate-900/50 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-400">
            {actionLabels[action.action_type] ?? 'Weiterer Hinweis'}
          </p>
          <h3 className="mt-1 break-words text-lg font-semibold text-white">{action.title}</h3>
        </div>
        <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
          {action.state === 'BLOCKED' ? 'Voraussetzung offen' : 'Bearbeitbar'}
        </span>
      </div>
      {productName && <p className="mt-2 break-words font-medium text-slate-200">{productName}</p>}
      {hasProduct && !productName && (
        <p className="mt-2 text-sm text-slate-400">Optionsschein: Name nicht verfügbar</p>
      )}
      {hasProduct && (
        <p className="mt-1 break-words text-xs text-slate-400">
          WKN: {action.product_wkn || '—'} · ISIN: {action.product_isin || '—'}
        </p>
      )}
      <p className="mt-3 text-sm leading-6 text-slate-300">{action.detail}</p>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">{action.next_action}</p>
        <Link
          to={target}
          aria-label={`${action.next_action}: ${action.title}`}
          className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-white focus-visible:outline-2 focus-visible:outline-sky-400"
        >
          Öffnen
        </Link>
      </div>
      <details className="mt-4 text-xs text-slate-500">
        <summary className="cursor-pointer">Herkunft und Zeitpunkt</summary>
        <dl className="mt-2 grid gap-1 break-words">
          <div>
            <dt className="inline">Bereich: </dt>
            <dd className="inline">{action.source_feature}</dd>
          </div>
          <div>
            <dt className="inline">Referenz: </dt>
            <dd className="inline">
              {action.resource_type} · {action.resource_id}
            </dd>
          </div>
          <div>
            <dt className="inline">Zeitpunkt: </dt>
            <dd className="inline">
              {action.occurred_at
                ? new Date(action.occurred_at).toLocaleString('de-DE')
                : 'Nicht verfügbar'}
            </dd>
          </div>
        </dl>
      </details>
    </li>
  );
}

export function TodayPage() {
  const { response, loading, error, reload } = useWorkspaceActions();
  const actions = response?.actions ?? [];
  return (
    <section className="w-full min-w-0 space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">Aktuelles</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Was erfordert jetzt deine Aufmerksamkeit? Hinweise aus deinen Positionen und laufenden
            Arbeitswegen.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          disabled={loading}
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-50"
        >
          {loading ? 'Aktualisiere …' : 'Aktualisieren'}
        </button>
      </header>
      <nav aria-label="Häufige Aufgaben" className="flex flex-wrap gap-3 text-sm">
        <Link to="/workspace" className="rounded-lg bg-sky-950 px-4 py-2 text-sky-100">
          Depot öffnen
        </Link>
        <Link to="/executions" className="rounded-lg border border-slate-700 px-4 py-2">
          Ausführung erfassen
        </Link>
        <Link to="/trade-plans" className="rounded-lg border border-slate-700 px-4 py-2">
          Tradeplan anlegen
        </Link>
      </nav>
      {loading && (
        <p role="status" className="text-sm text-slate-400">
          Aktuelle Hinweise werden geladen …
        </p>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200"
        >
          <p>{error}</p>
          <button type="button" onClick={() => void reload()} className="mt-2 underline">
            Erneut versuchen
          </button>
        </div>
      )}
      {!loading && !error && actions.length === 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="text-xl font-semibold">Aktuell keine offenen Hinweise</h2>
          <p className="mt-2 text-sm text-slate-400">
            Eine leere Hinweisliste bestätigt keine vollständige Überwachung. Den
            Überwachungszustand jeder Position findest du im Depot.
          </p>
        </section>
      )}
      {!error &&
        sections.map(({ priority, title, description }) => {
          const items = actions.filter((action) => action.priority === priority);
          if (!items.length) return null;
          return (
            <section key={priority} aria-labelledby={`today-${priority}`}>
              <h2 id={`today-${priority}`} className="text-xl font-semibold text-white">
                {title} <span className="text-slate-500">· {items.length}</span>
              </h2>
              <p className="mt-1 text-sm text-slate-400">{description}</p>
              <ul className="mt-3 grid gap-3 xl:grid-cols-2">
                {items.map((action) => (
                  <ActionCard key={action.id} action={action} />
                ))}
              </ul>
            </section>
          );
        })}
      <aside className="rounded-xl border border-slate-800 px-4 py-3 text-sm text-slate-400">
        <p>
          Hinweise zu einzelnen Positionen stehen oben und im Depot. Den übergreifenden Datenstand,
          Kurshistorien und Providerdiagnosen findest du unter{' '}
          <Link to="/data-sources" className="text-sky-300 underline">
            Datenquellen &amp; Diagnose
          </Link>
          .
        </p>
      </aside>
      {response && !error && (
        <p className="text-xs text-slate-500">
          Stand der Hinweise: {new Date(response.generated_at).toLocaleString('de-DE')}
        </p>
      )}
    </section>
  );
}
