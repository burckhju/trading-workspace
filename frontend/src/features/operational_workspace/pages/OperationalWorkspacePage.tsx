import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { loadPositionSignals } from '../services/loadPositionSignals';
import { operationalWorkspaceApiClient } from '../services/client';
import type { OperationalAction, OperationalPosition, OperationalPriority } from '../types';
import { MarketDataRefreshPanel } from './MarketDataRefreshPanel';
import { OpenPositionsPanel } from './OpenPositionsPanel';

const sections: Array<{ priority: OperationalPriority; title: string; description: string }> = [
  {
    priority: 'ACTION',
    title: 'Jetzt handeln',
    description:
      'Offene Positionshinweise zuerst, danach Monitoring-Datenprobleme und weitere ausführbare Schritte.',
  },
  {
    priority: 'REVIEW',
    title: 'Prüfen',
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
  const [positions, setPositions] = useState<OperationalPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [signalsLoading, setSignalsLoading] = useState(false);
  const activeLoad = useRef<AbortController | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    activeLoad.current?.abort();
    const controller = new AbortController();
    activeLoad.current = controller;
    if (signal?.aborted) controller.abort();
    signal?.addEventListener('abort', () => controller.abort(), { once: true });
    const currentSignal = controller.signal;
    setLoading(true);
    setSignalsLoading(false);
    setError(null);
    try {
      const [actionResponse, positionResponse] = await Promise.all([
        operationalWorkspaceApiClient.getActions(currentSignal),
        operationalWorkspaceApiClient.getPositions(currentSignal),
      ]);
      if (currentSignal.aborted) return;
      setActions(actionResponse.actions);
      setPositions(positionResponse.positions);
      setGeneratedAt(positionResponse.generated_at);
      setLoading(false);
      setSignalsLoading(positionResponse.positions.length > 0);
      await loadPositionSignals(
        positionResponse.positions,
        operationalWorkspaceApiClient.getPositionAlertProjection,
        (id, result) =>
          setPositions((current) =>
            current.map((p) => (p.position_id === id ? { ...p, position_signal: result } : p)),
          ),
        currentSignal,
      );
    } catch (caught) {
      if (currentSignal.aborted) return;
      setError(
        caught instanceof Error ? caught.message : 'Arbeitsbereich konnte nicht geladen werden.',
      );
    } finally {
      if (!currentSignal.aborted) {
        setLoading(false);
        setSignalsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => {
      controller.abort();
      activeLoad.current?.abort();
    };
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
    <section className="min-w-0 w-full space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-400">Operativer Arbeitsbereich</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">
            Was benötigt jetzt deine Aufmerksamkeit?
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Priorisierte nächste Schritte aus bestehenden Fachzuständen. Die Fachlogik bleibt in den
            jeweiligen zuständigen Bereichen. Die Reihenfolge ist eine operative Sicht und keine
            Tradingempfehlung.
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

      <MarketDataRefreshPanel />
      {!error && !loading && (
        <OpenPositionsPanel positions={positions} signalsLoading={signalsLoading} />
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
