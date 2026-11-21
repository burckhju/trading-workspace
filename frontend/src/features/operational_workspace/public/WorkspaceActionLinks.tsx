import { Link } from 'react-router-dom';

import { useWorkspaceActions } from '../hooks/useWorkspaceActions';
import { workspaceActionTarget } from '../services/workspaceActionTarget';

/** Reuses the existing projection; it is neither a journal index nor a new task state. */
export function WorkspaceActionLinks({ scope }: { scope: 'learning' | 'purchase' }) {
  const { response, loading, error, reload } = useWorkspaceActions();
  const allowed =
    scope === 'learning' ? ['POST_TRADE_OBSERVATION', 'EXIT_REVIEW'] : ['INITIAL_PURCHASE'];
  const actions = response?.actions.filter((action) => allowed.includes(action.action_type)) ?? [];
  return (
    <section
      className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6"
      aria-label={
        scope === 'learning' ? 'Vorhandener Nachbereitungsbedarf' : 'Vorbereitete Kauferfassung'
      }
    >
      <h2 className="text-xl font-semibold text-white">
        {scope === 'learning' ? 'Vorhandener Nachbereitungsbedarf' : 'Vorbereitete Kauferfassung'}
      </h2>
      {loading && (
        <p role="status" className="mt-3 text-sm text-slate-400">
          Hinweise werden geladen …
        </p>
      )}
      {error && (
        <div role="alert" className="mt-3 text-sm text-rose-200">
          <p>{error}</p>
          <button type="button" onClick={() => void reload()} className="mt-2 underline">
            Erneut versuchen
          </button>
        </div>
      )}
      {!loading && !error && actions.length === 0 && (
        <p className="mt-3 text-sm text-slate-400">
          Hier liegen aktuell keine Hinweise vor. Die direkten Einstiege bleiben verfügbar.
        </p>
      )}
      {!error && (
        <ul className="mt-3 space-y-3">
          {actions.map((action) => (
            <li key={action.id} className="rounded-lg border border-slate-800 p-3">
              <Link
                to={workspaceActionTarget(action)}
                className="font-medium text-sky-300 underline underline-offset-4"
              >
                {action.product_name || action.title}
              </Link>
              <p className="mt-1 text-sm text-slate-400">{action.detail}</p>
              {action.state === 'BLOCKED' && (
                <p className="mt-1 text-sm text-amber-200">
                  Voraussetzung offen: {action.next_action}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
