import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { operationalWorkspaceApiClient } from '../services/client';
import type { OperationalAction, OperationalPriority } from '../types';

const sections: Array<{ priority: OperationalPriority; title: string; description: string }> = [
  {
    priority: 'ACTION',
    title: 'Jetzt handeln',
    description: 'Aktive Arbeit an Kandidaten und offenen Positionen.',
  },
  {
    priority: 'REVIEW',
    title: 'Review',
    description: 'Abgeschlossene Trades mit offenem Nachbereitungsbedarf.',
  },
  {
    priority: 'BLOCKED',
    title: 'Blockiert',
    description: 'Nicht ausführbare Schritte mit dem nächsten bekannten Entblocker.',
  },
];

function ActionCard({ action }: { action: OperationalAction }) {
  return (
    <li className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">{action.source_feature}</p>
          <h3 className="mt-1 text-lg font-semibold text-white">{action.title}</h3>
        </div>
        <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
          {action.state === 'BLOCKED' ? 'Blockiert' : 'Handlungsbereit'}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{action.detail}</p>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">Nächster Schritt: {action.next_action}</p>
        <Link
          to={action.target}
          className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-white"
        >
          Öffnen
        </Link>
      </div>
    </li>
  );
}

export function OperationalWorkspacePage() {
  const [actions, setActions] = useState<OperationalAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const response = await operationalWorkspaceApiClient.getActions(signal);
      setActions(response.actions);
      setGeneratedAt(response.generated_at);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return;
      setError(
        caught instanceof Error ? caught.message : 'Arbeitsbereich konnte nicht geladen werden.',
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const grouped = useMemo(
    () =>
      Object.fromEntries(
        sections.map(({ priority }) => [
          priority,
          actions.filter((action) => action.priority === priority),
        ]),
      ) as Record<OperationalPriority, OperationalAction[]>,
    [actions],
  );

  return (
    <section className="w-full space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-400">Operational Workspace</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">
            Was benötigt jetzt deine Aufmerksamkeit?
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Priorisierte nächste Schritte aus bestehenden Feature-Zuständen. Die Fachlogik bleibt in
            den jeweiligen Owner-Features.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Aktualisiere …' : 'Aktualisieren'}
        </button>
      </header>

      {error && (
        <div className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-3 underline underline-offset-4"
          >
            Erneut versuchen
          </button>
        </div>
      )}

      {!error && !loading && actions.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center">
          <h2 className="text-lg font-semibold text-white">Aktuell keine offenen Aufgaben.</h2>
          <p className="mt-2 text-sm text-slate-400">
            Neue Aktionen erscheinen automatisch, wenn sich die zugrunde liegenden Fachzustände
            ändern.
          </p>
        </div>
      )}

      {!error && actions.length > 0 && (
        <div className="space-y-8">
          {sections.map((section) => {
            const items = grouped[section.priority];
            if (items.length === 0) return null;
            return (
              <section
                key={section.priority}
                aria-labelledby={`workspace-${section.priority.toLowerCase()}`}
              >
                <div className="mb-3">
                  <h2
                    id={`workspace-${section.priority.toLowerCase()}`}
                    className="text-xl font-semibold text-white"
                  >
                    {section.title} <span className="text-slate-500">· {items.length}</span>
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">{section.description}</p>
                </div>
                <ul className="space-y-3">
                  {items.map((action) => (
                    <ActionCard key={action.id} action={action} />
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      {generatedAt && !error && (
        <p className="text-xs text-slate-500">
          Stand: {new Date(generatedAt).toLocaleString('de-DE')}
        </p>
      )}
    </section>
  );
}
