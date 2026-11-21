import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { loadPositionSignals } from '../services/loadPositionSignals';
import { operationalWorkspaceApiClient } from '../services/client';
import type { OperationalPosition } from '../types';
import { OpenPositionsPanel } from './OpenPositionsPanel';

export function OperationalWorkspacePage() {
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
      const positionResponse = await operationalWorkspaceApiClient.getPositions(currentSignal);
      if (currentSignal.aborted) return;
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
        caught instanceof Error
          ? caught.message
          : 'Offene Positionen konnten nicht geladen werden.',
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

  return (
    <section className="w-full min-w-0 space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-white">Depot</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Offene Positionen finden, ihren Datenstand prüfen und im Trade bearbeiten.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Link to="/executions" className="rounded-lg bg-sky-950 px-3 py-2 text-sky-100">
            Ausführung erfassen
          </Link>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-slate-700 px-3 py-2 text-slate-200 disabled:opacity-50"
          >
            {loading ? 'Aktualisiere …' : 'Aktualisieren'}
          </button>
        </div>
      </header>
      {loading && (
        <p role="status" className="text-sm text-slate-400">
          Offene Positionen werden geladen …
        </p>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-200"
        >
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
      {!error && !loading && (
        <OpenPositionsPanel positions={positions} signalsLoading={signalsLoading} />
      )}
      <p className="text-sm text-slate-400">
        Abgeschlossene Trades findest du im Bericht{' '}
        <Link to="/performance/closed-trades" className="text-sky-300 underline">
          Vollabschlüsse im Zeitraum
        </Link>
        . Übergreifende Versorgungsprobleme prüfst du unter{' '}
        <Link to="/data-sources" className="text-sky-300 underline">
          Datenquellen &amp; Diagnose
        </Link>
        .
      </p>
      {generatedAt && !error && (
        <p className="text-xs text-slate-500">
          Stand des Depots: {new Date(generatedAt).toLocaleString('de-DE')}
        </p>
      )}
    </section>
  );
}
