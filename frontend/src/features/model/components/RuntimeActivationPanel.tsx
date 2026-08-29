import { useEffect, useState } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { runtimeActivationClient } from '../services/runtimeActivationClient';
import type { RuntimeActivation } from '../types/runtimeActivation';

interface RuntimeActivationPanelProps {
  modelId: string;
  approvedVersionId: string;
  approvedVersionNumber: number;
}

export function RuntimeActivationPanel({
  modelId,
  approvedVersionId,
  approvedVersionNumber,
}: RuntimeActivationPanelProps) {
  const [current, setCurrent] = useState<RuntimeActivation | null>(null);
  const [correlationId, setCorrelationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    runtimeActivationClient
      .getCurrent(modelId, controller.signal)
      .then(setCurrent)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [modelId]);

  async function activate() {
    setSaving(true);
    setError(null);
    try {
      const result = await runtimeActivationClient.activate(
        modelId,
        approvedVersionId,
        correlationId.trim() || undefined,
      );
      setCurrent(result);
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingNotice label="Runtime-Status wird geladen …" />;

  const isTargetActive = current?.model_version_id === approvedVersionId;

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">Runtime-Aktivierung</h4>
      {current === null ? (
        <p className="mt-2 text-sm text-slate-400">
          Für dieses Modell ist noch keine Runtime-Version aktiviert.
        </p>
      ) : (
        <p className="mt-2 text-sm text-slate-400">
          Aktuell aktiv: Version {current.model_version.version}
        </p>
      )}
      {isTargetActive ? (
        <p className="mt-3 text-sm font-medium text-emerald-300">
          APPROVED Version {approvedVersionNumber} ist aktuell aktiv.
        </p>
      ) : (
        <>
          <p className="mt-3 text-sm text-slate-400">
            Version {approvedVersionNumber} ist freigegeben, aber noch nicht aktiv. Die Aktivierung
            ist ein bewusster letzter Governance-Schritt.
          </p>
          {error !== null && (
            <div className="mt-3">
              <ErrorNotice error={error} />
            </div>
          )}
          <label className="mt-4 block text-sm">
            <span className="text-slate-400">Correlation ID (optional)</span>
            <input
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
              value={correlationId}
              onChange={(event) => setCorrelationId(event.target.value)}
              maxLength={100}
            />
          </label>
          <button
            type="button"
            disabled={saving}
            onClick={() => void activate()}
            className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Runtime wird umgestellt …' : `Version ${approvedVersionNumber} aktivieren`}
          </button>
        </>
      )}
    </div>
  );
}
