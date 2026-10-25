import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { hypothesisProposalClient } from '../services/hypothesisProposalClient';
import { runtimeActivationClient } from '../services/runtimeActivationClient';
import {
  CANDIDATE_MODEL_KEY,
  candidatePolicyLabel,
  readCandidateConfiguration,
} from '../types/candidateConfiguration';
import type { GovernedModelVersion } from '../types/hypothesisProposal';
import type { RuntimeActivation } from '../types/runtimeActivation';

interface RuntimeActivationPanelProps {
  modelId: string;
  approvedVersionId: string;
  approvedVersionNumber: number;
  modelKey?: string;
}

export function RuntimeActivationPanel(props: RuntimeActivationPanelProps) {
  return <RuntimeActivationForm key={`${props.modelId}:${props.approvedVersionId}`} {...props} />;
}

function RuntimeActivationForm({
  modelId,
  approvedVersionId,
  modelKey,
}: RuntimeActivationPanelProps) {
  const [current, setCurrent] = useState<RuntimeActivation | null>(null);
  const [versions, setVersions] = useState<GovernedModelVersion[]>([]);
  const [targetId, setTargetId] = useState(approvedVersionId);
  const [correlationId, setCorrelationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const instance = useRef<object | null>(null);
  const operation = useRef<object | null>(null);

  useLayoutEffect(() => {
    instance.current = {};
    return () => {
      instance.current = null;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const visit = instance.current;
    const ownsRead = () =>
      visit !== null && instance.current === visit && !controller.signal.aborted;
    setLoading(true);
    setReady(false);
    setError(null);
    Promise.all([
      runtimeActivationClient.getCurrent(modelId, controller.signal),
      hypothesisProposalClient.listVersions(modelId, controller.signal),
    ])
      .then(([activation, items]) => {
        if (!ownsRead()) return;
        if (
          items.some((v) => !v.id || v.model_id !== modelId) ||
          new Set(items.map((v) => v.id)).size !== items.length ||
          (activation !== null &&
            (activation.model_id !== modelId ||
              activation.model_version.model_id !== modelId ||
              activation.model_version.id !== activation.model_version_id))
        ) {
          throw new Error('Der Aktivierungslesestand passt nicht eindeutig zum Modell.');
        }
        setCurrent(activation);
        setVersions(items);
        setUncertain(false);
        setReady(true);
      })
      .catch((nextError: unknown) => {
        if (ownsRead()) setError(nextError);
      })
      .finally(() => {
        if (ownsRead()) setLoading(false);
      });
    return () => controller.abort();
  }, [modelId, refresh]);

  const choices = versions.filter(
    (v) =>
      v.status === 'APPROVED' &&
      (modelKey !== CANDIDATE_MODEL_KEY || readCandidateConfiguration(v.definition) !== null),
  );
  const target = choices.find((v) => v.id === targetId);
  const targetConfiguration = target ? readCandidateConfiguration(target.definition) : null;
  const newest = versions.reduce<GovernedModelVersion | null>(
    (latest, v) => (!latest || v.version > latest.version ? v : latest),
    null,
  );
  const isTargetActive = target !== undefined && current?.model_version_id === target.id;

  async function activate() {
    const visit = instance.current;
    if (
      !ready ||
      loading ||
      uncertain ||
      !target ||
      isTargetActive ||
      visit === null ||
      operation.current !== null
    )
      return;
    const pending = {};
    operation.current = pending;
    const ownsCommand = () => instance.current === visit && operation.current === pending;
    const versionId = target.id;
    setSaving(true);
    setError(null);
    try {
      const result = await runtimeActivationClient.activate(
        modelId,
        versionId,
        correlationId.trim() || undefined,
      );
      if (!ownsCommand()) return;
      if (
        result.model_id !== modelId ||
        result.model_version_id !== versionId ||
        result.model_version.id !== versionId ||
        result.model_version.model_id !== modelId
      ) {
        throw new Error('Die Aktivierungsantwort gehört nicht zum bestätigten Ziel.');
      }
      setCurrent(result);
    } catch (nextError: unknown) {
      if (ownsCommand()) {
        setError(nextError);
        setUncertain(true);
      }
    } finally {
      if (ownsCommand()) {
        operation.current = null;
        setSaving(false);
      }
    }
  }

  if (loading) return <LoadingNotice label="Runtime-Status wird geladen …" />;

  return (
    <section
      aria-label="Runtime-Aktivierung"
      className="mt-4 min-w-0 rounded-lg border border-slate-800 p-4"
    >
      <h4 className="font-medium">Runtime-Aktivierung</h4>
      {error !== null && (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      )}
      <button
        type="button"
        disabled={saving}
        className="mt-3 text-sm text-emerald-300 underline"
        onClick={() => {
          if (operation.current === null) setRefresh((n) => n + 1);
        }}
      >
        Aktivierungsstand neu laden
      </button>
      {uncertain && (
        <p className="mt-2 text-sm text-amber-300">
          Der Befehlsabschluss ist nicht bestätigt. Vor einer weiteren Aktivierung den gespeicherten
          Stand bewusst neu laden. Keine automatische Wiederholung.
        </p>
      )}
      {!ready ? (
        <p className="mt-2 text-sm">
          Aktivierungsstand nicht verifiziert. Keine Aktivierung bis zum erfolgreichen Neuladen.
        </p>
      ) : (
        <>
          {newest && (
            <p className="mt-2 break-all text-sm">
              Neueste Modellversion: {newest.version} · {newest.status} · {newest.id}. Neueste,
              genehmigte und aktive Version sind getrennte Angaben.
            </p>
          )}
          {current === null ? (
            <p className="mt-2 text-sm text-slate-400">
              Für dieses Modell ist noch keine Runtime-Version aktiviert.
            </p>
          ) : (
            <div className="mt-2 break-all text-sm text-slate-400">
              <p>
                Aktuell aktiv: Version {current.model_version.version} · {current.model_version_id}
              </p>
              <p>
                Aktivierung {current.id} · {current.activated_at}
              </p>
            </div>
          )}
          <label className="mt-4 block text-sm">
            <span>Genehmigte Zielversion</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
              value={targetId}
              disabled={saving || uncertain}
              onChange={(event) => {
                if (operation.current === null) {
                  setTargetId(event.target.value);
                  setCorrelationId('');
                }
              }}
            >
              <option value="">Version ausdrücklich auswählen</option>
              {choices.map((v) => (
                <option key={v.id} value={v.id}>
                  Version {v.version} · {v.id}
                  {current?.model_version_id === v.id ? ' · aktiv' : ''}
                </option>
              ))}
            </select>
          </label>
          {target ? (
            <>
              <p className="mt-2 break-all text-sm">
                Genehmigtes Ziel: Version {target.version} · {target.id}
              </p>
              {targetConfiguration && (
                <p className="mt-1 text-sm">
                  Ziel-Policy: {candidatePolicyLabel(targetConfiguration.policy)}
                </p>
              )}
              {isTargetActive ? (
                <p className="mt-3 text-sm font-medium text-emerald-300">
                  APPROVED Version {target.version} ist aktuell aktiv.
                </p>
              ) : (
                <>
                  <p className="mt-3 text-sm text-slate-400">
                    Version {target.version} ist freigegeben, aber noch nicht aktiv. Auch die
                    Rückkehr zu einer früheren Version ist eine neue ausdrückliche Aktivierung.
                    Historische Ergebnisse bleiben erhalten.
                  </p>
                  <label className="mt-4 block text-sm">
                    <span className="text-slate-400">Correlation ID (optional)</span>
                    <input
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
                      value={correlationId}
                      disabled={saving || uncertain}
                      onChange={(event) => {
                        if (operation.current === null) setCorrelationId(event.target.value);
                      }}
                      maxLength={100}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={saving || uncertain}
                    onClick={() => void activate()}
                    className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
                  >
                    {saving ? 'Runtime wird umgestellt …' : `Version ${target.version} aktivieren`}
                  </button>
                </>
              )}
            </>
          ) : (
            <p className="mt-2 text-sm text-amber-300">
              Keine genehmigte kompatible Zielversion ausgewählt.
            </p>
          )}
          <p className="mt-3 text-xs text-slate-400">
            Die nächste Candidate-Ausführung löst ihre dann aktive Version erneut auf; dieser
            Lesestand bindet keine spätere Bewertung.
          </p>
        </>
      )}
    </section>
  );
}
