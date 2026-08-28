import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { hypothesisProposalClient } from '../services/hypothesisProposalClient';
import type {
  GovernedModelSummary,
  GovernedModelVersion,
  ModelChangeProposalSummary,
} from '../types/hypothesisProposal';

interface HypothesisProposalPanelProps {
  hypothesisId: string;
}

export function HypothesisProposalPanel({ hypothesisId }: HypothesisProposalPanelProps) {
  const [proposals, setProposals] = useState<ModelChangeProposalSummary[]>([]);
  const [models, setModels] = useState<GovernedModelSummary[]>([]);
  const [versions, setVersions] = useState<GovernedModelVersion[]>([]);
  const [modelId, setModelId] = useState('');
  const [baseVersionId, setBaseVersionId] = useState('');
  const [definition, setDefinition] = useState('');
  const [rationale, setRationale] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      hypothesisProposalClient.listForHypothesis(hypothesisId, controller.signal),
      hypothesisProposalClient.listModels(controller.signal),
    ])
      .then(([nextProposals, nextModels]) => {
        setProposals(nextProposals);
        setModels(nextModels);
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [hypothesisId]);

  useEffect(() => {
    if (!modelId || proposals.length > 0) {
      setVersions([]);
      setBaseVersionId('');
      return;
    }

    const controller = new AbortController();
    setLoadingVersions(true);
    setError(null);
    hypothesisProposalClient
      .listVersions(modelId, controller.signal)
      .then((nextVersions) => {
        const approved = nextVersions.filter((version) => version.status === 'APPROVED');
        setVersions(approved);
        const latest = approved.at(-1);
        setBaseVersionId(latest?.id ?? '');
        setDefinition(latest ? JSON.stringify(latest.definition, null, 2) : '');
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingVersions(false);
      });

    return () => controller.abort();
  }, [modelId, proposals.length]);

  const selectedVersion = useMemo(
    () => versions.find((version) => version.id === baseVersionId),
    [versions, baseVersionId],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const proposedDefinition = JSON.parse(definition) as Record<string, unknown>;
      const created = await hypothesisProposalClient.create({
        model_id: modelId,
        base_model_version_id: baseVersionId,
        hypothesis_id: hypothesisId,
        proposed_definition: proposedDefinition,
        rationale,
      });
      setProposals([created]);
    } catch (nextError: unknown) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    void submit(event);
  }

  if (loading) return <LoadingNotice label="FT-013-Proposals werden geladen …" />;

  if (proposals.length > 0) {
    return (
      <div className="mt-4 rounded-lg border border-slate-800 p-4">
        <p className="text-sm font-medium text-emerald-300">ModelChangeProposal vorhanden</p>
        {proposals.map((proposal) => (
          <div key={proposal.id} className="mt-3 text-sm">
            <p>
              Status: <span className="font-medium">{proposal.status}</span>
            </p>
            <p className="mt-1 break-all text-slate-500">Proposal {proposal.id}</p>
            <p className="mt-2 whitespace-pre-wrap text-slate-300">{proposal.rationale}</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <h4 className="font-medium">ModelChangeProposal erstellen</h4>
      <p className="mt-1 text-sm text-slate-400">
        Erstellt nur einen DRAFT. Validation, Approval und Aktivierung erfolgen nicht automatisch.
      </p>

      {error !== null && (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      )}

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm">
          <span className="text-slate-400">Governed Model</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={modelId}
            onChange={(event) => setModelId(event.target.value)}
            required
          >
            <option value="">Model auswählen</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.model_key} · {model.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-slate-400">APPROVED Base-Version</span>
          <select
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={baseVersionId}
            onChange={(event) => {
              const nextId = event.target.value;
              setBaseVersionId(nextId);
              const nextVersion = versions.find((version) => version.id === nextId);
              if (nextVersion) setDefinition(JSON.stringify(nextVersion.definition, null, 2));
            }}
            required
            disabled={!modelId || loadingVersions}
          >
            <option value="">{loadingVersions ? 'Versionen werden geladen …' : 'Version auswählen'}</option>
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                Version {version.version}
              </option>
            ))}
          </select>
        </label>

        {modelId && !loadingVersions && versions.length === 0 && (
          <p className="text-sm text-amber-300">Dieses Model hat keine APPROVED Version.</p>
        )}

        <label className="block text-sm">
          <span className="text-slate-400">Proposed Definition (JSON)</span>
          <textarea
            className="mt-1 min-h-48 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            value={definition}
            onChange={(event) => setDefinition(event.target.value)}
            required
          />
        </label>

        {selectedVersion && (
          <p className="text-xs text-slate-500">
            Ausgangspunkt: Model-Version {selectedVersion.version} · {selectedVersion.id}
          </p>
        )}

        <label className="block text-sm">
          <span className="text-slate-400">Rationale</span>
          <textarea
            className="mt-1 min-h-24 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            required
          />
        </label>

        <button
          type="submit"
          disabled={saving || !modelId || !baseVersionId}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Proposal wird angelegt …' : 'ModelChangeProposal als DRAFT anlegen'}
        </button>
      </form>
    </div>
  );
}
